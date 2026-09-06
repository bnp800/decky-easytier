import { useCallback, useEffect, useState } from 'react';
import { callable } from '@decky/api';
import { ApiResponse, PluginSettings, PluginState, Profile, RuntimeSnapshot, SaveProfileResult } from '../types';

const initialState: PluginState = {
  schema_version: 2, binary_version: 'bundled', settings: { auto_start: false, auto_restart_core: true },
  profiles: [], selected_profile_id: null,
  process: { status: 'stopped', profile_id: null, pid: null, restart_attempt: 0, error: null }, restart_required: false,
};

export function useEasyTier() {
  const [state, setState] = useState<PluginState>(initialState);
  const [runtime, setRuntime] = useState<RuntimeSnapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async <T,>(operation: () => Promise<ApiResponse<T>>): Promise<T | undefined> => {
    setBusy(true); setError(null);
    try {
      const response = await operation();
      if (!response.success) {
        const message = response.error?.details ? `${response.error.message}\n${response.error.details}` : response.error?.message;
        setError(message || '操作失败');
        return undefined;
      }
      return response.data;
    } catch (reason) {
      setError(String(reason));
      return undefined;
    } finally { setBusy(false); }
  }, []);

  const refresh = useCallback(async () => {
    const response = await callable<[], ApiResponse<PluginState>>('get_state')();
    if (response.success && response.data) setState(response.data);
    else setError(response.error?.message || '无法读取插件状态');
  }, []);

  const refreshRuntime = useCallback(async () => {
    const response = await callable<[number], ApiResponse<RuntimeSnapshot>>('get_runtime_snapshot')(100);
    if (response.success && response.data) setRuntime(response.data);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    refreshRuntime();
    const timer = window.setInterval(() => { refresh(); refreshRuntime(); }, 5000);
    return () => window.clearInterval(timer);
  }, [refresh, refreshRuntime]);

  const getProfile = (id: string) => run(() => callable<[string], ApiResponse<Profile>>('get_profile')(id));
  const saveProfile = async (profile: { id?: string; name: string; toml: string }) => {
    const result = await run(() => callable<[typeof profile], ApiResponse<SaveProfileResult>>('save_profile')(profile));
    await refresh(); return result;
  };
  const deleteProfile = async (id: string) => { const result = await run(() => callable<[string], ApiResponse>('delete_profile')(id)); await refresh(); return result; };
  const selectProfile = async (id: string) => { const result = await run(() => callable<[string], ApiResponse>('select_profile')(id)); await refresh(); return result; };
  const startProfile = async (id: string) => { const result = await run(() => callable<[string], ApiResponse>('start_profile')(id)); await refresh(); await refreshRuntime(); return result; };
  const stop = async () => { const result = await run(() => callable<[], ApiResponse>('stop_easytier')()); await refresh(); return result; };
  const restart = async () => { const result = await run(() => callable<[], ApiResponse>('restart_easytier')()); await refresh(); return result; };
  const saveSettings = async (settings: PluginSettings) => { const result = await run(() => callable<[PluginSettings], ApiResponse>('save_settings')(settings)); await refresh(); return result; };

  return { state, runtime, busy, error, setError, refresh, getProfile, saveProfile, deleteProfile, selectProfile, startProfile, stop, restart, saveSettings };
}
