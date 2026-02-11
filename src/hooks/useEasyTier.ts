/**
 * useEasyTier - EasyTier状态管理Hook
 * 管理整个插件的状态、API调用和事件监听
 */

import { useState, useEffect, useCallback } from 'react';
import { callable, addEventListener } from '@decky/api';
import {
  CombinedStatus,
  PluginSettings,
  InstallProgress
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
  savePluginSettings: (settings: PluginSettings) => Promise<ApiResult>;
  loadPluginSettings: () => Promise<ApiResult<PluginSettings>>;
}

export const useEasyTier = () => {
  // 状态管理
  const [status, setStatus] = useState<CombinedStatus>({
    overall: 'stopped',
    plugin_settings: {
      auto_start: false,
      auto_restart_core: true
    }
  });

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [installProgress, setInstallProgress] = useState<InstallProgress | null>(null);

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
    }, []),

    savePluginSettings: useCallback(async (settings: PluginSettings) => {
      try {
        await callable<[PluginSettings], void>('save_plugin_settings')(settings);
        return { success: true };
      } catch (e) {
        return { success: false, error: String(e) };
      }
    }, []),

    loadPluginSettings: useCallback(async () => {
      try {
        const response = await callable<[], { settings: PluginSettings }>('load_plugin_settings')();
        return { success: true, data: response.settings };
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

  const savePluginSettings = useCallback(async (settings: Partial<PluginSettings>) => {
    try {
      const newSettings = { ...status.plugin_settings!, ...settings };
      const result = await api.savePluginSettings(newSettings);
      if (result.success) {
        setStatus((prev: CombinedStatus) => ({
          ...prev,
          plugin_settings: newSettings
        }));
      } else {
        setError(result.error || 'Failed to save settings');
      }
    } catch (e) {
      setError(String(e));
    }
  }, [api, status.plugin_settings]);

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
    const init = async () => {
      try {
        await refreshStatus();

        const settingsResult = await api.loadPluginSettings();
        if (settingsResult.success && settingsResult.data) {
          setStatus((prev: CombinedStatus) => ({
            ...prev,
            plugin_settings: settingsResult.data
          }));
        }
        return;
      } catch (e) {
        setError(String(e));
        return;
      }
    };

    init();
  }, [api, refreshStatus]);

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
    error,
    installProgress,

    // 操作函数
    refreshStatus,
    installEasyTier,
    startEasyTier,
    stopEasyTier,
    savePluginSettings
  };
};
