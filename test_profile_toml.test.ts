import assert from 'node:assert/strict';
import test from 'node:test';
import { parse } from 'smol-toml';
import { defaultProfileToml, readCommonFields, writeCommonFields } from './src/profileToml';

test('default profile is valid TOML with safe native defaults', () => {
  const parsed: any = parse(defaultProfileToml());
  assert.equal(parsed.dhcp, true);
  assert.equal(parsed.network_identity.network_name, 'default');
  assert.equal(parsed.flags.enable_encryption, true);
});

test('form round trip preserves unknown advanced values', () => {
  const source = `${defaultProfileToml()}\n[secure_mode]\nenabled = true\nlocal_private_key = "key"\n`;
  const fields = readCommonFields(source);
  fields.networkName = 'gaming'; fields.addressMode = 'static'; fields.ipv4 = '10.20.0.2/24';
  const parsed: any = parse(writeCommonFields(source, fields));
  assert.equal(parsed.network_identity.network_name, 'gaming');
  assert.equal(parsed.ipv4, '10.20.0.2/24');
  assert.equal(parsed.secure_mode.local_private_key, 'key');
});

test('proxy mapping and list fields are normalized', () => {
  const fields = readCommonFields(defaultProfileToml());
  fields.proxyNetworks = '192.168.1.0/24->10.50.0.0/24\n10.0.0.0/8';
  fields.peers = 'tcp://one:11010, udp://two:11010';
  const parsed: any = parse(writeCommonFields(defaultProfileToml(), fields));
  assert.equal(parsed.proxy_network[0].mapped_cidr, '10.50.0.0/24');
  assert.equal(parsed.peer.length, 2);
});

test('common switches round trip through the flags table', () => {
  const fields = readCommonFields(defaultProfileToml());
  fields.noTun = true;
  fields.acceptDns = true;
  fields.enableExitNode = true;
  fields.disableUdpHolePunching = true;
  fields.relayAllPeerRpc = true;
  const parsed: any = parse(writeCommonFields(defaultProfileToml(), fields));
  assert.equal(parsed.flags.no_tun, true);
  assert.equal(parsed.flags.accept_dns, true);
  assert.equal(parsed.flags.enable_exit_node, true);
  assert.equal(parsed.flags.disable_udp_hole_punching, true);
  assert.equal(parsed.flags.relay_all_peer_rpc, true);
});
