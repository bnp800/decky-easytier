# Decky EasyTier

Steam Deck 游戏模式下的 EasyTier 原生管理插件。插件不使用 Web 控制台、Flatpak 或系统 Arch 包，只运行随插件打包的 `easytier-core`，并通过本地 `easytier-cli` 展示节点、路由与日志。

## 功能

- 多配置档案，单档案运行
- 常用配置表单与完整 TOML 编辑/剪贴板导入导出
- 启动、停止、配置变更后安全重启
- 节点、路由、本机状态和日志查看
- 自动启动与崩溃退避重启
- 配置保存前使用同版本 EasyTier 校验
- 配置文件 `0600`、管理 RPC 仅监听本机

## 安装

1. 在 GitHub Actions 中运行 `build-native-plugin`。
2. 下载 `decky-easytier-v2.0.0` artifact 并解压得到插件 ZIP。
3. 使用 Decky Loader 的“从 URL 安装”或开发者侧载功能安装 ZIP。

发布流水线会获取 EasyTier 最新稳定版源码，针对 SteamOS 构建并完成兼容性测试，再将二进制和版本记录打入 ZIP。安装和运行时不需要再次联网下载。

> 从旧版 Web 原型升级会执行一次完整重置，旧配置与旧二进制不会迁移。

## 本地开发

需要 Node.js 20、pnpm 9.15.4 和 Python 3.11+。

```bash
pnpm install
pnpm check
python -m unittest -v test_backend.py
```

本地前端构建不包含 EasyTier 二进制；完整侧载包由 CI 生成。

## 数据位置

Decky 设置目录下的 `native/` 保存 `state.json`、`profiles.json` 和 `profiles/*.toml`。日志写入 Decky 为插件分配的日志目录，单文件 2 MiB，最多保留三个文件。

## 限制

- 仅支持 Steam Deck x86_64 / SteamOS 稳定版。
- 同一时刻只运行一个网络档案。
- Secure Mode、ACL、端口转发和 WireGuard 门户通过高级 TOML 配置。
- 当前发布目标为个人侧载，尚未按 Decky 商店流程提交。
