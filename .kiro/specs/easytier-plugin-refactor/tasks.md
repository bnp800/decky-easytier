# Implementation Plan: EasyTier 插件重构

## 概述

按照设计文档对 Decky EasyTier 插件进行重构：清理 QR 码相关代码和冗余依赖，精简后端逻辑，重构前端组件，修复按钮布局，新增 Web 控制台信息面板。

## Tasks

- [ ] 1. 清理 QR 码相关代码和冗余依赖
  - [ ] 1.1 删除 `src/components/QRCodeDisplay.tsx` 文件
  - [ ] 1.2 删除 `py_modules/qrcode/` 目录和 `py_modules/png.py` 文件
  - [ ] 1.3 更新 `src/types.ts`：移除 `qr_code` 和 `node_count` 字段，移除 `log_level` 属性，移除未使用的 `EasyTierProcessStatus` 和 `ApiResponse` 接口，移除 `starting` 状态（前端未使用）
    - _Requirements: 6.1, 6.2_

- [ ] 2. 重构后端 main.py
  - [ ] 2.1 精简 `DualProcessManager`：移除冗余 `[DEBUG]` 日志，保留关键操作日志
    - _Requirements: 6.4_
  - [ ] 2.2 精简 `EasyTierManager`：移除 `generate_qr_code` 方法、`qr_code` 属性、`_monitor_node_registration` 方法；从 `start_easytier` 中移除 QR 码生成调用；从 `get_combined_status` 返回值中移除 `qr_code` 字段
    - _Requirements: 6.1, 6.2_
  - [ ] 2.3 精简 `Plugin` 类：移除 `_migration` 方法中的冗余迁移逻辑，清理调试日志
    - _Requirements: 6.4_
  - [ ]* 2.4 编写属性测试：设置保存/加载往返一致性
    - **Property 1: 设置保存/加载往返一致性**
    - **Validates: Requirements 5.3, 5.4**
  - [ ]* 2.5 编写属性测试：组合状态响应完整性
    - **Property 2: 组合状态响应完整性**
    - **Validates: Requirements 3.5**
  - [ ]* 2.6 编写属性测试：安装失败错误响应结构
    - **Property 3: 安装失败错误响应结构**
    - **Validates: Requirements 1.4**

- [ ] 3. Checkpoint - 确保后端重构完成
  - 确保所有测试通过，如有问题请向用户确认。

- [ ] 4. 重构前端组件
  - [ ] 4.1 创建 `src/components/WebConsoleInfo.tsx` 组件，显示访问 URL、默认凭据（admin/admin）、api-host 提示和复制 URL 按钮
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [ ] 4.2 重构 `src/components/EasyTierPanel.tsx`：移除 QRCodeDisplay 引用，引入 WebConsoleInfo；修复按钮布局确保每个按钮独占一行；精简各状态渲染函数
    - _Requirements: 6.1, 6.3, 4.1_
  - [ ] 4.3 精简 `src/components/DualStatusPanel.tsx`：移除 `node_count` 显示，简化状态文本
    - _Requirements: 3.1, 6.1_
  - [ ] 4.4 精简 `src/hooks/useEasyTier.ts`：移除 `nodeRegistered` 状态和 `node_registered` 事件监听，移除冗余 console.log
    - _Requirements: 6.1, 6.4_
  - [ ]* 4.5 编写属性测试：状态显示完整性
    - **Property 4: 状态显示完整性**
    - **Validates: Requirements 3.1**

- [ ] 5. 更新插件元数据和清理
  - [ ] 5.1 更新 `plugin.json` 描述：移除 QR 码相关描述
  - [ ] 5.2 更新 `package.json` 描述和关键词：移除 qr-code 关键词
    - _Requirements: 6.1_

- [ ] 6. Final checkpoint - 确保所有变更完成
  - 确保所有测试通过，验证前端构建无错误，如有问题请向用户确认。

## 备注

- 标记 `*` 的任务为可选任务，可跳过以加快 MVP 进度
- 每个任务引用了具体的需求编号以便追溯
- Checkpoint 任务确保增量验证
- 属性测试使用 hypothesis（Python）和 fast-check（TypeScript）
