export type ProcessStatus = 'stopped' | 'starting' | 'running' | 'stopping' | 'restart_wait' | 'crashed' | 'error';
export interface ApiError { code: string; message: string; details?: string }
export interface ApiResponse<T = unknown> { success: boolean; data?: T; error?: ApiError }
export interface PluginSettings { auto_start: boolean; auto_restart_core: boolean }
export interface ProfileSummary { id: string; name: string; created_at: string; updated_at: string }
export interface Profile extends ProfileSummary { toml: string }
export interface ProcessState { status: ProcessStatus; profile_id: string | null; pid: number | null; restart_attempt: number; error: string | null }
export interface PluginState { schema_version: number; binary_version: string; settings: PluginSettings; profiles: ProfileSummary[]; selected_profile_id: string | null; process: ProcessState; restart_required: boolean }
export interface RuntimeSnapshot { process: ProcessState; node: unknown; peers: unknown[]; routes: unknown[]; logs: string[]; cli_error: string | null }
export interface SaveProfileResult { profile: ProfileSummary; restart_required: boolean }
export interface CommonProfileFields {
  hostname: string; networkName: string; networkSecret: string;
  addressMode: 'dhcp' | 'static'; ipv4: string;
  peers: string; listeners: string; proxyNetworks: string; exitNodes: string;
  encryption: boolean; ipv6: boolean; privateMode: boolean; latencyFirst: boolean;
  disableUpnp: boolean; udpBroadcastRelay: boolean; noTun: boolean; useSmoltcp: boolean;
  disableP2p: boolean; p2pOnly: boolean; lazyP2p: boolean; needP2p: boolean;
  enableExitNode: boolean; acceptDns: boolean; proxyForwardBySystem: boolean;
  disableTcpHolePunching: boolean; disableUdpHolePunching: boolean; disableSymHolePunching: boolean;
  multiThread: boolean; bindDevice: boolean; disableRelayData: boolean; relayAllPeerRpc: boolean;
}
