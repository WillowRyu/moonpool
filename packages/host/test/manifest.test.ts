/** T06 / SPEC §6.1, §7 — finish manifest admission before loading a Portal. */
import { ERROR_CODES, PROFILE_METHODS, STORAGE_METHODS } from '@moonpool/protocol';
import { describe, expect, it } from 'vitest';
import { createClient } from '../../client/src/index';
import { createHost, ManifestError, parseManifest } from '../src/index';
import { createLinkedTransports } from './helpers/memory-transport';

const VALID = {
  manifestVersion: 1,
  id: 'com.example.hello',
  name: 'Hello',
  version: '1.0.0',
  entry: 'index.html',
  protocolVersion: '0.1',
  permissions: ['profile', 'storage'],
};

function json(overrides: Record<string, unknown> = {}) {
  return JSON.stringify({ ...VALID, ...overrides });
}

function rejection(source: unknown): ManifestError {
  try {
    parseManifest(source);
  } catch (error) {
    if (error instanceof ManifestError) {
      return error;
    }
    throw error;
  }
  throw new Error('expected manifest admission to reject the source');
}

describe('SPEC §7 — public parser composes field validation and admission', () => {
  it.each([
    { source: null, field: 'json' },
    { source: '{', field: 'json' },
    { source: '[]', field: 'manifest' },
    { source: json({ manifestVersion: 2 }), field: 'manifestVersion' },
    { source: json({ id: 'invalid' }), field: 'id' },
    { source: json({ name: '😀'.repeat(41) }), field: 'name' },
    { source: json({ version: 'v1.0.0' }), field: 'version' },
    { source: json({ entry: null }), field: 'entry' },
    { source: json({ protocolVersion: 0.1 }), field: 'protocolVersion' },
    { source: json({ permissions: ['profile', 1] }), field: 'permissions' },
  ])('retains the field validation failure for $field', ({ source, field }) => {
    expect(rejection(source).field).toBe(field);
  });

  it.each(Object.keys(VALID))('still requires the member %s', (field) => {
    const manifest: Record<string, unknown> = { ...VALID };
    delete manifest[field];
    expect(rejection(JSON.stringify(manifest)).field).toBe(field);
  });

  it('leaves protocol version negotiation to the handshake', () => {
    expect(parseManifest(json({ protocolVersion: '0.2' })).protocolVersion).toBe('0.2');
  });
});

describe('SPEC §6.1 / §7 — recognized capability namespaces', () => {
  it('accepts the specified manifest without changing its fields', () => {
    expect(parseManifest(json())).toEqual(VALID);
  });

  it.each([
    { permissions: [] },
    { permissions: ['profile'] },
    { permissions: ['storage'] },
    { permissions: ['storage', 'profile', 'storage'] },
  ])('preserves a valid permissions array $permissions', ({ permissions }) => {
    expect(parseManifest(json({ permissions })).permissions).toEqual(permissions);
  });

  it.each([...Object.values(PROFILE_METHODS), ...Object.values(STORAGE_METHODS)])(
    'recognizes the namespace of the protocol capability %s',
    (method) => {
      const scope = method.slice(0, method.indexOf('.'));
      expect(parseManifest(json({ permissions: [scope] })).permissions).toEqual([scope]);
    },
  );

  it.each([
    '',
    'camera',
    'Profile',
    'profile ',
    ' storage',
    'profile.get',
    'storage.*',
    '*',
    'portal',
    'constructor',
    '__proto__',
    'toString',
  ])('rejects the unrecognized permission %j rather than dropping it', (scope) => {
    expect(rejection(json({ permissions: ['profile', scope, 'storage'] })).field).toBe(
      'permissions',
    );
  });

  it('reports unknown scopes without echoing their untrusted contents', () => {
    const marker = 'private-scope-marker';
    const error = rejection(json({ permissions: [marker] }));

    expect(error.field).toBe('permissions');
    expect(error.message).not.toContain(marker);
  });
});

describe('SPEC §7 — package-relative entry containment', () => {
  it.each([
    'index.html',
    'pages/start.html',
    './index.html',
    'pages/../index.html',
    'a/b/../../index.html',
    './a/./b/../start',
    'a//b/../index.html',
    '시작/화면.html',
    'pages/hello world.html',
    'folder name/index.html',
    '.index',
    '.../index.html',
    '..index.html',
  ])('accepts the package-relative path %j without rewriting it', (entry) => {
    expect(parseManifest(json({ entry })).entry).toBe(entry);
  });

  it.each([
    '/index.html',
    '//other.example/index.html',
    '../index.html',
    'a/../../index.html',
    './../index.html',
    'a/b/../../../index.html',
    '../a/index.html',
    'a/../../a/index.html',
  ])('rejects an absolute path or package-root escape %j', (entry) => {
    expect(rejection(json({ entry })).field).toBe('entry');
  });

  it.each([
    'https://other.example/index.html',
    'http:other.example',
    'file:///index.html',
    'data:text/html,Hello',
    'javascript:alert(1)',
    'moonpool://com.example.other/index.html',
    'C:/index.html',
    'C:index.html',
    'pages/file:name.html',
    '../index.html?inside=true',
    'index.html?theme=dark',
    'index.html#section',
    '\\index.html',
    '..\\index.html',
    'pages\\..\\index.html',
    '\\\\server\\share\\index.html',
    'pages/%2e%2e/index.html',
    '%2e%2e/index.html',
    '%2Findex.html',
    'pages%5c..%5cindex.html',
    '%252e%252e/index.html',
    'pages/hello%20world.html',
    '100%.html',
    ' index.html',
    'index.html ',
    '\u00a0index.html',
    'index.html\u3000',
    'pages/in\u0000dex.html',
    'pages/in\tdex.html',
    'pages/in\ndex.html',
    'pages/in\rdex.html',
    'pages/in\u007fdex.html',
    'pages/in\u0085dex.html',
  ])('rejects the nonportable entry syntax %j without repairing it', (entry) => {
    expect(rejection(json({ entry })).field).toBe('entry');
  });

  it.each(['', '.', '..', './', 'pages/', 'pages/.', 'pages/..', 'pages/../', 'a//'])(
    'requires a final file segment rather than %j',
    (entry) => {
      expect(rejection(json({ entry })).field).toBe('entry');
    },
  );

  it('reports invalid entry syntax without echoing its untrusted contents', () => {
    const marker = 'private-entry-marker';
    const error = rejection(json({ entry: `../${marker}` }));

    expect(error.field).toBe('entry');
    expect(error.message).not.toContain(marker);
  });
});

describe('SPEC §5 / §9.3 — parsing does not grant or install capabilities', () => {
  it.each([
    {
      label: 'declared storage without a host grant',
      permissions: ['storage'],
      grants: [],
      expectedScopes: [],
      code: ERROR_CODES.PERMISSION_DENIED,
    },
    {
      label: 'a host grant without a declared permission',
      permissions: [],
      grants: ['storage'],
      expectedScopes: [],
      code: ERROR_CODES.PERMISSION_DENIED,
    },
    {
      label: 'recognized and granted storage without an installed provider',
      permissions: ['storage'],
      grants: ['storage'],
      expectedScopes: ['storage'],
      code: ERROR_CODES.CAPABILITY_UNAVAILABLE,
    },
  ])(
    'retains dispatch behavior for $label',
    async ({ permissions, grants, expectedScopes, code }) => {
      const bridge = createLinkedTransports();
      const client = createClient({ transport: bridge.a });
      createHost({
        hostInfo: { name: 'manifest-test-host', version: '0.1.0', platform: 'browser' },
        manifest: parseManifest(json({ permissions })),
        grantedScopes: grants,
        environment: { locale: 'en', colorScheme: 'light' },
      }).connect(bridge.b);

      try {
        const initialized = await client.initialize();
        expect(initialized.grantedScopes).toEqual(expectedScopes);
        await expect(client.call(STORAGE_METHODS.GET, { key: 'settings' })).rejects.toMatchObject({
          code,
        });
      } finally {
        client.close();
        bridge.b.close();
      }
    },
  );
});
