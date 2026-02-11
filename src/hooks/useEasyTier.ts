/**
 * useEasyTier - EasyTier状态管理Hook
 * 管理整个插件的状态、API调用和事件监听
 */

import { useState, useEffect, useCallback } from 'react';
import { callable, addEventListener } from '@decky/api';
import {
  CombinedStatus,
  PluginSettings,
  ApiResponse,
  InstallProgress
} from '../types';

// API函数类型
interface EasyTierApi {
  getCombinedStatus: () => Promise<ApiResponse<CombinedStatus>>;
  installEasyTier: () => Promise<ApiResponse>;
  startEasyTier: () => Promise<ApiResponse>;
  stopEasyTier: () => Promise<ApiResponse>;
  savePluginSettings: (settings: PluginSettings) => Promise<ApiResponse>;
  loadPluginSettings: () => Promise<ApiResponse<PluginSettings>>;
}

export const useEasyTier = () => {
  // 状态管理
  const [status, setStatus] = useState<CombinedStatus>({
    overall: 'stopped',
    plugin_settings: {
      auto_start: false,
      log_level: 'info',
      auto_restart_core: true
    }
  });

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [installProgress, setInstallProgress] = useState<InstallProgress | null>(null);
  const [nodeRegistered, setNodeRegistered] = useState<boolean>(false);

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
      console.log('[Frontend API] startEasyTier callable called');
      try {
        const result = await callable<[], { success: boolean; error?: string }>('start_easytier')();
        console.log('[Frontend API] start_easytier callable returned:', result);
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
        setStatus(prev => ({ ...prev, ...result.data }));
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
    console.log('[Frontend] startEasyTier called');
    setLoading(true);
    setError(null);
    try {
      console.log('[Frontend] Calling api.startEasyTier()...');
      const result = await api.startEasyTier();
      console.log('[Frontend] api.startEasyTier() returned:', result);
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
        setStatus(prev => ({
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
    const unlistenServiceStatus = addEventListener<[CombinedStatus]>('service_status', (newStatus) => {
      setStatus(prev => ({ ...prev, ...newStatus }));
    });

    // 监听安装进度
    const unlistenInstallProgress = addEventListener<[InstallProgress]>('install_progress', (progress) => {
      setInstallProgress(progress);
    });

    // 监听节点注册状态
    const unlistenNodeRegistered = addEventListener<[boolean]>('node_registered', (registered) => {
      setNodeRegistered(registered);
    });

    return () => {
      (unlistenServiceStatus as any)();
      (unlistenInstallProgress as any)();
      (unlistenNodeRegistered as any)();
    };
  }, []);

  // 初始化加载
  useEffect(() => {
    // 加载初始状态
    const init = async () => {
      try {
        // 获取初始状态
        await refreshStatus();

        // 加载插件设置
        const settingsResult = await api.loadPluginSettings();
        if (settingsResult.success && settingsResult.data) {
          setStatus(prev => ({
            ...prev,
            plugin_settings: settingsResult.data
          }));
        }
        return;  // 修复TypeScript错误：确保所有路径都返回值
      } catch (e) {
        setError(String(e));
        return;  // 修复TypeScript错误：确保所有路径都返回值
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
    return () => {};  // 确保所有路径都返回函数
  }, [status.overall, refreshStatus]);

  return {
    // 状态
    status,
    loading,
    error,
    installProgress,
    nodeRegistered,

    // 操作函数
    refreshStatus,
    installEasyTier,
    startEasyTier,
    stopEasyTier,
    savePluginSettings
  };
};