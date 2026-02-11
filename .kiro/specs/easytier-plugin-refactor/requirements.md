# 需求文档

## 简介

对 Decky EasyTier 插件进行修缮与重构。移除已失效的 QR 码功能，修复 Steam Deck 内置浏览器打开 Web 控制台的 -401 错误，修复页面按钮布局错乱问题，精简冗余代码。重构后的插件聚焦于核心功能：EasyTier 二进制文件的下载与更新、进程启停控制、状态监控，以及启动后引导用户通过 URL 访问 Web 控制台。

## 术语表

- **Plugin**: Decky EasyTier 插件系统，包含 Python 后端和 TypeScript/React 前端
- **Backend**: Python 后端服务（main.py），负责进程管理、文件下载和系统交互
- **Frontend**: TypeScript/React 前端界面，运行在 Steam Deck 的 Decky 侧边栏中
- **EasyTier_Binary**: EasyTier 的可执行文件，包括 easytier-core 和 easytier-web-embed
- **Process_Manager**: 后端中负责管理 easytier-core 和 easytier-web-embed 进程生命周期的模块
- **Web_Console**: easytier-web-embed 提供的 Web 管理控制台，通过浏览器访问
- **Status_Monitor**: 定期检查进程运行状态并向前端推送更新的监控模块

## 需求

### 需求 1：EasyTier 二进制文件下载与更新

**用户故事：** 作为 Steam Deck 用户，我希望能够一键下载和更新 EasyTier 二进制文件，以便获取最新版本的 VPN 服务。

#### 验收标准

1. WHEN 用户首次使用插件且 EasyTier_Binary 未安装时，THE Frontend SHALL 显示安装界面，包含下载按钮和文件大小说明
2. WHEN 用户点击安装按钮，THE Backend SHALL 从 GitHub Releases 下载对应架构的 ZIP 压缩包，解压并设置可执行权限
3. WHILE 下载进行中，THE Frontend SHALL 显示下载进度信息（百分比和当前步骤描述）
4. IF 下载失败（网络错误、磁盘空间不足、文件损坏），THEN THE Backend SHALL 返回包含具体错误原因的失败响应
5. IF 下载失败，THEN THE Frontend SHALL 显示错误信息并提供重试按钮
6. WHEN 安装完成，THE Frontend SHALL 自动刷新状态并切换到已停止界面

### 需求 2：进程启动与停止控制

**用户故事：** 作为 Steam Deck 用户，我希望通过按钮控制 easytier-core 和 easytier-web-embed 的启停，以便按需使用 VPN 服务。

#### 验收标准

1. WHEN 用户点击启动按钮，THE Backend SHALL 按顺序启动 easytier-web-embed（含 API 服务端口 11211 和配置服务端口 22020）和 easytier-core（连接配置服务）
2. WHEN 用户点击停止按钮，THE Backend SHALL 按顺序停止 easytier-core 和 easytier-web-embed，先发送 SIGTERM 信号，超时 5 秒后发送 SIGKILL
3. WHILE 启动或停止操作进行中，THE Frontend SHALL 禁用操作按钮并显示加载指示器
4. IF easytier-web-embed 启动失败，THEN THE Backend SHALL 返回错误信息且不启动 easytier-core
5. IF easytier-core 启动失败，THEN THE Backend SHALL 停止已启动的 easytier-web-embed 并返回错误信息

### 需求 3：进程状态监控

**用户故事：** 作为 Steam Deck 用户，我希望实时了解 EasyTier 各进程的运行状态，以便及时发现和处理异常。

#### 验收标准

1. THE Frontend SHALL 分别显示 easytier-web-embed 和 easytier-core 的运行状态（运行中、已停止、错误）
2. WHILE 服务运行中，THE Status_Monitor SHALL 每 5 秒检查一次进程状态并通过事件推送给前端
3. IF easytier-core 进程崩溃且自动重启设置已开启，THEN THE Process_Manager SHALL 自动重启 easytier-core
4. IF easytier-web-embed 进程崩溃，THEN THE Process_Manager SHALL 停止 easytier-core 并将两个进程状态标记为异常
5. WHEN 前端请求组合状态，THE Backend SHALL 返回包含总体状态、各进程状态和 Steam Deck IP 地址的状态对象

### 需求 4：Web 控制台访问引导

**用户故事：** 作为 Steam Deck 用户，我希望在启动服务后获得清晰的 Web 控制台访问指引，以便在其他设备上配置 VPN 网络。

#### 验收标准

1. WHEN 服务启动成功，THE Frontend SHALL 显示 Web 控制台的访问 URL（格式为 http://{Steam Deck IP}:11211）
2. WHEN 服务启动成功，THE Frontend SHALL 显示默认登录凭据提示（用户名: admin，密码: admin）
3. WHEN 服务启动成功，THE Frontend SHALL 显示提示信息，说明 api-host 需填写 Steam Deck 的 IP 地址
4. THE Frontend SHALL 提供复制 URL 到剪贴板的功能按钮

### 需求 5：插件设置管理

**用户故事：** 作为 Steam Deck 用户，我希望配置插件的行为选项，以便根据个人需求定制插件运行方式。

#### 验收标准

1. THE Frontend SHALL 提供开机自动启动的开关选项
2. THE Frontend SHALL 提供 easytier-core 崩溃后自动重启的开关选项
3. WHEN 用户修改设置，THE Backend SHALL 将设置持久化到 JSON 配置文件
4. WHEN 插件加载时，THE Backend SHALL 从配置文件恢复上次保存的设置
5. IF 配置文件不存在或损坏，THEN THE Backend SHALL 使用默认设置值（auto_start: false, auto_restart_core: true）

### 需求 6：代码精简与重构

**用户故事：** 作为开发者，我希望移除冗余代码并重构项目结构，以便提高代码可维护性。

#### 验收标准

1. THE Plugin SHALL 移除所有 QR 码相关代码，包括 QRCodeDisplay 组件、后端 generate_qr_code 方法和 py_modules 中的 qrcode 依赖
2. THE Plugin SHALL 移除后端状态对象中的 qr_code 字段和前端类型定义中的 qr_code 属性
3. THE Frontend SHALL 使用清晰的布局结构，每个操作按钮独占一行，避免按钮重叠或错位
4. THE Backend SHALL 移除冗余的调试日志语句（[DEBUG] 前缀的日志），保留关键操作日志
5. WHEN 插件卸载时，THE Backend SHALL 停止所有运行中的进程并清理资源

### 需求 7：插件生命周期管理

**用户故事：** 作为 Steam Deck 用户，我希望插件能正确处理加载、卸载和卸载安装等生命周期事件。

#### 验收标准

1. WHEN 插件加载时，THE Backend SHALL 初始化进程管理器、加载配置并获取本机 IP 地址
2. IF 自动启动设置已开启，THEN THE Backend SHALL 在插件加载完成后自动启动 EasyTier 服务
3. WHEN 插件卸载（unload）时，THE Backend SHALL 停止所有运行中的进程
4. WHEN 插件被卸载安装（uninstall）时，THE Backend SHALL 停止进程并删除所有二进制文件和配置文件
