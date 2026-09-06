"""Native Decky backend for EasyTier profiles and one managed core process."""

import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import decky

SCHEMA_VERSION = 2
EASYTIER_VERSION = "bundled"
RPC_ADDRESS = "127.0.0.1:15888"
MAX_LOG_BYTES = 2 * 1024 * 1024
MAX_LOG_LINES = 200
STOP_TIMEOUT = 5
RESTART_DELAYS = (1, 2, 4, 8, 16, 30)


def ok(data: Any = None) -> dict[str, Any]:
    value = {"success": True}
    if data is not None:
        value["data"] = data
    return value


def fail(code: str, message: str, details: str | None = None) -> dict[str, Any]:
    error = {"code": code, "message": message}
    if details:
        error["details"] = details
    return {"success": False, "error": error}


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class ProfileRepository:
    """Stores plugin state, profile metadata and EasyTier TOML."""

    def __init__(self, settings_dir: Path, runtime_dir: Path):
        self.root = settings_dir / "native"
        self.profiles_dir = self.root / "profiles"
        self.state_path = self.root / "state.json"
        self.index_path = self.root / "profiles.json"
        self.legacy_config = settings_dir / "config.json"
        self.legacy_runtime = runtime_dir / "easytier"
        self.state: dict[str, Any] = {}
        self.index: dict[str, Any] = {"profiles": []}

    def initialize(self) -> None:
        version = None
        try:
            version = json.loads(self.state_path.read_text("utf-8")).get("schema_version")
        except (OSError, ValueError):
            pass
        if version != SCHEMA_VERSION:
            self._reset_legacy()
        self.profiles_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        os.chmod(self.profiles_dir, 0o700)
        self.state = self._read_json(self.state_path, {
            "schema_version": SCHEMA_VERSION,
            "selected_profile_id": None,
            "settings": {"auto_start": False, "auto_restart_core": True},
        })
        self.state["schema_version"] = SCHEMA_VERSION
        self.state.setdefault("selected_profile_id", None)
        self.state.setdefault("settings", {})
        self.state["settings"].setdefault("auto_start", False)
        self.state["settings"].setdefault("auto_restart_core", True)
        self.index = self._read_json(self.index_path, {"profiles": []})
        self.index.setdefault("profiles", [])
        self._save_state()
        self._save_index()

    def _reset_legacy(self) -> None:
        for path in (self.root, self.legacy_runtime):
            if path.exists():
                shutil.rmtree(path)
        self.legacy_config.unlink(missing_ok=True)

    @staticmethod
    def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text("utf-8"))
            return value if isinstance(value, dict) else default.copy()
        except (OSError, ValueError):
            return default.copy()

    def _save_state(self) -> None:
        atomic_write(self.state_path, json.dumps(self.state, ensure_ascii=False, indent=2) + "\n")

    def _save_index(self) -> None:
        atomic_write(self.index_path, json.dumps(self.index, ensure_ascii=False, indent=2) + "\n")

    def list_profiles(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self.index["profiles"]]

    def profile_path(self, profile_id: str) -> Path:
        try:
            if str(uuid.UUID(profile_id)) != profile_id:
                raise ValueError
        except (ValueError, AttributeError):
            raise ValueError("Invalid profile id") from None
        return self.profiles_dir / f"{profile_id}.toml"

    def get_profile(self, profile_id: str | None) -> dict[str, Any] | None:
        if not profile_id:
            return None
        meta = next((item for item in self.index["profiles"] if item["id"] == profile_id), None)
        if not meta:
            return None
        try:
            path = self.profile_path(profile_id)
        except ValueError:
            return None
        return {**meta, "toml": path.read_text("utf-8")} if path.exists() else None

    def save_profile(self, name: str, toml: str, profile_id: str | None = None) -> dict[str, Any]:
        name = name.strip()
        if not name or len(name) > 64:
            raise ValueError("Profile name must contain 1-64 characters")
        if any(x["name"].casefold() == name.casefold() and x["id"] != profile_id for x in self.index["profiles"]):
            raise ValueError("Profile name already exists")
        now = datetime.now(timezone.utc).isoformat()
        if profile_id:
            meta = next((x for x in self.index["profiles"] if x["id"] == profile_id), None)
            if not meta:
                raise KeyError(profile_id)
            meta.update(name=name, updated_at=now)
        else:
            profile_id = str(uuid.uuid4())
            meta = {"id": profile_id, "name": name, "created_at": now, "updated_at": now}
            self.index["profiles"].append(meta)
        atomic_write(self.profile_path(profile_id), toml.rstrip() + "\n")
        self._save_index()
        if not self.state.get("selected_profile_id"):
            self.state["selected_profile_id"] = profile_id
            self._save_state()
        return dict(meta)

    def delete_profile(self, profile_id: str) -> bool:
        old_count = len(self.index["profiles"])
        self.index["profiles"] = [x for x in self.index["profiles"] if x["id"] != profile_id]
        if len(self.index["profiles"]) == old_count:
            return False
        self.profile_path(profile_id).unlink(missing_ok=True)
        if self.state.get("selected_profile_id") == profile_id:
            self.state["selected_profile_id"] = self.index["profiles"][0]["id"] if self.index["profiles"] else None
            self._save_state()
        self._save_index()
        return True

    def select_profile(self, profile_id: str) -> None:
        if not self.get_profile(profile_id):
            raise KeyError(profile_id)
        self.state["selected_profile_id"] = profile_id
        self._save_state()

    def save_settings(self, settings: dict[str, Any]) -> dict[str, bool]:
        normalized = {
            "auto_start": bool(settings.get("auto_start", False)),
            "auto_restart_core": bool(settings.get("auto_restart_core", True)),
        }
        self.state["settings"] = normalized
        self._save_state()
        return normalized


class RotatingLog:
    def __init__(self, log_dir: Path):
        self.dir = log_dir
        self.path = log_dir / "easytier.log"
        self.recent: deque[str] = deque(maxlen=MAX_LOG_LINES)
        self.dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.dir, 0o700)

    def _rotate(self) -> None:
        if not self.path.exists() or self.path.stat().st_size < MAX_LOG_BYTES:
            return
        (self.dir / "easytier.log.2").unlink(missing_ok=True)
        one = self.dir / "easytier.log.1"
        if one.exists():
            one.replace(self.dir / "easytier.log.2")
        self.path.replace(one)

    def write(self, line: str, secrets: list[str] | None = None) -> None:
        clean = line.rstrip("\r\n")
        for secret in secrets or []:
            if secret:
                clean = clean.replace(secret, "<redacted>")
        self._rotate()
        with self.path.open("a", encoding="utf-8") as output:
            output.write(clean + "\n")
        os.chmod(self.path, 0o600)
        self.recent.append(clean)

    def tail(self, limit: int) -> list[str]:
        limit = max(0, min(int(limit), MAX_LOG_LINES))
        if not limit:
            return []
        try:
            return self.path.read_text("utf-8", errors="replace").splitlines()[-limit:]
        except OSError:
            return list(self.recent)[-limit:]


@dataclass
class ProcessState:
    status: str = "stopped"
    profile_id: str | None = None
    pid: int | None = None
    restart_attempt: int = 0
    error: str | None = None


class EasyTierProcessManager:
    def __init__(self, core: Path, cli: Path, repository: ProfileRepository, log: RotatingLog):
        self.core, self.cli, self.repository, self.log = core, cli, repository, log
        self.process: asyncio.subprocess.Process | None = None
        self.state = ProcessState()
        self.monitor_task: asyncio.Task[Any] | None = None
        self.log_tasks: list[asyncio.Task[Any]] = []
        self.stop_requested = False
        self.restart_failures: deque[float] = deque()
        self.started_at: float | None = None
        self.restart_required = False
        self.pending_backup: dict[str, Any] | None = None
        self.lock = asyncio.Lock()

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.returncode is None

    async def validate(self, toml: str) -> dict[str, Any]:
        if not self.core.exists():
            return fail("BINARY_MISSING", "easytier-core is missing from the plugin package")
        fd, name = tempfile.mkstemp(suffix=".toml", dir=self.repository.root)
        os.close(fd)
        candidate = Path(name)
        try:
            atomic_write(candidate, toml.rstrip() + "\n")
            proc = await asyncio.create_subprocess_exec(str(self.core), "--check-config", "-c", str(candidate), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), 10)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return fail("VALIDATION_TIMEOUT", "Configuration validation timed out")
            if proc.returncode:
                detail = (stderr or stdout).decode("utf-8", "replace")[-4000:]
                for secret in self._secrets(toml):
                    detail = detail.replace(secret, "<redacted>")
                return fail("INVALID_CONFIG", "EasyTier rejected this TOML configuration", detail)
            return ok({"valid": True})
        finally:
            candidate.unlink(missing_ok=True)

    @staticmethod
    def _secrets(toml: str) -> list[str]:
        return re.findall(r'''(?m)^\s*(?:network_secret|credential|local_private_key)\s*=\s*["']([^"']+)''', toml)

    async def _enable_ip_forwarding(self) -> None:
        """Best-effort host setup required by routed TUN profiles."""
        for setting in ("net.ipv4.ip_forward=1", "net.ipv6.conf.all.forwarding=1"):
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["sysctl", "-w", setting],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if result.returncode:
                    decky.logger.warning("Unable to enable %s: %s", setting, result.stderr.strip())
            except (OSError, subprocess.SubprocessError) as error:
                decky.logger.warning("Unable to enable %s: %s", setting, error)

    async def start(self, profile_id: str, restart_attempt: int = 0) -> dict[str, Any]:
        async with self.lock:
            if self.running:
                return ok(asdict(self.state)) if self.state.profile_id == profile_id else fail("ALREADY_RUNNING", "Stop the active profile first")
            profile = self.repository.get_profile(profile_id)
            if not profile:
                return fail("PROFILE_NOT_FOUND", "Profile not found")
            if not self.core.exists() or not self.cli.exists():
                return fail("BINARY_MISSING", "EasyTier binaries are missing from the plugin package")
            validation = await self.validate(profile["toml"])
            if not validation["success"]:
                return validation
            if restart_attempt == 0:
                self.restart_failures.clear()
            self.state = ProcessState("starting", profile_id, restart_attempt=restart_attempt)
            self.stop_requested = False
            await self._enable_ip_forwarding()
            try:
                self.process = await asyncio.create_subprocess_exec(
                    str(self.core), "-c", str(self.repository.profile_path(profile_id)),
                    "--rpc-portal", RPC_ADDRESS,
                    "--rpc-portal-whitelist", "127.0.0.0/8,::1/128",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.repository.root),
                )
            except OSError as error:
                self.state = ProcessState("error", profile_id, error=str(error))
                return fail("START_FAILED", "Unable to start easytier-core", str(error))
            self.started_at = time.monotonic()
            self.state.status, self.state.pid = "running", self.process.pid
            secrets = self._secrets(profile["toml"])
            self.log_tasks = [asyncio.create_task(self._drain(self.process.stdout, secrets)), asyncio.create_task(self._drain(self.process.stderr, secrets))]
            self.monitor_task = asyncio.create_task(self._monitor(self.process, profile_id))
            self.repository.select_profile(profile_id)
            self.restart_required = False
            self.pending_backup = None
            return ok(asdict(self.state))

    async def _drain(self, stream: asyncio.StreamReader | None, secrets: list[str]) -> None:
        if stream:
            while line := await stream.readline():
                self.log.write(line.decode("utf-8", "replace"), secrets)

    async def _monitor(self, process: asyncio.subprocess.Process, profile_id: str) -> None:
        code = await process.wait()
        await asyncio.gather(*self.log_tasks, return_exceptions=True)
        if self.process is not process:
            return
        self.process, self.state.pid = None, None
        if self.stop_requested:
            self.state.status = "stopped"
            return
        self.state.status, self.state.error = "crashed", f"easytier-core exited with code {code}"
        self.log.write(self.state.error)
        if not self.repository.state["settings"].get("auto_restart_core", True):
            return
        now = time.monotonic()
        if self.started_at and now - self.started_at >= 300:
            self.restart_failures.clear()
        while self.restart_failures and now - self.restart_failures[0] > 600:
            self.restart_failures.popleft()
        if len(self.restart_failures) >= 5:
            self.state.status, self.state.error = "error", "Automatic restart stopped after 5 failures in 10 minutes"
            return
        self.restart_failures.append(now)
        attempt = len(self.restart_failures)
        self.state.status, self.state.restart_attempt = "restart_wait", attempt
        await asyncio.sleep(RESTART_DELAYS[min(attempt - 1, len(RESTART_DELAYS) - 1)])
        if not self.stop_requested:
            await self.start(profile_id, attempt)

    async def stop(self) -> dict[str, Any]:
        async with self.lock:
            self.stop_requested = True
            proc = self.process
            if not proc or proc.returncode is not None:
                if self.monitor_task and not self.monitor_task.done() and self.monitor_task is not asyncio.current_task():
                    self.monitor_task.cancel()
                    await asyncio.gather(self.monitor_task, return_exceptions=True)
                self.process, self.state = None, ProcessState()
                return ok(asdict(self.state))
            self.state.status = "stopping"
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), STOP_TIMEOUT)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            await asyncio.gather(*self.log_tasks, return_exceptions=True)
            self.process, self.state = None, ProcessState()
            return ok(asdict(self.state))

    async def restart(self) -> dict[str, Any]:
        profile_id = self.state.profile_id or self.repository.state.get("selected_profile_id")
        if not profile_id:
            return fail("NO_PROFILE_SELECTED", "No profile is selected")
        await self.stop()
        return await self.start(profile_id)

    async def query(self, command: str) -> Any:
        if not self.running:
            return None
        proc = await asyncio.create_subprocess_exec(str(self.cli), "-p", RPC_ADDRESS, "-o", "json", command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), 3)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError(f"{command} query timed out")
        if proc.returncode:
            raise RuntimeError(stderr.decode("utf-8", "replace")[-1000:] or f"{command} query failed")
        return json.loads(stdout.decode("utf-8"))


class EasyTierManager:
    def __init__(self, settings_dir: Path | None = None, runtime_dir: Path | None = None, log_dir: Path | None = None, plugin_dir: Path | None = None):
        settings = settings_dir or Path(decky.DECKY_PLUGIN_SETTINGS_DIR)
        runtime = runtime_dir or Path(decky.DECKY_PLUGIN_RUNTIME_DIR)
        logs = log_dir or Path(decky.DECKY_PLUGIN_LOG_DIR)
        plugin = plugin_dir or Path(decky.DECKY_PLUGIN_DIR)
        self.repository = ProfileRepository(settings, runtime)
        self.log = RotatingLog(logs)
        self.process = EasyTierProcessManager(plugin / "bin/easytier-core", plugin / "bin/easytier-cli", self.repository, self.log)
        version_file = plugin / "bin/VERSION"
        self.binary_version = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else EASYTIER_VERSION

    async def initialize(self) -> None:
        self.repository.initialize()

    def state_data(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "binary_version": self.binary_version,
            "settings": dict(self.repository.state["settings"]),
            "profiles": self.repository.list_profiles(),
            "selected_profile_id": self.repository.state.get("selected_profile_id"),
            "process": asdict(self.process.state),
            "restart_required": self.process.restart_required,
        }

    async def runtime_snapshot(self, limit: int) -> dict[str, Any]:
        data = {"process": asdict(self.process.state), "node": None, "peers": [], "routes": [], "logs": self.log.tail(limit), "cli_error": None}
        if self.process.running:
            try:
                node, peers, routes = await asyncio.gather(self.process.query("node"), self.process.query("peer"), self.process.query("route"))
                data.update(node=node, peers=peers or [], routes=routes or [])
            except (RuntimeError, ValueError, json.JSONDecodeError) as error:
                data["cli_error"] = str(error)
        return data


class Plugin:
    def __init__(self):
        self.manager: EasyTierManager | None = None

    async def _main(self) -> None:
        self.manager = EasyTierManager()
        await self.manager.initialize()
        state = self.manager.repository.state
        if state["settings"].get("auto_start") and state.get("selected_profile_id"):
            asyncio.create_task(self.manager.process.start(state["selected_profile_id"]))

    async def _unload(self) -> None:
        if self.manager:
            await self.manager.process.stop()

    async def _uninstall(self) -> None:
        if self.manager:
            await self.manager.process.stop()
            shutil.rmtree(self.manager.repository.root, ignore_errors=True)
            shutil.rmtree(self.manager.log.dir, ignore_errors=True)

    async def get_state(self) -> dict[str, Any]:
        return ok(self.manager.state_data()) if self.manager else fail("NOT_READY", "Plugin is not initialized")

    async def get_profile(self, profile_id: str) -> dict[str, Any]:
        if not self.manager:
            return fail("NOT_READY", "Plugin is not initialized")
        profile = self.manager.repository.get_profile(profile_id)
        return ok(profile) if profile else fail("PROFILE_NOT_FOUND", "Profile not found")

    async def validate_profile(self, toml: str) -> dict[str, Any]:
        return await self.manager.process.validate(toml) if self.manager else fail("NOT_READY", "Plugin is not initialized")

    async def save_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        if not self.manager:
            return fail("NOT_READY", "Plugin is not initialized")
        validation = await self.manager.process.validate(profile.get("toml", ""))
        if not validation["success"]:
            return validation
        profile_id = profile.get("id")
        backup = self.manager.repository.get_profile(profile_id)
        try:
            meta = self.manager.repository.save_profile(profile.get("name", ""), profile.get("toml", ""), profile_id)
        except ValueError as error:
            return fail("INVALID_PROFILE", str(error))
        except KeyError:
            return fail("PROFILE_NOT_FOUND", "Profile not found")
        restart = bool(self.manager.process.running and profile_id == self.manager.process.state.profile_id)
        self.manager.process.restart_required = restart
        if restart and self.manager.process.pending_backup is None:
            self.manager.process.pending_backup = backup
        return ok({"profile": meta, "restart_required": restart})

    async def delete_profile(self, profile_id: str) -> dict[str, Any]:
        if not self.manager:
            return fail("NOT_READY", "Plugin is not initialized")
        if self.manager.process.running and self.manager.process.state.profile_id == profile_id:
            return fail("PROFILE_RUNNING", "Stop the active profile before deleting it")
        return ok({"deleted": self.manager.repository.delete_profile(profile_id)})

    async def select_profile(self, profile_id: str) -> dict[str, Any]:
        if not self.manager:
            return fail("NOT_READY", "Plugin is not initialized")
        if self.manager.process.running and self.manager.process.state.profile_id != profile_id:
            return fail("PROFILE_RUNNING", "Stop the active profile before selecting another one")
        try:
            self.manager.repository.select_profile(profile_id)
            return ok({"selected_profile_id": profile_id})
        except KeyError:
            return fail("PROFILE_NOT_FOUND", "Profile not found")

    async def start_profile(self, profile_id: str) -> dict[str, Any]:
        return await self.manager.process.start(profile_id) if self.manager else fail("NOT_READY", "Plugin is not initialized")

    async def stop_easytier(self) -> dict[str, Any]:
        return await self.manager.process.stop() if self.manager else fail("NOT_READY", "Plugin is not initialized")

    async def restart_easytier(self) -> dict[str, Any]:
        if not self.manager:
            return fail("NOT_READY", "Plugin is not initialized")
        active = self.manager.process.state.profile_id
        backup = self.manager.process.pending_backup
        result = await self.manager.process.restart()
        if result["success"]:
            await asyncio.sleep(0.5)
            if self.manager.process.running:
                self.manager.process.restart_required = False
                self.manager.process.pending_backup = None
                return result
            result = fail("RESTART_FAILED", "New configuration exited during startup")
        if backup and active:
            await self.manager.process.stop()
            self.manager.repository.save_profile(backup["name"], backup["toml"], active)
            rollback = await self.manager.process.start(active)
            detail = "Previous configuration restored" + ("; rollback start failed" if not rollback["success"] else "")
            return fail("RESTART_ROLLED_BACK", "New configuration failed to start", detail)
        return result

    async def get_runtime_snapshot(self, log_limit: int = 100) -> dict[str, Any]:
        return ok(await self.manager.runtime_snapshot(log_limit)) if self.manager else fail("NOT_READY", "Plugin is not initialized")

    async def save_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        return ok(self.manager.repository.save_settings(settings)) if self.manager else fail("NOT_READY", "Plugin is not initialized")
