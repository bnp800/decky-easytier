import { useState } from 'react';
import { Button, ButtonItem, ConfirmModal, Field, Focusable, PanelSection, PanelSectionRow, Spinner, ToggleField, showModal } from '@decky/ui';
import { FaCopy, FaEdit, FaPlay, FaPlus, FaStop, FaTrash } from 'react-icons/fa';
import { defaultProfileToml } from '../profileToml';
import { Profile, ProfileSummary } from '../types';
import { useEasyTier } from '../hooks/useEasyTier';
import { ProfileEditor } from './ProfileEditor';

const LABELS: Record<string, string> = {
  stopped: '已停止', starting: '启动中', running: '运行中', stopping: '停止中',
  restart_wait: '等待自动重启', crashed: '已崩溃', error: '错误',
};

const JsonView = ({ value, empty }: { value: unknown; empty: string }) => {
  const items = Array.isArray(value) ? value : value ? [value] : [];
  if (!items.length) return <div className="et-muted">{empty}</div>;
  return <pre className="et-json">{JSON.stringify(value, null, 2)}</pre>;
};

export function EasyTierPanel() {
  const api = useEasyTier();
  const [editor, setEditor] = useState<(Pick<Profile, 'name' | 'toml'> & Partial<Pick<Profile, 'id'>>) | null>(null);
  const selected = api.state.profiles.find((profile) => profile.id === api.state.selected_profile_id);
  const running = api.state.process.status === 'running' || api.state.process.status === 'starting' || api.state.process.status === 'restart_wait';

  const openProfile = async (profile: ProfileSummary) => {
    const full = await api.getProfile(profile.id);
    if (full) setEditor(full);
  };
  const saveProfile = async (profile: { id?: string; name: string; toml: string }) => {
    const result = await api.saveProfile(profile);
    if (!result) return;
    setEditor(null);
    if (result.restart_required) {
      showModal(<ConfirmModal strTitle="配置已保存" strDescription="当前连接仍在使用旧配置。是否立即重启 EasyTier？" strOKButtonText="立即重启" strCancelButtonText="稍后" onOK={() => api.restart()} />);
    }
  };
  const duplicate = async (profile: ProfileSummary) => {
    const full = await api.getProfile(profile.id);
    if (full) setEditor({ name: `${full.name} 副本`, toml: full.toml });
  };
  const remove = (profile: ProfileSummary) => showModal(
    <ConfirmModal bDestructiveWarning strTitle="删除配置档案" strDescription={`确定删除“${profile.name}”？`} strOKButtonText="删除" onOK={() => api.deleteProfile(profile.id)} />,
  );

  if (editor) return <ProfileEditor profile={editor} busy={api.busy} onCancel={() => setEditor(null)} onSave={saveProfile} />;

  return (
    <>
      <PanelSection title="运行状态">
        <Field label="EasyTier Core">{LABELS[api.state.process.status] || api.state.process.status}</Field>
        <Field label="版本">{api.state.binary_version}</Field>
        <Field label="当前档案">{selected?.name || '未选择'}</Field>
        {api.state.process.pid && <Field label="PID">{api.state.process.pid}</Field>}
        {api.state.process.restart_attempt > 0 && <Field label="重启次数">{api.state.process.restart_attempt}</Field>}
        {api.state.process.error && <div className="et-error">{api.state.process.error}</div>}
        {api.runtime?.cli_error && <div className="et-warning">管理接口暂不可用：{api.runtime.cli_error}</div>}
        <PanelSectionRow>
          {api.busy ? <Spinner /> : running ? (
            <ButtonItem layout="below" onClick={api.stop}><FaStop /> 停止 EasyTier</ButtonItem>
          ) : (
            <ButtonItem layout="below" disabled={!selected} onClick={() => selected && api.startProfile(selected.id)}><FaPlay /> 启动所选档案</ButtonItem>
          )}
        </PanelSectionRow>
        {api.state.restart_required && <PanelSectionRow><ButtonItem layout="below" onClick={api.restart}>应用配置并重启</ButtonItem></PanelSectionRow>}
      </PanelSection>

      {running && <>
        <PanelSection title="本机"><JsonView value={api.runtime?.node} empty="RPC 正在就绪…" /></PanelSection>
        <PanelSection title="节点"><JsonView value={api.runtime?.peers} empty="尚未发现节点" /></PanelSection>
        <PanelSection title="路由"><JsonView value={api.runtime?.routes} empty="暂无路由" /></PanelSection>
        <PanelSection title="最近日志"><pre className="et-log">{api.runtime?.logs.join('\n') || '暂无日志'}</pre></PanelSection>
      </>}

      <PanelSection title="配置档案">
        {!api.state.profiles.length && <div className="et-muted">还没有配置档案。</div>}
        {api.state.profiles.map((profile) => (
          <div className={`et-profile ${profile.id === api.state.selected_profile_id ? 'selected' : ''}`} key={profile.id}>
            <ButtonItem layout="below" disabled={running && profile.id !== api.state.process.profile_id} onClick={() => api.selectProfile(profile.id)}>{profile.id === api.state.selected_profile_id ? '● ' : '○ '}{profile.name}</ButtonItem>
            <Focusable className="et-actions" flow-children="right">
              <Button focusable onClick={() => openProfile(profile)}><FaEdit /> 编辑</Button>
              <Button focusable onClick={() => duplicate(profile)}><FaCopy /> 复制</Button>
              <Button focusable disabled={running && profile.id === api.state.process.profile_id} onClick={() => remove(profile)}><FaTrash /> 删除</Button>
            </Focusable>
          </div>
        ))}
        <PanelSectionRow><ButtonItem layout="below" onClick={() => setEditor({ name: `网络 ${api.state.profiles.length + 1}`, toml: defaultProfileToml() })}><FaPlus /> 新建档案</ButtonItem></PanelSectionRow>
      </PanelSection>

      <PanelSection title="插件设置">
        <ToggleField label="Decky 加载时自动启动" checked={api.state.settings.auto_start} onChange={(value) => api.saveSettings({ ...api.state.settings, auto_start: value })} />
        <ToggleField label="Core 崩溃后自动重启" checked={api.state.settings.auto_restart_core} onChange={(value) => api.saveSettings({ ...api.state.settings, auto_restart_core: value })} />
      </PanelSection>
      {api.error && <div className="et-error" onClick={() => api.setError(null)}>{api.error}<div className="et-muted">点击关闭</div></div>}
    </>
  );
}
