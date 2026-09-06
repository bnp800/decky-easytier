import { parse, stringify } from 'smol-toml';
import { CommonProfileFields } from './types';

type TomlObject = Record<string, any>;
const PUBLIC_PEER = 'tcp://public.easytier.top:11010';
const lines = (value: string) => value.split(/[,\n]/).map((item) => item.trim()).filter(Boolean);

export const defaultProfileToml = (): string => stringify({
  hostname: 'steamdeck',
  dhcp: true,
  listeners: ['tcp://0.0.0.0:11010', 'udp://0.0.0.0:11010'],
  network_identity: { network_name: 'default', network_secret: '' },
  peer: [{ uri: PUBLIC_PEER }],
  flags: { enable_encryption: true, enable_ipv6: true, private_mode: false },
} as any);

export function readCommonFields(source: string): CommonProfileFields {
  const value = parse(source) as TomlObject;
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
    noTun: flags.no_tun === true,
    useSmoltcp: flags.use_smoltcp === true,
    disableP2p: flags.disable_p2p === true,
    p2pOnly: flags.p2p_only === true,
    lazyP2p: flags.lazy_p2p === true,
    needP2p: flags.need_p2p === true,
    enableExitNode: flags.enable_exit_node === true,
    acceptDns: flags.accept_dns === true,
    proxyForwardBySystem: flags.proxy_forward_by_system === true,
    disableTcpHolePunching: flags.disable_tcp_hole_punching === true,
    disableUdpHolePunching: flags.disable_udp_hole_punching === true,
    disableSymHolePunching: flags.disable_sym_hole_punching === true,
    multiThread: flags.multi_thread !== false,
    bindDevice: flags.bind_device !== false,
    disableRelayData: flags.disable_relay_data === true,
    relayAllPeerRpc: flags.relay_all_peer_rpc === true,
  };
}

export function writeCommonFields(source: string, fields: CommonProfileFields): string {
  const value = parse(source) as TomlObject;
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
    no_tun: fields.noTun,
    use_smoltcp: fields.useSmoltcp,
    disable_p2p: fields.disableP2p,
    p2p_only: fields.p2pOnly,
    lazy_p2p: fields.lazyP2p,
    need_p2p: fields.needP2p,
    enable_exit_node: fields.enableExitNode,
    accept_dns: fields.acceptDns,
    proxy_forward_by_system: fields.proxyForwardBySystem,
    disable_tcp_hole_punching: fields.disableTcpHolePunching,
    disable_udp_hole_punching: fields.disableUdpHolePunching,
    disable_sym_hole_punching: fields.disableSymHolePunching,
    multi_thread: fields.multiThread,
    bind_device: fields.bindDevice,
    disable_relay_data: fields.disableRelayData,
    relay_all_peer_rpc: fields.relayAllPeerRpc,
  };
  return stringify(value as any);
}
