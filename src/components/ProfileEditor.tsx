import { useMemo, useRef, useState } from 'react';
import { Button, ButtonItem, DropdownItem, Focusable, PanelSection, PanelSectionRow, TextField, ToggleField } from '@decky/ui';
import { CommonProfileFields, Profile } from '../types';
import { readCommonFields, writeCommonFields } from '../profileToml';

interface Props {
  profile: Pick<Profile, 'name' | 'toml'> & Partial<Pick<Profile, 'id'>>;
  busy: boolean;
  onCancel: () => void;
  onSave: (profile: { id?: string; name: string; toml: string }) => Promise<void>;
}

const TextInput = ({ label, value, onChange, password = false }: { label: string; value: string; onChange: (value: string) => void; password?: boolean }) => (
  <PanelSectionRow>
    <TextField label={label} value={value} bIsPassword={password} onChange={(event) => onChange(event.currentTarget.value)} />
  </PanelSectionRow>
);

const MultiValueInput = ({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) => {
  const entries = value === '' ? [''] : value.split('\n');
  const setEntry = (index: number, next: string) => onChange(entries.map((entry, position) => position === index ? next : entry).join('\n'));
  const removeEntry = (index: number) => onChange(entries.filter((_, position) => position !== index).join('\n'));
  return (
    <PanelSectionRow>
      <div className="et-label">{label}</div>
      <Focusable className="et-list-editor" flow-children="down">
        {entries.map((entry, index) => (
          <Focusable className="et-list-row" flow-children="right" key={index}>
            <TextField value={entry} onChange={(event) => setEntry(index, event.currentTarget.value)} />
            <Button focusable onClick={() => removeEntry(index)}>删除</Button>
          </Focusable>
        ))}
        <Button focusable onClick={() => onChange([...entries, ''].join('\n'))}>添加</Button>
      </Focusable>
    </PanelSectionRow>
  );
};

export function ProfileEditor({ profile, busy, onCancel, onSave }: Props) {
  const initial = useMemo(() => readCommonFields(profile.toml), [profile.toml]);
  const [name, setName] = useState(profile.name);
  const [toml, setToml] = useState(profile.toml);
  const [fields, setFields] = useState<CommonProfileFields>(initial);
  const [rawMode, setRawMode] = useState(false);
  const tomlArea = useRef<HTMLTextAreaElement>(null);
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
        <TextInput label="档案名称" value={name} onChange={setName} />
        <PanelSectionRow><ButtonItem layout="below" onClick={toggleMode}>{rawMode ? '返回常用表单' : '编辑完整 TOML'}</ButtonItem></PanelSectionRow>
      </PanelSection>
      {rawMode ? (
        <PanelSection title="高级 TOML">
          <PanelSectionRow><Focusable flow-children="down" onActivate={() => tomlArea.current?.focus()}><textarea ref={tomlArea} className="et-toml" value={toml} onChange={(event) => setToml(event.currentTarget.value)} spellCheck={false} /></Focusable></PanelSectionRow>
          <PanelSectionRow><ButtonItem layout="below" onClick={async () => navigator.clipboard.writeText(toml)}>复制 TOML</ButtonItem></PanelSectionRow>
          <PanelSectionRow><ButtonItem layout="below" onClick={async () => setToml(await navigator.clipboard.readText())}>从剪贴板导入</ButtonItem></PanelSectionRow>
        </PanelSection>
      ) : (
        <>
          <PanelSection title="网络">
            <TextInput label="主机名" value={fields.hostname} onChange={(v) => update('hostname', v)} />
            <TextInput label="网络名称" value={fields.networkName} onChange={(v) => update('networkName', v)} />
            <TextInput label="网络密钥" value={fields.networkSecret} password onChange={(v) => update('networkSecret', v)} />
            <DropdownItem label="地址模式" selectedOption={fields.addressMode} rgOptions={[{ data: 'dhcp', label: 'DHCP' }, { data: 'static', label: '静态 IPv4' }]} onChange={(item) => update('addressMode', item.data)} />
            {fields.addressMode === 'static' && <TextInput label="虚拟 IPv4/CIDR" value={fields.ipv4} onChange={(v) => update('ipv4', v)} />}
            <MultiValueInput label="初始节点" value={fields.peers} onChange={(v) => update('peers', v)} />
            <MultiValueInput label="监听器" value={fields.listeners} onChange={(v) => update('listeners', v)} />
            <MultiValueInput label="子网代理" value={fields.proxyNetworks} onChange={(v) => update('proxyNetworks', v)} />
            <MultiValueInput label="出口节点 IP" value={fields.exitNodes} onChange={(v) => update('exitNodes', v)} />
          </PanelSection>
          <PanelSection title="常用开关">
            <ToggleField label="传输加密" checked={fields.encryption} onChange={(v) => update('encryption', v)} />
            <ToggleField label="IPv6" checked={fields.ipv6} onChange={(v) => update('ipv6', v)} />
            <ToggleField label="私有模式" checked={fields.privateMode} onChange={(v) => update('privateMode', v)} />
            <ToggleField label="延迟优先" checked={fields.latencyFirst} onChange={(v) => update('latencyFirst', v)} />
            <ToggleField label="禁用 UPnP" checked={fields.disableUpnp} onChange={(v) => update('disableUpnp', v)} />
            <ToggleField label="UDP 广播中继" checked={fields.udpBroadcastRelay} onChange={(v) => update('udpBroadcastRelay', v)} />
            <ToggleField label="无 TUN 模式" description="不创建虚拟网卡" checked={fields.noTun} onChange={(v) => update('noTun', v)} />
            <ToggleField label="用户态网络栈" description="使用 smoltcp" checked={fields.useSmoltcp} onChange={(v) => update('useSmoltcp', v)} />
            <ToggleField label="禁用 P2P" checked={fields.disableP2p} onChange={(v) => update('disableP2p', v)} />
            <ToggleField label="仅允许 P2P" checked={fields.p2pOnly} onChange={(v) => update('p2pOnly', v)} />
            <ToggleField label="按需建立 P2P" checked={fields.lazyP2p} onChange={(v) => update('lazyP2p', v)} />
            <ToggleField label="强制需要 P2P" checked={fields.needP2p} onChange={(v) => update('needP2p', v)} />
            <ToggleField label="允许作为出口节点" checked={fields.enableExitNode} onChange={(v) => update('enableExitNode', v)} />
            <ToggleField label="接受 Magic DNS" checked={fields.acceptDns} onChange={(v) => update('acceptDns', v)} />
            <ToggleField label="使用系统转发子网代理" checked={fields.proxyForwardBySystem} onChange={(v) => update('proxyForwardBySystem', v)} />
            <ToggleField label="禁用 TCP 打洞" checked={fields.disableTcpHolePunching} onChange={(v) => update('disableTcpHolePunching', v)} />
            <ToggleField label="禁用 UDP 打洞" checked={fields.disableUdpHolePunching} onChange={(v) => update('disableUdpHolePunching', v)} />
            <ToggleField label="禁用对称 NAT 打洞" checked={fields.disableSymHolePunching} onChange={(v) => update('disableSymHolePunching', v)} />
            <ToggleField label="多线程运行" checked={fields.multiThread} onChange={(v) => update('multiThread', v)} />
            <ToggleField label="监听器绑定设备" checked={fields.bindDevice} onChange={(v) => update('bindDevice', v)} />
            <ToggleField label="禁止转发中继数据" checked={fields.disableRelayData} onChange={(v) => update('disableRelayData', v)} />
            <ToggleField label="转发所有节点 RPC" checked={fields.relayAllPeerRpc} onChange={(v) => update('relayAllPeerRpc', v)} />
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
