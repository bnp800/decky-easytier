import os
import sys
import asyncio
import decky
import json
import urllib.request
import urllib.error
import socket
from typing import Dict, Optional

# Add py_modules to path for bundled dependencies
plugin_dir = os.path.dirname(os.path.abspath(__file__))
py_modules_path = os.path.join(plugin_dir, "py_modules")
if py_modules_path not in sys.path:
    sys.path.insert(0, py_modules_path)

# EasyTier配置
EASYTIER_GITHUB_REPO = "EasyTier/EasyTier"
EASYTIER_WEB_BINARY = "easytier-web-embed"
EASYTIER_CORE_BINARY = "easytier-core"

class DualProcessManager:
    """管理easytier-web和easytier-core两个进程"""

    def __init__(self, easytier_path: str):
        self.easytier_path = easytier_path
        self.web_process: Optional[asyncio.subprocess.Process] = None
        self.core_process: Optional[asyncio.subprocess.Process] = None
        self.web_status: str = "stopped"  # stopped, running, crashed
        self.core_status: str = "stopped"  # stopped, running, crashed
        self.monitor_task: Optional[asyncio.Task] = None
        self.auto_restart_core: bool = True

    async def start_both(self, ip_address: str = "127.0.0.1") -> Dict:
        """按顺序启动两个进程"""
        try:
            # 1. 检查二进制文件是否存在
            web_path = os.path.join(self.easytier_path, EASYTIER_WEB_BINARY)
            core_path = os.path.join(self.easytier_path, EASYTIER_CORE_BINARY)

            if not os.path.exists(web_path):
                decky.logger.error(f"{EASYTIER_WEB_BINARY} not found at {web_path}")
                return {"success": False, "error": f"{EASYTIER_WEB_BINARY} not found at {web_path}"}
            if not os.path.exists(core_path):
                decky.logger.error(f"{EASYTIER_CORE_BINARY} not found at {core_path}")
                return {"success": False, "error": f"{EASYTIER_CORE_BINARY} not found at {core_path}"}

            # 2. 启动web和配置服务器
            api_host = f"http://{ip_address}:11211"
            try:
                self.web_process = await asyncio.create_subprocess_exec(
                    web_path,
                    "--api-server-port", "11211",
                    "--api-host", api_host,
                    "--config-server-port", "22020",
                    "--config-server-protocol", "udp",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.easytier_path
                )
                self.web_status = "running"
                decky.logger.info(f"easytier-web started (PID: {self.web_process.pid})")
            except Exception as e:
                decky.logger.error(f"Failed to start web process: {e}")
                return {"success": False, "error": f"Failed to start web: {e}"}

            await asyncio.sleep(2)  # 等待配置服务器就绪

            # 3. 启动core节点
            try:
                self.core_process = await asyncio.create_subprocess_exec(
                    core_path,
                    "-w", "udp://127.0.0.1:22020/admin",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.easytier_path
                )
                self.core_status = "running"
                decky.logger.info(f"easytier-core started (PID: {self.core_process.pid})")
            except Exception as e:
                decky.logger.error(f"Failed to start core process: {e}")
                await self.stop_both()
                return {"success": False, "error": f"Failed to start core: {e}"}

            # 4. 启动监控任务
            self.monitor_task = asyncio.create_task(self.monitor_processes())

            decky.logger.info("EasyTier services started successfully")
            return {"success": True}

        except Exception as e:
            decky.logger.error(f"Failed to start EasyTier services: {e}")
            import traceback
            decky.logger.error(traceback.format_exc())
            await self.stop_both()
            return {"success": False, "error": str(e)}

    async def stop_both(self) -> Dict:
        """停止两个进程"""
        decky.logger.info("Stopping EasyTier services...")

        # 停止监控任务
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        # 先停止core（从节点）
        if self.core_process:
            try:
                self.core_process.terminate()
                await asyncio.wait_for(self.core_process.wait(), timeout=5)
                decky.logger.info("easytier-core stopped")
            except asyncio.TimeoutError:
                self.core_process.kill()
                decky.logger.warning("easytier-core killed")

        # 再停止web（主服务）
        if self.web_process:
            try:
                self.web_process.terminate()
                await asyncio.wait_for(self.web_process.wait(), timeout=5)
                decky.logger.info("easytier-web stopped")
            except asyncio.TimeoutError:
                self.web_process.kill()
                decky.logger.warning("easytier-web killed")

        self.web_status = "stopped"
        self.core_status = "stopped"
        return {"success": True}

    async def monitor_processes(self):
        """监控两个进程的状态"""
        while True:
            try:
                # 检查web进程
                if self.web_process:
                    if self.web_process.returncode is None:
                        # 检查是否仍在运行
                        try:
                            self.web_process.send_signal(0)
                        except ProcessLookupError:
                            self.web_status = "crashed"
                            decky.logger.error("easytier-web process crashed")
                            # core依赖web，停止core
                            if self.core_process:
                                self.core_process.terminate()
                                self.core_status = "stopped"
                            await self._emit_status()

                # 检查core进程
                if self.core_process:
                    if self.core_process.returncode is None:
                        try:
                            self.core_process.send_signal(0)
                        except ProcessLookupError:
                            self.core_status = "crashed"
                            decky.logger.error("easytier-core process crashed")
                            # 自动重启core
                            if self.auto_restart_core:
                                decky.logger.info("Restarting easytier-core...")
                                await self._restart_core()
                            await self._emit_status()

                await self._emit_status()
                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                decky.logger.error(f"Error in monitor task: {e}")
                await asyncio.sleep(5)

    async def _restart_core(self):
        """重启core进程"""
        try:
            core_path = os.path.join(self.easytier_path, EASYTIER_CORE_BINARY)
            self.core_process = await asyncio.create_subprocess_exec(
                core_path,
                "-w", "udp://127.0.0.1:22020/admin",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.easytier_path
            )
            self.core_status = "running"
            decky.logger.info("easytier-core restarted")
        except Exception as e:
            decky.logger.error(f"Failed to restart easytier-core: {e}")
            self.core_status = "error"

    async def _emit_status(self):
        """发送状态更新事件"""
        status = {
            "web_status": self.web_status,
            "core_status": self.core_status
        }
        await decky.emit("service_status", status)

    def get_status(self) -> Dict:
        """获取当前状态"""
        return {
            "web_status": self.web_status,
            "core_status": self.core_status
        }


class EasyTierManager:
    """EasyTier插件主管理类"""

    def __init__(self):
        self.easytier_path = os.path.join(decky.DECKY_PLUGIN_RUNTIME_DIR, "easytier")
        self.version_file = os.path.join(decky.DECKY_PLUGIN_RUNTIME_DIR, "easytier", "version.json")
        self.process_manager: Optional[DualProcessManager] = None
        self.ip_address: Optional[str] = None
        self.installed_version: Optional[str] = None
        self.latest_version: Optional[str] = None
        self._latest_version_ts: float = 0

    async def init(self):
        """初始化插件"""
        # 创建必要的目录
        try:
            os.makedirs(self.easytier_path, exist_ok=True)
            os.makedirs(decky.DECKY_PLUGIN_LOG_DIR, exist_ok=True)
        except Exception as e:
            decky.logger.error(f"Failed to create directories: {e}")
            raise

        # 初始化进程管理器
        self.process_manager = DualProcessManager(self.easytier_path)

        # 获取IP地址
        self.ip_address = self._get_local_ip()

        # 加载已安装版本
        self._load_installed_version()

        decky.logger.info(f"Plugin initialized. Runtime dir: {decky.DECKY_PLUGIN_RUNTIME_DIR}")

    async def install_easytier(self) -> Dict:
        """下载并安装最新版EasyTier二进制文件"""
        import zipfile
        try:
            decky.logger.info("Starting EasyTier installation...")

            # 检查存储空间（至少需要100MB）
            statvfs = os.statvfs(self.easytier_path)
            free_space = statvfs.f_frsize * statvfs.f_bavail
            if free_space < 100 * 1024 * 1024:
                return {"success": False, "error": "Insufficient disk space. Need at least 100MB."}

            # 获取最新版本号
            await decky.emit("install_progress", 5, "正在获取最新版本...")
            version = await self._fetch_latest_version()
            if not version:
                return {"success": False, "error": "无法获取最新版本信息，请检查网络连接"}

            decky.logger.info(f"Latest version: {version}")

            # 构建下载URL
            zip_name = f"easytier-linux-x86_64-v{version}.zip"
            zip_url = f"https://github.com/{EASYTIER_GITHUB_REPO}/releases/download/v{version}/{zip_name}"

            # 下载ZIP压缩包
            await decky.emit("install_progress", 20, f"正在下载 {zip_name}...")
            zip_path = os.path.join(self.easytier_path, zip_name)
            if not await self._download_file(zip_url, zip_path):
                return {"success": False, "error": f"Failed to download {zip_name}"}

            # 解压ZIP文件
            await decky.emit("install_progress", 60, "正在解压...")
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(self.easytier_path)
                decky.logger.info(f"Extracted ZIP to {self.easytier_path}")
            except Exception as e:
                decky.logger.error(f"Failed to extract ZIP: {e}")
                return {"success": False, "error": f"Failed to extract ZIP: {e}"}
            finally:
                if os.path.exists(zip_path):
                    os.remove(zip_path)

            # ZIP解压后文件在子目录中，需要移动到正确位置
            import shutil
            extracted_dir = os.path.join(self.easytier_path, "easytier-linux-x86_64")
            if os.path.exists(extracted_dir):
                decky.logger.info(f"Moving files from {extracted_dir} to {self.easytier_path}")
                for filename in os.listdir(extracted_dir):
                    src = os.path.join(extracted_dir, filename)
                    dst = os.path.join(self.easytier_path, filename)
                    if os.path.isfile(src):
                        shutil.move(src, dst)
                        decky.logger.info(f"Moved {filename}")
                os.rmdir(extracted_dir)

            # 设置执行权限
            web_path = os.path.join(self.easytier_path, EASYTIER_WEB_BINARY)
            core_path = os.path.join(self.easytier_path, EASYTIER_CORE_BINARY)

            if os.path.exists(web_path):
                os.chmod(web_path, 0o755)
            else:
                return {"success": False, "error": f"{EASYTIER_WEB_BINARY} not found in extracted archive"}

            if os.path.exists(core_path):
                os.chmod(core_path, 0o755)
            else:
                return {"success": False, "error": f"{EASYTIER_CORE_BINARY} not found in extracted archive"}

            # 保存版本信息
            self._save_installed_version(version)

            await decky.emit("install_progress", 100, "安装完成!")
            decky.logger.info(f"EasyTier v{version} installed successfully")
            return {"success": True}

        except Exception as e:
            decky.logger.error(f"Installation failed: {e}")
            import traceback
            decky.logger.error(f"Traceback: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def _download_file(self, url: str, dest_path: str) -> bool:
        """下载文件（禁用SSL验证以解决证书问题）"""
        try:
            decky.logger.info(f"Downloading from {url}...")

            # 创建SSL上下文，禁用证书验证
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # 使用自定义SSL上下文下载
            req = urllib.request.Request(url, headers={'User-Agent': 'DeckyEasyTier/1.0'})
            with urllib.request.urlopen(req, context=ssl_context, timeout=60) as response:
                with open(dest_path, 'wb') as out_file:
                    out_file.write(response.read())

            # 验证文件大小（至少应该有5MB）
            file_size = os.path.getsize(dest_path)
            decky.logger.info(f"Downloaded file size: {file_size} bytes")
            if file_size < 5 * 1024 * 1024:  # 5MB minimum for ZIP
                decky.logger.error(f"File too small ({file_size} bytes), deleting...")
                os.remove(dest_path)
                return False

            return True
        except Exception as e:
            decky.logger.error(f"Download error: {e}")
            import traceback
            decky.logger.error(f"Download traceback: {traceback.format_exc()}")
            return False

    async def start_easytier(self) -> Dict:
        """启动EasyTier服务"""
        if not self.process_manager:
            return {"success": False, "error": "Process manager not initialized"}

        # 启动前刷新IP地址
        self.ip_address = self._get_local_ip()

        # 启动服务，传递IP地址以便api-host使用
        result = await self.process_manager.start_both(self.ip_address)

        if result["success"]:
            decky.logger.info("EasyTier services started successfully")
        else:
            decky.logger.error(f"Failed to start services: {result.get('error', 'Unknown error')}")

        return result

    async def stop_easytier(self) -> Dict:
        """停止EasyTier服务"""
        if not self.process_manager:
            return {"success": False, "error": "Process manager not initialized"}

        return await self.process_manager.stop_both()

    async def get_combined_status(self) -> Dict:
        """获取组合状态"""
        # 每次查询时刷新IP地址
        self.ip_address = self._get_local_ip()

        if not self.process_manager:
            # 检查是否已安装
            web_path = os.path.join(self.easytier_path, EASYTIER_WEB_BINARY)
            core_path = os.path.join(self.easytier_path, EASYTIER_CORE_BINARY)

            if not os.path.exists(web_path) or not os.path.exists(core_path):
                return {
                    "overall": "uninstalled",
                    "ip": self.ip_address
                }

            return {
                "overall": "stopped",
                "ip": self.ip_address,
                "installed_version": self.installed_version
            }

        # 检查二进制文件是否存在（即使process_manager已初始化）
        web_path = os.path.join(self.easytier_path, EASYTIER_WEB_BINARY)
        core_path = os.path.join(self.easytier_path, EASYTIER_CORE_BINARY)
        if not os.path.exists(web_path) or not os.path.exists(core_path):
            return {
                "overall": "uninstalled",
                "ip": self.ip_address
            }

        # 获取进程状态
        process_status = self.process_manager.get_status()
        web_status = process_status["web_status"]
        core_status = process_status["core_status"]

        # 计算总体状态
        if web_status == "stopped" and core_status == "stopped":
            overall = "stopped"
        elif web_status == "running" and core_status == "running":
            overall = "running"
        elif web_status == "running" and core_status == "stopped":
            overall = "partial"
        else:
            overall = "error"

        return {
            "overall": overall,
            "web_status": web_status,
            "core_status": core_status,
            "ip": self.ip_address,
            "installed_version": self.installed_version
        }


    async def _fetch_latest_version(self) -> Optional[str]:
        """通过GitHub releases redirect获取最新版本号（不消耗API配额）"""
        import time

        # 缓存30分钟，避免频繁请求
        if (self.latest_version and self._latest_version_ts
                and time.time() - self._latest_version_ts < 1800):
            return self.latest_version

        try:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # HEAD请求 /releases/latest 会302重定向到 /releases/tag/vX.Y.Z
            url = f"https://github.com/{EASYTIER_GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(url, method='HEAD', headers={
                'User-Agent': 'DeckyEasyTier/1.0'
            })

            class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    self.redirect_url = newurl
                    return None

            handler = NoRedirectHandler()
            opener = urllib.request.build_opener(
                handler,
                urllib.request.HTTPSHandler(context=ssl_context)
            )

            try:
                opener.open(req, timeout=10)
            except urllib.error.HTTPError:
                pass

            redirect_url = getattr(handler, 'redirect_url', '')
            if redirect_url and '/tag/' in redirect_url:
                tag = redirect_url.split('/tag/')[-1]
                version = tag.lstrip('v')
                self.latest_version = version
                self._latest_version_ts = time.time()
                decky.logger.info(f"Latest EasyTier version: {version}")
                return version

            decky.logger.warning("Could not parse version from redirect")
            return self.latest_version
        except Exception as e:
            decky.logger.error(f"Failed to fetch latest version: {e}")
            return self.latest_version

    def _load_installed_version(self):
        """从版本文件加载已安装版本，如无则尝试从二进制检测"""
        try:
            if os.path.exists(self.version_file):
                with open(self.version_file, 'r') as f:
                    data = json.load(f)
                    self.installed_version = data.get("version")
                    decky.logger.info(f"Installed version: {self.installed_version}")
                    return
        except Exception as e:
            decky.logger.warning(f"Failed to load version file: {e}")

        # 没有版本文件，尝试从二进制检测
        core_path = os.path.join(self.easytier_path, EASYTIER_CORE_BINARY)
        if os.path.exists(core_path):
            try:
                import subprocess
                result = subprocess.run(
                    [core_path, "--version"],
                    capture_output=True, text=True, timeout=5
                )
                # 输出格式通常为 "easytier-core x.y.z" 或 "x.y.z"
                output = result.stdout.strip()
                if output:
                    # 取最后一个空格后的部分作为版本号
                    version = output.split()[-1].lstrip('v')
                    self.installed_version = version
                    self._save_installed_version(version)
                    decky.logger.info(f"Detected version from binary: {version}")
            except Exception as e:
                decky.logger.warning(f"Failed to detect version from binary: {e}")

    def _save_installed_version(self, version: str):
        """保存已安装版本到文件"""
        try:
            with open(self.version_file, 'w') as f:
                json.dump({"version": version}, f)
            self.installed_version = version
            decky.logger.info(f"Saved installed version: {version}")
        except Exception as e:
            decky.logger.error(f"Failed to save version file: {e}")

    async def check_update(self) -> Dict:
        """检查是否有新版本"""
        latest = await self._fetch_latest_version()
        return {
            "installed_version": self.installed_version,
            "latest_version": latest,
            "update_available": bool(latest and self.installed_version and latest != self.installed_version)
        }

    def _get_local_ip(self) -> str:
        """智能获取本地IP地址"""
        try:
            # 尝试连接一个公共地址获取本机IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()

            # 如果是私有IP，优先返回
            if ip.startswith(("10.", "192.168.", "172.")):
                return ip

            # 否则枚举所有接口，查找私有IP
            import netifaces
            for iface in netifaces.interfaces():
                for addr in netifaces.ifaddresses(iface).get(netifaces.AF_INET, []):
                    ip = addr['addr']
                    if ip.startswith(("10.", "192.168.", "172.")):
                        return ip
            return ip
        except:
            return "localhost"

    async def cleanup(self):
        """清理资源"""
        if self.process_manager:
            await self.process_manager.stop_both()


class Plugin:
    """Decky插件主类"""

    def __init__(self):
        self.manager: Optional[EasyTierManager] = None

    # ========== 插件生命周期 ==========

    async def _main(self):
        """插件加载时初始化"""
        decky.logger.info("=== Decky EasyTier Plugin Starting ===")

        try:
            self.manager = EasyTierManager()
            await self.manager.init()
        except Exception as e:
            decky.logger.error(f"Failed to initialize plugin: {e}")
            import traceback
            decky.logger.error(traceback.format_exc())
            raise

    async def _unload(self):
        """插件卸载时清理"""
        decky.logger.info("=== Decky EasyTier Plugin Unloading ===")

        if self.manager:
            await self.manager.cleanup()

    async def _uninstall(self):
        """插件卸载时清理所有文件"""
        decky.logger.info("=== Decky EasyTier Plugin Uninstalling ===")

        if self.manager:
            await self.manager.cleanup()

        # 删除二进制文件和配置
        try:
            import shutil
            if os.path.exists(self.manager.easytier_path):
                shutil.rmtree(self.manager.easytier_path)
            decky.logger.info("All plugin files removed")
        except Exception as e:
            decky.logger.error(f"Failed to remove plugin files: {e}")

    async def _migration(self):
        """数据迁移（如果插件版本变化）"""
        pass

    # ========== 前端可调用的API ==========

    async def get_combined_status(self) -> Dict:
        """获取组合状态（前端调用）"""
        if self.manager:
            return await self.manager.get_combined_status()
        return {"overall": "error", "error": "Manager not initialized"}

    async def install_easytier(self) -> Dict:
        """安装EasyTier（前端调用）"""
        if self.manager:
            return await self.manager.install_easytier()
        return {"success": False, "error": "Manager not initialized"}

    async def start_easytier(self) -> Dict:
        """启动EasyTier（前端调用）"""
        if self.manager:
            try:
                return await self.manager.start_easytier()
            except Exception as e:
                decky.logger.error(f"Failed to start EasyTier: {e}")
                import traceback
                decky.logger.error(traceback.format_exc())
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Manager not initialized"}

    async def stop_easytier(self) -> Dict:
        """停止EasyTier（前端调用）"""
        if self.manager:
            return await self.manager.stop_easytier()
        return {"success": False, "error": "Manager not initialized"}

    async def check_update(self) -> Dict:
        """检查更新（前端调用）"""
        if self.manager:
            return await self.manager.check_update()
        return {"installed_version": None, "latest_version": None, "update_available": False}

    async def update_easytier(self) -> Dict:
        """更新EasyTier（前端调用），需先停止服务"""
        if self.manager:
            # 如果服务正在运行，先停止
            if self.manager.process_manager:
                status = self.manager.process_manager.get_status()
                if status["web_status"] == "running" or status["core_status"] == "running":
                    await self.manager.stop_easytier()
            return await self.manager.install_easytier()
        return {"success": False, "error": "Manager not initialized"}
