import os
import asyncio
import decky
import json
import urllib.request
import urllib.error
import stat
import socket
import subprocess
import aiohttp
from typing import Dict, Optional, Tuple
from pathlib import Path

# EasyTier下载配置
EASYTIER_VERSION = "2.5.0"
EASYTIER_RELEASES_URL = f"https://github.com/EasyTier/EasyTier/releases/download/v{EASYTIER_VERSION}"
EASYTIER_WEB_BINARY = "easytier-web"
EASYTIER_CORE_BINARY = "easytier-core"
EASYTIER_WEB_URL = f"{EASYTIER_RELEASES_URL}/{EASYTIER_WEB_BINARY}"
EASYTIER_CORE_URL = f"{EASYTIER_RELEASES_URL}/{EASYTIER_CORE_BINARY}"

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

    async def start_both(self) -> Dict:
        """按顺序启动两个进程"""
        try:
            decky.logger.info("Starting EasyTier Web service...")

            # 1. 检查二进制文件是否存在
            web_path = os.path.join(self.easytier_path, EASYTIER_WEB_BINARY)
            core_path = os.path.join(self.easytier_path, EASYTIER_CORE_BINARY)

            if not os.path.exists(web_path):
                return {"success": False, "error": f"{EASYTIER_WEB_BINARY} not found"}
            if not os.path.exists(core_path):
                return {"success": False, "error": f"{EASYTIER_CORE_BINARY} not found"}

            # 2. 启动web和配置服务器
            self.web_process = await asyncio.create_subprocess_exec(
                web_path,
                "--config-server-port", "22020",
                "--config-server-protocol", "udp",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.easytier_path
            )
            self.web_status = "running"

            decky.logger.info("Waiting for config server to be ready...")
            await asyncio.sleep(2)  # 等待配置服务器就绪

            # 3. 启动core节点
            self.core_process = await asyncio.create_subprocess_exec(
                core_path,
                "-w", "udp://127.0.0.1:22020/deck",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.easytier_path
            )
            self.core_status = "running"

            # 4. 启动监控任务
            self.monitor_task = asyncio.create_task(self.monitor_processes())

            decky.logger.info("EasyTier services started successfully")
            return {"success": True}

        except Exception as e:
            decky.logger.error(f"Failed to start EasyTier services: {e}")
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
        decky.logger.info("Initializing Decky EasyTier plugin...")

        # 创建必要的目录
        os.makedirs(self.easytier_path, exist_ok=True)
        os.makedirs(decky.DECKY_PLUGIN_LOG_DIR, exist_ok=True)

        # 加载配置
        await self.load_plugin_settings()

        # 初始化进程管理器
        self.process_manager = DualProcessManager(self.easytier_path)
        self.process_manager.auto_restart_core = self.plugin_settings.get("auto_restart_core", True)

        # 获取IP地址
        self.ip_address = self._get_local_ip()

        decky.logger.info(f"Plugin initialized. Runtime dir: {decky.DECKY_PLUGIN_RUNTIME_DIR}")

    async def install_easytier(self) -> Dict:
        """下载并安装EasyTier二进制文件"""
        try:
            decky.logger.info("Starting EasyTier installation...")

            # 检查存储空间（至少需要100MB）
            statvfs = os.statvfs(self.easytier_path)
            free_space = statvfs.f_frsize * statvfs.f_bavail
            if free_space < 100 * 1024 * 1024:  # 100MB
                return {"success": False, "error": "Insufficient disk space. Need at least 100MB."}

            # 安装qrcode依赖
            await decky.emit("install_progress", 0, "Installing QR code dependencies...")
            try:
                import subprocess
                subprocess.run(["pip", "install", "qrcode[pil]", "--user"],
                             capture_output=True, text=True, check=True)
            except Exception as e:
                decky.logger.warning(f"Failed to install qrcode: {e}")

            # 下载easytier-web
            await decky.emit("install_progress", 20, "Downloading easytier-web...")
            web_path = os.path.join(self.easytier_path, EASYTIER_WEB_BINARY)
            if not await self._download_file(EASYTIER_WEB_URL, web_path):
                return {"success": False, "error": "Failed to download easytier-web"}
            os.chmod(web_path, 0o755)

            # 下载easytier-core
            await decky.emit("install_progress", 60, "Downloading easytier-core...")
            core_path = os.path.join(self.easytier_path, EASYTIER_CORE_BINARY)
            if not await self._download_file(EASYTIER_CORE_URL, core_path):
                return {"success": False, "error": "Failed to download easytier-core"}
            os.chmod(core_path, 0o755)

            await decky.emit("install_progress", 100, "Installation complete!")
            decky.logger.info("EasyTier installation completed successfully")
            return {"success": True}

        except Exception as e:
            decky.logger.error(f"Installation failed: {e}")
            return {"success": False, "error": str(e)}

    async def _download_file(self, url: str, dest_path: str) -> bool:
        """下载文件"""
        try:
            urllib.request.urlretrieve(url, dest_path)

            # 验证文件大小（至少应该有10MB）
            file_size = os.path.getsize(dest_path)
            if file_size < 10 * 1024 * 1024:
                os.remove(dest_path)
                return False

            return True
        except Exception as e:
            decky.logger.error(f"Download error: {e}")
            return False

    async def start_easytier(self) -> Dict:
        """启动EasyTier服务"""
        if not self.process_manager:
            return {"success": False, "error": "Process manager not initialized"}

        # 生成二维码
        self.qr_code = await self.generate_qr_code()

        # 启动服务
        result = await self.process_manager.start_both()

        if result["success"]:
            # 开始监控节点注册
            asyncio.create_task(self._monitor_node_registration())

        return result

    async def stop_easytier(self) -> Dict:
        """停止EasyTier服务"""
        if not self.process_manager:
            return {"success": False, "error": "Process manager not initialized"}

        return await self.process_manager.stop_both()

    async def get_combined_status(self) -> Dict:
        """获取组合状态"""
        if not self.process_manager:
            # 检查是否已安装
            web_path = os.path.join(self.easytier_path, EASYTIER_WEB_BINARY)
            core_path = os.path.join(self.easytier_path, EASYTIER_CORE_BINARY)

            if not os.path.exists(web_path) or not os.path.exists(core_path):
                return {
                    "overall": "uninstalled",
                    "ip": self.ip_address,
                    "plugin_settings": self.plugin_settings
                }

            return {
                "overall": "stopped",
                "ip": self.ip_address,
                "plugin_settings": self.plugin_settings
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
        """生成Web控制台二维码"""
        try:
            # 动态导入qrcode
            try:
                import qrcode
            except ImportError:
                # 如果导入失败，尝试安装
                import subprocess
                subprocess.run(["pip", "install", "qrcode[pil]", "--user"],
                             capture_output=True, check=True)
                import qrcode

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

            img = qr.make_image(fill_color="black", back_color="white")

            # 转换为base64
            import io
            import base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return base64.b64encode(buffer.getvalue()).decode()

        except Exception as e:
            decky.logger.error(f"Failed to generate QR code: {e}")
            return None

    async def _monitor_node_registration(self):
        """监控core节点是否成功注册到web"""
        retry_count = 0
        max_retries = 10  # 最多等待50秒

        while retry_count < max_retries:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://127.0.0.1:11211/api/nodes") as resp:
                        if resp.status == 200:
                            nodes = await resp.json()
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

        self.manager = EasyTierManager()
        await self.manager.init()

        # 如果设置了自动启动，则启动服务
        if self.manager.plugin_settings.get("auto_start", False):
            decky.logger.info("Auto-start enabled, starting EasyTier services...")
            asyncio.create_task(self.manager.start_easytier())

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
        if self.manager:
            return await self.manager.start_easytier()
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
