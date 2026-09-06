import asyncio
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

decky = SimpleNamespace(
    DECKY_PLUGIN_SETTINGS_DIR="/tmp/settings",
    DECKY_PLUGIN_RUNTIME_DIR="/tmp/runtime",
    DECKY_PLUGIN_LOG_DIR="/tmp/logs",
    DECKY_PLUGIN_DIR="/tmp/plugin",
    logger=Mock(),
)
sys.modules.setdefault("decky", decky)
import main

VALID_TOML = 'hostname = "deck"\ndhcp = true\n[network_identity]\nnetwork_name = "test"\nnetwork_secret = "secret-value"\n'


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.settings, self.runtime = root / "settings", root / "runtime"
        self.settings.mkdir(); self.runtime.mkdir()
        self.repo = main.ProfileRepository(self.settings, self.runtime)
        self.repo.initialize()

    def tearDown(self): self.temp.cleanup()

    def test_crud_selection_and_permissions(self):
        first = self.repo.save_profile("Home", VALID_TOML)
        second = self.repo.save_profile("Travel", VALID_TOML.replace("test", "travel"))
        self.assertEqual(self.repo.state["selected_profile_id"], first["id"])
        self.repo.select_profile(second["id"])
        self.assertEqual(self.repo.get_profile(second["id"])["name"], "Travel")
        self.assertEqual(stat.S_IMODE(self.repo.profile_path(first["id"]).stat().st_mode), 0o600)
        with self.assertRaises(ValueError): self.repo.save_profile("home", VALID_TOML)
        self.assertTrue(self.repo.delete_profile(second["id"]))

    def test_legacy_reset(self):
        legacy = self.runtime / "easytier"; legacy.mkdir(); (legacy / "easytier-web").write_text("old")
        (self.settings / "config.json").write_text("{}")
        self.repo.state_path.write_text(json.dumps({"schema_version": 1}))
        self.repo.initialize()
        self.assertFalse(legacy.exists())
        self.assertFalse((self.settings / "config.json").exists())
        self.assertEqual(self.repo.state["schema_version"], 2)

    def test_log_redaction_and_limit(self):
        log = main.RotatingLog(Path(self.temp.name) / "logs")
        log.write("secret-value connected", ["secret-value"])
        self.assertEqual(log.tail(999), ["<redacted> connected"])

    def test_log_rotation(self):
        log = main.RotatingLog(Path(self.temp.name) / "rotating")
        with patch.object(main, "MAX_LOG_BYTES", 5):
            log.write("first")
            log.write("second")
        self.assertTrue((log.dir / "easytier.log.1").exists())


class ProcessTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(); root = Path(self.temp.name)
        for name in ("settings", "runtime", "logs", "plugin/bin"): (root / name).mkdir(parents=True)
        self.root = root
        self.repo = main.ProfileRepository(root / "settings", root / "runtime"); self.repo.initialize()
        self.profile = self.repo.save_profile("Test", VALID_TOML)
        core = root / "plugin/bin/easytier-core"; cli = root / "plugin/bin/easytier-cli"
        core.write_text("#!/bin/sh\ncase \"$1\" in --check-config) grep -q INVALID \"$3\" && exit 2; exit 0;; esac\ntrap 'exit 0' TERM\necho 'secret-value connected'\nwhile :; do sleep 1; done\n")
        cli.write_text("#!/bin/sh\ncase \"$5\" in node) echo '{\"virtual_ip\":\"10.1.1.1\"}';; peer) echo '[{\"hostname\":\"peer\"}]';; route) echo '[{\"ipv4\":\"10.1.1.2\"}]';; esac\n")
        core.chmod(0o755); cli.chmod(0o755)
        self.manager = main.EasyTierProcessManager(core, cli, self.repo, main.RotatingLog(root / "logs"))

    async def asyncTearDown(self):
        await self.manager.stop(); self.temp.cleanup()

    async def test_validation_start_query_stop(self):
        self.assertTrue((await self.manager.validate(VALID_TOML))["success"])
        self.assertFalse((await self.manager.validate("INVALID"))["success"])
        self.assertTrue((await self.manager.start(self.profile["id"]))["success"])
        await asyncio.sleep(0.05)
        self.assertEqual((await self.manager.query("node"))["virtual_ip"], "10.1.1.1")
        self.assertIn("<redacted>", "\n".join(self.manager.log.tail(20)))
        await self.manager.stop()
        self.assertEqual(self.manager.state.status, "stopped")

    async def test_only_one_profile_runs(self):
        other = self.repo.save_profile("Other", VALID_TOML)
        await self.manager.start(self.profile["id"])
        result = await self.manager.start(other["id"])
        self.assertEqual(result["error"]["code"], "ALREADY_RUNNING")

    async def test_malformed_cli_output(self):
        await self.manager.start(self.profile["id"])
        self.manager.cli.write_text("#!/bin/sh\necho not-json\n")
        self.manager.cli.chmod(0o755)
        with self.assertRaises(json.JSONDecodeError):
            await self.manager.query("node")

    async def test_stop_escalates_when_term_is_ignored(self):
        await self.manager.stop()
        self.manager.core.write_text("#!/bin/sh\n[ \"$1\" = --check-config ] && exit 0\ntrap '' TERM\nwhile :; do sleep 1; done\n")
        self.manager.core.chmod(0o755)
        await self.manager.start(self.profile["id"])
        with patch.object(main, "STOP_TIMEOUT", 0.05):
            result = await self.manager.stop()
        self.assertTrue(result["success"])
        self.assertEqual(self.manager.state.status, "stopped")

    async def test_restart_limit(self):
        await self.manager.stop()
        self.manager.core.write_text("#!/bin/sh\n[ \"$1\" = --check-config ] && exit 0\nexit 9\n")
        self.manager.core.chmod(0o755)
        with patch.object(main, "RESTART_DELAYS", (0, 0, 0, 0, 0, 0)):
            await self.manager.start(self.profile["id"])
            for _ in range(100):
                if self.manager.state.status == "error": break
                await asyncio.sleep(0.01)
        self.assertEqual(self.manager.state.status, "error")
        self.assertIn("5 failures", self.manager.state.error)


if __name__ == "__main__": unittest.main()
