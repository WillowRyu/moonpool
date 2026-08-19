import { createHost } from '@moonpool/host';
import type { MiniAppManifest } from '@moonpool/protocol';
import { describe, expect, it } from 'vitest';

const HELLO_MANIFEST: MiniAppManifest = {
  manifestVersion: 1,
  id: 'com.example.hello',
  name: 'Hello',
  version: '1.0.0',
  entry: 'index.html',
  protocolVersion: '0.1',
  permissions: ['profile', 'storage'],
};

describe('createHost', () => {
  it('returns a host that can accept one bridge connection', () => {
    const host = createHost({
      hostInfo: { name: 'test-host', version: '0.0.0', platform: 'browser' },
      manifest: HELLO_MANIFEST,
      grantedScopes: ['profile', 'storage'],
      environment: { locale: 'ko-KR', colorScheme: 'light' },
    });

    expect(typeof host.connect).toBe('function');
  });
});
