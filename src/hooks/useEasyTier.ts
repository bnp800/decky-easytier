/**
 * useEasyTier - EasyTier状态管理Hook
 * 管理整个插件的状态、API调用和事件监听
 */

import { useState, useEffect, useCallback } from 'react';
import { callable, addEventListener } from '@decky/api';
import {
  CombinedStatus,
  InstallProgress,
  UpdateInfo
} from '../types';

// 本地 API 响应类型（ApiResponse 已从 types.ts 移除）
interface ApiResult<T = void> {
  success: boolean;
  error?: string;
  data?: T;
}

// API函数类型
interface EasyTierApi {
  getCombinedStatus: () => Promise<ApiResult<CombinedStatus>>;
  installEasyTier: () => Promise<ApiResult>;
  startEasyTier: () => Promise<ApiResult>;
  stopEasyTier: () => Promise<ApiResult>;
}

export const useEasyTier = () => {
  // 状态管理
  const [status, setStatus] = useState<CombinedStatus>({
    overall: 'stopped'
  });

  const [loading, setLoading] = useState<boolean>(false);
  const [updating, setUpdating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [installProgress, setInstallProgress] = useState<InstallProgress | null>(null);
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null);

  // API函数定义
  const api: EasyTierApi = {
    getCombinedStatus: useCallback(async () => {
      try {
        const response = await callable<[], CombinedStatus>('get_combined_status')();
        return { success: true, data: response };
      } catch (e) {
        return { success: false, error: String(e) };
      }
    }, []),

    installEasyTier: useCallback(async () => {
      try {
        await callable('install_easytier')();
        return { success: true };
      } catch (e) {
        return { success: false, error: String(e) };
      }
    }, []),

    startEasyTier: useCallback(async () => {
      try {
        const result = await callable<[], { success: boolean; error?: string }>('start_easytier')();
        return result;
      } catch (e) {
        console.error('[Frontend API] start_easytier callable error:', e);
        return { success: false, error: String(e) };
      }
    }, []),

    stopEasyTier: useCallback(async () => {
      try {
        await callable('stop_easytier')();
        return { success: true };
      } catch (e) {
        return { success: false, error: String(e) };
      }
    }, [])
  };

  // 异步操作函数
  const refreshStatus = useCallback(async () => {
    try {
      const result = await api.getCombinedStatus();
      if (result.success && result.data) {
        setStatus((prev: CombinedStatus) => ({ ...prev, ...result.data }));
        setError(null);
      } else {
        setError(result.error || 'Failed to get status');
      }
    } catch (e) {
      setError(String(e));
    }
  }, [api]);

  const installEasyTier = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setInstallProgress({ percent: 0, message: 'Starting installation...' });
      const result = await api.installEasyTier();
      if (result.success) {
        await refreshStatus();
        setInstallProgress(null);
      } else {
        setError(result.error || 'Installation failed');
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [api, refreshStatus]);

  const startEasyTier = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.startEasyTier();
      if (result.success) {
        await refreshStatus();
      } else {
        setError(result.error || 'Failed to start');
      }
    } catch (e) {
      console.error('[Frontend] startEasyTier error:', e);
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [api, refreshStatus]);

  const stopEasyTier = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.stopEasyTier();
      if (result.success) {
        await refreshStatus();
      } else {
        setError(result.error || 'Failed to stop');
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [api, refreshStatus]);

  const checkUpdate = useCallback(async () => {
    try {
      const result = await callable<[], UpdateInfo>('check_update')();
      setUpdateInfo(result);
      return result;
    } catch (e) {
      console.error('[Frontend] checkUpdate error:', e);
      return null;
    }
  }, []);

  const updateEasyTier = useCallback(async () => {
    setUpdating(true);
    setError(null);
    try {
      setInstallProgress({ percent: 0, message: '正在更新...' });
      const result = await callable<[], { success: boolean; error?: string }>('update_easytier')();
      if (result.success) {
        await refreshStatus();
        setInstallProgress(null);
        setUpdateInfo(null);
      } else {
        setError(result.error || 'Update failed');
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setUpdating(false);
    }
  }, [refreshStatus]);

  // 事件监听
  useEffect(() => {
    // 监听服务状态更新
    const unlistenServiceStatus = addEventListener<[CombinedStatus]>('service_status', (newStatus: CombinedStatus) => {
      setStatus((prev: CombinedStatus) => ({ ...prev, ...newStatus }));
    });

    // 监听安装进度
    const unlistenInstallProgress = addEventListener<[InstallProgress]>('install_progress', (progress: InstallProgress) => {
      setInstallProgress(progress);
    });

    return () => {
      (unlistenServiceStatus as any)();
      (unlistenInstallProgress as any)();
    };
  }, []);

  // 初始化加载
  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  // 启动时检查一次更新（独立effect，不会重复触发）
  useEffect(() => {
    callable<[], UpdateInfo>('check_update')().then((result) => {
      setUpdateInfo(result);
    }).catch(() => {});
  }, []);

  // 定期刷新状态（当服务运行时）
  useEffect(() => {
    if (status.overall === 'running') {
      const interval = setInterval(() => {
        refreshStatus();
      }, 5000);
      return () => clearInterval(interval);
    }
    return () => {};
  }, [status.overall, refreshStatus]);

  return {
    // 状态
    status,
    loading,
    updating,
    error,
    installProgress,
    updateInfo,

    // 操作函数
    refreshStatus,
    installEasyTier,
    startEasyTier,
    stopEasyTier,
    checkUpdate,
    updateEasyTier
  };
};
