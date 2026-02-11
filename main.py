import os
import sys
import asyncio
import decky
import json
import urllib.request
import urllib.error
import stat
import socket
import subprocess
from typing import Dict, Optional, Tuple
from pathlib import Path

# Add py_modules to path for bundled dependencies
plugin_dir = os.path.dirname(os.path.abspath(__file__))
py_modules_path = os.path.join(plugin_dir, "py_modules")
if py_modules_path not in sys.path:
    sys.path.insert(0, py_modules_path)

# EasyTier下载配置
EASYTIER_VERSION = "2.5.0"
EASYTIER_RELEASES_URL = f"https://github.com/EasyTier/EasyTier/releases/download/v{EASYTIER_VERSION}"
EASYTIER_WEB_BINARY = "easytier-web-embed"
EASYTIER_CORE_BINARY = "easytier-core"
# Steam Deck uses x86_64 architecture, download the ZIP archive
EASYTIER_ZIP_NAME = f"easytier-linux-x86_64-v{EASYTIER_VERSION}.zip"
EASYTIER_ZIP_URL = f"{EASYTIER_RELEASES_URL}/{EASYTIER_ZIP_NAME}"

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
            decky.logger.info("[DEBUG] Starting EasyTier Web service...")
            decky.logger.info(f"[DEBUG] easytier_path: {self.easytier_path}")
            decky.logger.info(f"[DEBUG] Using IP address for API host: {ip_address}")

            # 1. 检查二进制文件是否存在
            web_path = os.path.join(self.easytier_path, EASYTIER_WEB_BINARY)
            core_path = os.path.join(self.easytier_path, EASYTIER_CORE_BINARY)

            decky.logger.info(f"[DEBUG] web_path: {web_path}, exists: {os.path.exists(web_path)}")
            decky.logger.info(f"[DEBUG] core_path: {core_path}, exists: {os.path.exists(core_path)}")

            if not os.path.exists(web_path):
                decky.logger.error(f"[DEBUG] {EASYTIER_WEB_BINARY} not found at {web_path}")
                return {"success": False, "error": f"{EASYTIER_WEB_BINARY} not found at {web_path}"}
            if not os.path.exists(core_path):
                decky.logger.error(f"[DEBUG] {EASYTIER_CORE_BINARY} not found at {core_path}")
                return {"success": False, "error": f"{EASYTIER_CORE_BINARY} not found at {core_path}"}

            # 2. 启动web和配置服务器
            decky.logger.info(f"[DEBUG] Starting web process: {web_path}")
            api_host = f"http://{ip_address}:11211"
            decky.logger.info(f"[DEBUG] API host will be: {api_host}")
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
                decky.logger.info(f"[DEBUG] Web process started with PID: {self.web_process.pid}")
            except Exception as e:
                decky.logger.error(f"[DEBUG] Failed to start web process: {e}")
                return {"success": False, "error": f"Failed to start web: {e}"}

            decky.logger.info("[DEBUG] Waiting for config server to be ready...")
            await asyncio.sleep(2)  # 等待配置服务器就绪

            # 3. 启动core节点
            decky.logger.info(f"[DEBUG] Starting core process: {core_path}")
            try:
                self.core_process = await asyncio.create_subprocess_exec(
                    core_path,
                    "-w", "udp://127.0.0.1:22020/deck",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.easytier_path
                )
                self.core_status = "running"
                decky.logger.info(f"[DEBUG] Core process started with PID: {self.core_process.pid}")
            except Exception as e:
                decky.logger.error(f"[DEBUG] Failed to start core process: {e}")
                await self.stop_both()
                return {"success": False, "error": f"Failed to start core: {e}"}

            # 4. 启动监控任务
            decky.logger.info("[DEBUG] Starting monitor task")
            self.monitor_task = asyncio.create_task(self.monitor_processes())

            decky.logger.info("[DEBUG] EasyTier services started successfully")
            return {"success": True}

        except Exception as e:
            decky.logger.error(f"[DEBUG] Exception in start_both: {e}")
            import traceback
            decky.logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
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
                "-w", "udp://127.0.0.1:22020/deck",
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
        #decky.logger.info(f"[DEBUG] DualProcessManager.get_status: web={self.web_status}, core={self.core_status}")
        return {
            "web_status": self.web_status,
            "core_status": self.core_status
        }


class EasyTierManager:
    """EasyTier插件主管理类"""

    def __init__(self):
        self.easytier_path = os.path.join(decky.DECKY_PLUGIN_RUNTIME_DIR, "easytier")
        self.config_path = os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, "config.json")
        self.plugin_settings = {
            "auto_start": False,
            "log_level": "info",
            "auto_restart_core": True
        }
        self.process_manager: Optional[DualProcessManager] = None
        self.ip_address: Optional[str] = None
        self.qr_code: Optional[str] = None

    async def init(self):
        """初始化插件"""
        decky.logger.info("[DEBUG] Initializing Decky EasyTier plugin...")
        decky.logger.info(f"[DEBUG] easytier_path: {self.easytier_path}")
        decky.logger.info(f"[DEBUG] config_path: {self.config_path}")

        # 创建必要的目录
        try:
            os.makedirs(self.easytier_path, exist_ok=True)
            os.makedirs(decky.DECKY_PLUGIN_LOG_DIR, exist_ok=True)
            decky.logger.info("[DEBUG] Directories created successfully")
        except Exception as e:
            decky.logger.error(f"[DEBUG] Failed to create directories: {e}")
            raise

        # 加载配置
        decky.logger.info("[DEBUG] Loading plugin settings...")
        await self.load_plugin_settings()
        decky.logger.info(f"[DEBUG] Plugin settings loaded: {self.plugin_settings}")

        # 初始化进程管理器
        decky.logger.info("[DEBUG] Initializing DualProcessManager...")
        self.process_manager = DualProcessManager(self.easytier_path)
        self.process_manager.auto_restart_core = self.plugin_settings.get("auto_restart_core", True)
        decky.logger.info("[DEBUG] DualProcessManager initialized")

        # 获取IP地址
        self.ip_address = self._get_local_ip()

        decky.logger.info(f"Plugin initialized. Runtime dir: {decky.DECKY_PLUGIN_RUNTIME_DIR}")

    async def install_easytier(self) -> Dict:
        """下载并安装EasyTier二进制文件（从ZIP解压）"""
        import zipfile
        try:
            decky.logger.info("Starting EasyTier installation...")

            # 检查存储空间（至少需要100MB）
            statvfs = os.statvfs(self.easytier_path)
            free_space = statvfs.f_frsize * statvfs.f_bavail
            if free_space < 100 * 1024 * 1024:  # 100MB
                return {"success": False, "error": "Insufficient disk space. Need at least 100MB."}

            # 下载ZIP压缩包
            await decky.emit("install_progress", 20, f"Downloading {EASYTIER_ZIP_NAME}...")
            zip_path = os.path.join(self.easytier_path, EASYTIER_ZIP_NAME)
            if not await self._download_file(EASYTIER_ZIP_URL, zip_path):
                return {"success": False, "error": f"Failed to download {EASYTIER_ZIP_NAME}"}

            # 解压ZIP文件
            await decky.emit("install_progress", 60, "Extracting binaries...")
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(self.easytier_path)
                decky.logger.info(f"Extracted ZIP to {self.easytier_path}")
            except Exception as e:
                decky.logger.error(f"Failed to extract ZIP: {e}")
                return {"success": False, "error": f"Failed to extract ZIP: {e}"}
            finally:
                # 删除ZIP文件
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
                # 删除空目录
                os.rmdir(extracted_dir)

            # 设置执行权限
            web_path = os.path.join(self.easytier_path, EASYTIER_WEB_BINARY)
            core_path = os.path.join(self.easytier_path, EASYTIER_CORE_BINARY)

            if os.path.exists(web_path):
                os.chmod(web_path, 0o755)
                decky.logger.info(f"Set executable permission for {EASYTIER_WEB_BINARY}")
            else:
                return {"success": False, "error": f"{EASYTIER_WEB_BINARY} not found in extracted archive"}

            if os.path.exists(core_path):
                os.chmod(core_path, 0o755)
                decky.logger.info(f"Set executable permission for {EASYTIER_CORE_BINARY}")
            else:
                return {"success": False, "error": f"{EASYTIER_CORE_BINARY} not found in extracted archive"}

            await decky.emit("install_progress", 100, "Installation complete!")
            decky.logger.info("EasyTier installation completed successfully")
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
        decky.logger.info("[DEBUG] start_easytier called")

        if not self.process_manager:
            decky.logger.error("[DEBUG] Process manager not initialized")
            return {"success": False, "error": "Process manager not initialized"}

        # 生成二维码
        decky.logger.info("[DEBUG] Generating QR code...")
        try:
            self.qr_code = await self.generate_qr_code()
            decky.logger.info(f"[DEBUG] QR code generated: {self.qr_code is not None}")
        except Exception as e:
            decky.logger.warning(f"[DEBUG] Failed to generate QR code: {e}")
            self.qr_code = None

        # 启动服务，传递IP地址以便api-host使用
        decky.logger.info("[DEBUG] Calling process_manager.start_both() with IP: {}".format(self.ip_address))
        result = await self.process_manager.start_both(self.ip_address)
        decky.logger.info(f"[DEBUG] start_both returned: {result}")

        if result["success"]:
            decky.logger.info("[DEBUG] Services started successfully, starting node registration monitor")
            # 开始监控节点注册
            asyncio.create_task(self._monitor_node_registration())
        else:
            decky.logger.error(f"[DEBUG] Failed to start services: {result.get('error', 'Unknown error')}")

        return result

    async def stop_easytier(self) -> Dict:
        """停止EasyTier服务"""
        if not self.process_manager:
            return {"success": False, "error": "Process manager not initialized"}

        return await self.process_manager.stop_both()

    async def get_combined_status(self) -> Dict:
        """获取组合状态"""
        # decky.logger.debug("[DEBUG] get_combined_status called")

        if not self.process_manager:
            decky.logger.info("[DEBUG] Process manager not initialized, checking installation status")
            # 检查是否已安装
            web_path = os.path.join(self.easytier_path, EASYTIER_WEB_BINARY)
            core_path = os.path.join(self.easytier_path, EASYTIER_CORE_BINARY)

            web_exists = os.path.exists(web_path)
            core_exists = os.path.exists(core_path)
            decky.logger.info(f"[DEBUG] web exists: {web_exists}, core exists: {core_exists}")

            if not web_exists or not core_exists:
                return {
                    "overall": "uninstalled",
                    "ip": self.ip_address,
                    "plugin_settings": self.plugin_settings
                }

            decky.logger.info("[DEBUG] Returning 'stopped' status (process_manager exists but not running)")
            return {
                "overall": "stopped",
                "ip": self.ip_address,
                "plugin_settings": self.plugin_settings
            }

        # 检查二进制文件是否存在（即使process_manager已初始化）
        web_path = os.path.join(self.easytier_path, EASYTIER_WEB_BINARY)
        core_path = os.path.join(self.easytier_path, EASYTIER_CORE_BINARY)
        if not os.path.exists(web_path) or not os.path.exists(core_path):
            return {
                "overall": "uninstalled",
                "ip": self.ip_address,
                "plugin_settings": self.plugin_settings
            }

        # 获取进程状态
        #decky.logger.info("[DEBUG] Getting process status from DualProcessManager")
        process_status = self.process_manager.get_status()
        web_status = process_status["web_status"]
        core_status = process_status["core_status"]
        #decky.logger.info(f"[DEBUG] Process status: web={web_status}, core={core_status}")

        # 计算总体状态
        if web_status == "stopped" and core_status == "stopped":
            overall = "stopped"
        elif web_status == "running" and core_status == "running":
            overall = "running"
        elif web_status == "running" and core_status == "stopped":
            overall = "partial"
        else:
            overall = "error"

        #decky.logger.info(f"[DEBUG] Returning status: overall={overall}")
        return {
            "overall": overall,
            "web_status": web_status,
            "core_status": core_status,
            "ip": self.ip_address,
            "qr_code": self.qr_code,
            "plugin_settings": self.plugin_settings
        }

    async def save_plugin_settings(self, settings: Dict) -> Dict:
        """保存插件设置"""
        try:
            self.plugin_settings.update(settings)
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            with open(self.config_path, 'w') as f:
                json.dump({"plugin_settings": self.plugin_settings}, f, indent=2)

            # 更新进程管理器设置
            if self.process_manager:
                self.process_manager.auto_restart_core = self.plugin_settings.get("auto_restart_core", True)

            decky.logger.info("Plugin settings saved")
            return {"success": True}
        except Exception as e:
            decky.logger.error(f"Failed to save settings: {e}")
            return {"success": False, "error": str(e)}

    async def load_plugin_settings(self):
        """加载插件设置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    if "plugin_settings" in data:
                        self.plugin_settings.update(data["plugin_settings"])

            decky.logger.info("Plugin settings loaded")
        except Exception as e:
            decky.logger.warning(f"Failed to load settings, using defaults: {e}")

    async def generate_qr_code(self) -> Optional[str]:
        """生成Web控制台二维码（使用SVG格式，无需PIL依赖）"""
        try:
            # 动态导入qrcode，如果不存在则返回None
            try:
                import qrcode
                from qrcode.image.svg import SvgImage
            except ImportError:
                decky.logger.warning("qrcode module not available, skipping QR generation")
                return None

            # 生成二维码
            url = f"http://{self.ip_address}:11211"
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            # 使用SVG格式，无需PIL依赖
            img = qr.make_image(image_factory=SvgImage)

            # 转换为base64（SVG是文本格式）
            import io
            import base64
            buffer = io.BytesIO()
            img.save(buffer)
            svg_data = buffer.getvalue().decode('utf-8')
            return base64.b64encode(svg_data.encode('utf-8')).decode()

        except Exception as e:
            decky.logger.error(f"Failed to generate QR code: {e}")
            return None

    async def _monitor_node_registration(self):
        """监控core节点是否成功注册到web"""
        retry_count = 0
        max_retries = 10  # 最多等待50秒

        while retry_count < max_retries:
            try:
                # 使用同步 urllib 在线程中执行
                import urllib.request
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: urllib.request.urlopen("http://127.0.0.1:11211/api/nodes", timeout=5)
                )
                if response.status == 200:
                    data = response.read().decode('utf-8')
                    nodes = json.loads(data)
                    # 查找deck节点
                    for node in nodes:
                        if node.get('username') == 'deck':
                            # 节点已注册
                            await decky.emit("node_registered", True)
                            decky.logger.info("Core node registered to Web console")
                            return
            except Exception as e:
                decky.logger.debug(f"Failed to check node registration: {e}")

            retry_count += 1
            await asyncio.sleep(5)

        # 超时未注册
        decky.logger.warning("Core node registration timeout")
        await decky.emit("node_registered", False)

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
            decky.logger.info("[DEBUG] Creating EasyTierManager...")
            self.manager = EasyTierManager()
            decky.logger.info("[DEBUG] EasyTierManager created, calling init()...")
            await self.manager.init()
            decky.logger.info("[DEBUG] EasyTierManager init() completed")

            # 如果设置了自动启动，则启动服务
            if self.manager.plugin_settings.get("auto_start", False):
                decky.logger.info("[DEBUG] Auto-start enabled, starting EasyTier services...")
                asyncio.create_task(self.manager.start_easytier())
            else:
                decky.logger.info("[DEBUG] Auto-start disabled")
        except Exception as e:
            decky.logger.error(f"[DEBUG] Exception in _main: {e}")
            import traceback
            decky.logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
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
            if os.path.exists(self.manager.config_path):
                os.remove(self.manager.config_path)
            decky.logger.info("All plugin files removed")
        except Exception as e:
            decky.logger.error(f"Failed to remove plugin files: {e}")

    async def _migration(self):
        """数据迁移（如果插件版本变化）"""
        decky.logger.info("Checking for data migration...")

        # 迁移旧版本的日志和设置
        decky.migrate_logs(os.path.join(decky.DECKY_PLUGIN_RUNTIME_DIR, "easytier", "plugin.log"))
        decky.migrate_settings(
            os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, "config.json"),
            os.path.dirname(decky.DECKY_PLUGIN_SETTINGS_DIR)
        )
        decky.migrate_runtime(
            os.path.join(decky.DECKY_PLUGIN_RUNTIME_DIR, "easytier"),
            decky.DECKY_PLUGIN_RUNTIME_DIR
        )

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
        decky.logger.info("[DEBUG] Plugin.start_easytier called by frontend")
        if self.manager:
            try:
                result = await self.manager.start_easytier()
                decky.logger.info(f"[DEBUG] Plugin.start_easytier returning: {result}")
                return result
            except Exception as e:
                decky.logger.error(f"[DEBUG] Exception in Plugin.start_easytier: {e}")
                import traceback
                decky.logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
                return {"success": False, "error": str(e)}
        decky.logger.error("[DEBUG] Manager not initialized")
        return {"success": False, "error": "Manager not initialized"}

    async def stop_easytier(self) -> Dict:
        """停止EasyTier（前端调用）"""
        if self.manager:
            return await self.manager.stop_easytier()
        return {"success": False, "error": "Manager not initialized"}

    async def save_plugin_settings(self, settings: Dict) -> Dict:
        """保存插件设置（前端调用）"""
        if self.manager:
            return await self.manager.save_plugin_settings(settings)
        return {"success": False, "error": "Manager not initialized"}

    async def load_plugin_settings(self) -> Dict:
        """加载插件设置（前端调用）"""
        if self.manager:
            return {"success": True, "settings": self.manager.plugin_settings}
        return {"success": False, "error": "Manager not initialized"}
