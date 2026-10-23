/** T09 / SPEC §6.1 — validate complete method names without repairing input. */
import {
  isJsonRpcRequest,
  isJsonRpcRequestEnvelope,
  type JsonValue,
  PORTAL_METHODS,
  PROFILE_METHODS,
  STORAGE_METHODS,
} from '@moonpool/protocol';
import { describe, expect, it } from 'vitest';

describe('SPEC §6.1 — existing protocol method names', () => {
  it.each([
    ...Object.values(PORTAL_METHODS),
    ...Object.values(PROFILE_METHODS),
    ...Object.values(STORAGE_METHODS),
    'profile.readDisplayName',
    'storage.readValue',
    'portalX.ping',
    'a.b',
    'profile.getURL',
    'storage2.get2',
    'customAPI.readURL',
    'a1.b2',
    'myScope.doThing',
    `${'a'.repeat(1_000)}.b`,
  ])('retains the valid request shape for %s', (method) => {
    const request = { jsonrpc: '2.0', id: 1, method, params: {} };
    expect(isJsonRpcRequestEnvelope(request)).toBe(true);
    expect(isJsonRpcRequest(request)).toBe(true);
  });

  const NON_STRING_METHODS: JsonValue[] = [null, false, 42, [], {}];
  it.each(NON_STRING_METHODS)('still rejects a non-string method %j', (method) => {
    const request = { jsonrpc: '2.0', id: 1, method };
    expect(isJsonRpcRequestEnvelope(request)).toBe(false);
    expect(isJsonRpcRequest(request)).toBe(false);
  });

  it.each([
    '',
    'ping',
    'profile',
    'profile.',
    '.get',
    'profile..get',
    'profile.get.more',
    '.profile.get',
    'profile.get.',
    'Profile.get',
    'profile.Get',
    'PROFILE.GET',
    'profile_get',
    'profile.get_name',
    'profile-name.get',
    'profile.get-name',
    '1profile.get',
    'profile.1get',
    'pro file.get',
    'profile.g et',
    ' profile.get',
    'profile.get ',
    'profile.get\n',
    'profile.get\r\n',
    'profile.get\u2028',
    'profile.get\u2029',
    'profile.get\t',
    'profile.get\u0000',
    '프로필.get',
    'profile.조회',
    'profilé.get',
    'profile.get\u00a0',
    'profile.get?x',
    'profile.get/extra',
    'profile.get:extra',
  ])('rejects the malformed method %j in both request guards', (method) => {
    const request = { jsonrpc: '2.0', id: 1, method, params: {} };
    expect(isJsonRpcRequestEnvelope(request)).toBe(false);
    expect(isJsonRpcRequest(request)).toBe(false);
  });

  it('keeps params-container validation separate for a valid method', () => {
    const request = { jsonrpc: '2.0', id: 1, method: 'profile.get', params: [] };
    expect(isJsonRpcRequestEnvelope(request)).toBe(true);
    expect(isJsonRpcRequest(request)).toBe(false);
  });
});
