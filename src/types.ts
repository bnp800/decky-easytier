/**
 * TypeScript 类型定义 - Decky EasyTier
 */

// 插件设置
export interface PluginSettings {
  auto_start: boolean;
  log_level: 'debug' | 'info' | 'warning' | 'error';
  auto_restart_core: boolean;
}

// 进程状态
export type ProcessStatus = 'stopped' | 'running' | 'crashed' | 'error';

// EasyTier进程状态
export interface EasyTierProcessStatus {
  web: ProcessStatus;
  core: ProcessStatus;
}

// 总体状态
export type OverallStatus = 'uninstalled' | 'stopped' | 'starting' | 'partial' | 'running' | 'error';

// 组合状态（后端返回）
export interface CombinedStatus {
  overall: OverallStatus;
  web_status?: ProcessStatus;
  core_status?: ProcessStatus;
  ip?: string;
  qr_code?: string;
  plugin_settings?: PluginSettings;
  node_count?: number;
  error?: string;
}

// API响应
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
}

// 安装进度
export interface InstallProgress {
  percent: number;
  message: string;
}
