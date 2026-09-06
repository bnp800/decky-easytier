import * as TOML from '@iarna/toml';
import { CommonProfileFields } from './types';

type TomlObject = Record<string, any>;
const PUBLIC_PEER = 'tcp://public.easytier.top:11010';
const lines = (value: string) => value.split(/[,\n]/).map((item) => item.trim()).filter(Boolean);

export const defaultProfileToml = (): string => TOML.stringify({
  hostname: 'steamdeck',
  dhcp: true,
  listeners: ['tcp://0.0.0.0:11010', 'udp://0.0.0.0:11010'],
  network_identity: { network_name: 'default', network_secret: '' },
  peer: [{ uri: PUBLIC_PEER }],
  flags: { enable_encryption: true, enable_ipv6: true, private_mode: false },
} as any);

export function readCommonFields(source: string): CommonProfileFields {
  const value = TOML.parse(source) as TomlObject;
  const flags = (value.flags || {}) as TomlObject;
  return {
    hostname: String(value.hostname || 'steamdeck'),
    networkName: String(value.network_identity?.network_name || ''),
    networkSecret: String(value.network_identity?.network_secret || ''),
    addressMode: value.dhcp === false ? 'static' : 'dhcp',
    ipv4: String(value.ipv4 || ''),
    peers: (value.peer || []).map((item: any) => item.uri).filter(Boolean).join('\n'),
    listeners: (value.listeners || []).join('\n'),
    proxyNetworks: (value.proxy_network || []).map((item: any) => item.mapped_cidr ? `${item.cidr}->${item.mapped_cidr}` : item.cidr).filter(Boolean).join('\n'),
    exitNodes: (value.exit_nodes || []).join('\n'),
    encryption: flags.enable_encryption !== false,
    ipv6: flags.enable_ipv6 !== false,
    privateMode: flags.private_mode === true,
    latencyFirst: flags.latency_first === true,
    disableUpnp: flags.disable_upnp === true,
    udpBroadcastRelay: flags.enable_udp_broadcast_relay === true,
  };
}

export function writeCommonFields(source: string, fields: CommonProfileFields): string {
  const value = TOML.parse(source) as TomlObject;
  value.hostname = fields.hostname.trim();
  value.dhcp = fields.addressMode === 'dhcp';
  if (value.dhcp) delete value.ipv4; else value.ipv4 = fields.ipv4.trim();
  value.network_identity = { ...(value.network_identity || {}), network_name: fields.networkName.trim(), network_secret: fields.networkSecret };
  value.peer = lines(fields.peers).map((uri) => ({ uri }));
  value.listeners = lines(fields.listeners);
  value.proxy_network = lines(fields.proxyNetworks).map((entry) => {
    const [cidr, mapped_cidr] = entry.split('->').map((item) => item.trim());
    return mapped_cidr ? { cidr, mapped_cidr } : { cidr };
  });
  value.exit_nodes = lines(fields.exitNodes);
  value.flags = {
    ...(value.flags || {}),
    enable_encryption: fields.encryption,
    enable_ipv6: fields.ipv6,
    private_mode: fields.privateMode,
    latency_first: fields.latencyFirst,
    disable_upnp: fields.disableUpnp,
    enable_udp_broadcast_relay: fields.udpBroadcastRelay,
  };
  return TOML.stringify(value as any);
}
