/**
 * TypeScript 类型定义 - Decky EasyTier
 */

// 插件设置
export interface PluginSettings {
  auto_start: boolean;
  auto_restart_core: boolean;
}

// 进程状态
export type ProcessStatus = 'stopped' | 'running' | 'crashed' | 'error';

// 总体状态
export type OverallStatus = 'uninstalled' | 'stopped' | 'running' | 'partial' | 'error';

// 组合状态（后端返回）
export interface CombinedStatus {
  overall: OverallStatus;
  web_status?: ProcessStatus;
  core_status?: ProcessStatus;
  ip?: string;
  plugin_settings?: PluginSettings;
  error?: string;
}

// 安装进度
export interface InstallProgress {
  percent: number;
  message: string;
}
