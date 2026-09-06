import { useMemo, useState } from 'react';
import { ButtonItem, DropdownItem, PanelSection, PanelSectionRow, TextField, ToggleField } from '@decky/ui';
import { CommonProfileFields, Profile } from '../types';
import { readCommonFields, writeCommonFields } from '../profileToml';

interface Props {
  profile: Pick<Profile, 'name' | 'toml'> & Partial<Pick<Profile, 'id'>>;
  busy: boolean;
  onCancel: () => void;
  onSave: (profile: { id?: string; name: string; toml: string }) => Promise<void>;
}

const TextArea = ({ label, value, onChange, password = false }: { label: string; value: string; onChange: (value: string) => void; password?: boolean }) => (
  <PanelSectionRow>
    <div className="et-label">{label}</div>
    {value.includes('\n') ? (
      <textarea className="et-textarea" value={value} onChange={(event) => onChange(event.currentTarget.value)} />
    ) : (
      <TextField value={value} bIsPassword={password} onChange={(event) => onChange(event.currentTarget.value)} />
    )}
  </PanelSectionRow>
);

export function ProfileEditor({ profile, busy, onCancel, onSave }: Props) {
  const initial = useMemo(() => readCommonFields(profile.toml), [profile.toml]);
  const [name, setName] = useState(profile.name);
  const [toml, setToml] = useState(profile.toml);
  const [fields, setFields] = useState<CommonProfileFields>(initial);
  const [rawMode, setRawMode] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const update = <K extends keyof CommonProfileFields>(key: K, value: CommonProfileFields[K]) => setFields((old) => ({ ...old, [key]: value }));

  const toggleMode = () => {
    try {
      if (rawMode) setFields(readCommonFields(toml));
      else setToml(writeCommonFields(toml, fields));
      setRawMode(!rawMode); setLocalError(null);
    } catch (reason) { setLocalError(`TOML 解析失败：${String(reason)}`); }
  };
  const save = async () => {
    try {
      const source = rawMode ? toml : writeCommonFields(toml, fields);
      setLocalError(null);
      await onSave({ id: profile.id, name, toml: source });
    } catch (reason) { setLocalError(`配置格式错误：${String(reason)}`); }
  };

  return (
    <>
      <PanelSection title="配置档案">
        <TextArea label="档案名称" value={name} onChange={setName} />
        <PanelSectionRow><ButtonItem layout="below" onClick={toggleMode}>{rawMode ? '返回常用表单' : '编辑完整 TOML'}</ButtonItem></PanelSectionRow>
      </PanelSection>
      {rawMode ? (
        <PanelSection title="高级 TOML">
          <PanelSectionRow><textarea className="et-toml" value={toml} onChange={(event) => setToml(event.currentTarget.value)} spellCheck={false} /></PanelSectionRow>
          <PanelSectionRow><ButtonItem layout="below" onClick={async () => navigator.clipboard.writeText(toml)}>复制 TOML</ButtonItem></PanelSectionRow>
          <PanelSectionRow><ButtonItem layout="below" onClick={async () => setToml(await navigator.clipboard.readText())}>从剪贴板导入</ButtonItem></PanelSectionRow>
        </PanelSection>
      ) : (
        <>
          <PanelSection title="网络">
            <TextArea label="主机名" value={fields.hostname} onChange={(v) => update('hostname', v)} />
            <TextArea label="网络名称" value={fields.networkName} onChange={(v) => update('networkName', v)} />
            <TextArea label="网络密钥" value={fields.networkSecret} password onChange={(v) => update('networkSecret', v)} />
            <DropdownItem label="地址模式" selectedOption={fields.addressMode} rgOptions={[{ data: 'dhcp', label: 'DHCP' }, { data: 'static', label: '静态 IPv4' }]} onChange={(item) => update('addressMode', item.data)} />
            {fields.addressMode === 'static' && <TextArea label="虚拟 IPv4/CIDR" value={fields.ipv4} onChange={(v) => update('ipv4', v)} />}
            <TextArea label="初始节点（每行一个）" value={fields.peers} onChange={(v) => update('peers', v)} />
            <TextArea label="监听器（每行一个）" value={fields.listeners} onChange={(v) => update('listeners', v)} />
            <TextArea label="子网代理（每行一个）" value={fields.proxyNetworks} onChange={(v) => update('proxyNetworks', v)} />
            <TextArea label="出口节点 IP（每行一个）" value={fields.exitNodes} onChange={(v) => update('exitNodes', v)} />
          </PanelSection>
          <PanelSection title="常用开关">
            <ToggleField label="传输加密" checked={fields.encryption} onChange={(v) => update('encryption', v)} />
            <ToggleField label="IPv6" checked={fields.ipv6} onChange={(v) => update('ipv6', v)} />
            <ToggleField label="私有模式" checked={fields.privateMode} onChange={(v) => update('privateMode', v)} />
            <ToggleField label="延迟优先" checked={fields.latencyFirst} onChange={(v) => update('latencyFirst', v)} />
            <ToggleField label="禁用 UPnP" checked={fields.disableUpnp} onChange={(v) => update('disableUpnp', v)} />
            <ToggleField label="UDP 广播中继" checked={fields.udpBroadcastRelay} onChange={(v) => update('udpBroadcastRelay', v)} />
          </PanelSection>
        </>
      )}
      {localError && <div className="et-error">{localError}</div>}
      <PanelSection>
        <PanelSectionRow><ButtonItem layout="below" disabled={busy} onClick={save}>{busy ? '验证中…' : '验证并保存'}</ButtonItem></PanelSectionRow>
        <PanelSectionRow><ButtonItem layout="below" disabled={busy} onClick={onCancel}>取消</ButtonItem></PanelSectionRow>
      </PanelSection>
    </>
  );
}
