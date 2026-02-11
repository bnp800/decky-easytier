/**
 * TypeScript 类型定义 - Decky EasyTier
 */

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
  installed_version?: string;
  error?: string;
}

// 更新检查结果
export interface UpdateInfo {
  installed_version?: string;
  latest_version?: string;
  update_available: boolean;
}

// 安装进度
export interface InstallProgress {
  percent: number;
  message: string;
}
