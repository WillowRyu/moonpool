/**
 * T05 / SPEC §7 — parse required manifest fields without coercion.
 * This internal stage does not admit package paths or authorize scope names.
 */
import { describe, expect, it } from 'vitest';
import { ManifestError, parseManifestFields } from '../src/manifest-fields';

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
    parseManifestFields(source);
  } catch (error) {
    if (error instanceof ManifestError) {
      return error;
    }
    throw error;
  }
  throw new Error('expected manifest validation to reject the source');
}

describe('SPEC §7 — manifest source and required members', () => {
  it('parses the documented manifest without changing its field values', () => {
    expect(parseManifestFields(json())).toEqual(VALID);
  });

  it.each([{ source: undefined }, { source: null }, { source: 1 }, { source: {} }, { source: [] }])(
    'rejects non-text source $source before JSON coercion',
    ({ source }) => {
      expect(rejection(source).field).toBe('json');
    },
  );

  it.each(['', '{', '{"id":', '{"id":"x",}', 'undefined'])(
    'rejects malformed JSON %j',
    (source) => {
      expect(rejection(source).field).toBe('json');
    },
  );

  it('does not echo malformed source text in a parser error', () => {
    const marker = 'private-source-marker';
    const error = rejection(`{"name":"${marker}"`);

    expect(error.field).toBe('json');
    expect(error.message).not.toContain(marker);
  });

  it.each(['null', 'false', '0', '"text"', '[]'])(
    'requires a JSON object rather than %s',
    (source) => {
      expect(rejection(source).field).toBe('manifest');
    },
  );

  it.each(Object.keys(VALID))('requires the own member %s', (field) => {
    const manifest: Record<string, unknown> = { ...VALID };
    delete manifest[field];

    expect(rejection(JSON.stringify(manifest)).field).toBe(field);
  });

  it('does not satisfy a missing required member through Object.prototype', () => {
    const manifest: Record<string, unknown> = { ...VALID };
    delete manifest.id;
    const original = Object.getOwnPropertyDescriptor(Object.prototype, 'id');
    let error: ManifestError | undefined;
    try {
      Object.defineProperty(Object.prototype, 'id', {
        configurable: true,
        writable: true,
        value: VALID.id,
      });
      error = rejection(JSON.stringify(manifest));
    } finally {
      if (original === undefined) {
        Reflect.deleteProperty(Object.prototype, 'id');
      } else {
        Object.defineProperty(Object.prototype, 'id', original);
      }
    }

    expect(error?.field).toBe('id');
  });

  it.each([
    { field: 'manifestVersion', value: '1' },
    { field: 'id', value: 123 },
    { field: 'name', value: [] },
    { field: 'version', value: 1 },
    { field: 'entry', value: null },
    { field: 'protocolVersion', value: 0.1 },
    { field: 'permissions', value: 'storage' },
  ])('rejects the wrong type of $field', ({ field, value }) => {
    expect(rejection(json({ [field]: value })).field).toBe(field);
  });

  it.each([0, 2, -1, 1.1, null])('requires manifestVersion 1, rejecting %j', (value) => {
    expect(rejection(json({ manifestVersion: value })).field).toBe('manifestVersion');
  });

  it('allows an empty permissions array', () => {
    expect(parseManifestFields(json({ permissions: [] })).permissions).toEqual([]);
  });

  it.each([{ value: null }, { value: 1 }, { value: {} }, { value: ['storage'] }])(
    'rejects a non-string permissions member $value',
    ({ value }) => {
      expect(rejection(json({ permissions: ['profile', value] })).field).toBe('permissions');
    },
  );

  it('preserves declared strings without trimming, deduplicating, or negotiating a version', () => {
    const manifest = parseManifestFields(
      json({
        name: ' Hello ',
        protocolVersion: '0.2',
        permissions: ['storage', 'storage'],
      }),
    );

    expect(manifest.name).toBe(' Hello ');
    expect(manifest.protocolVersion).toBe('0.2');
    expect(manifest.permissions).toEqual(['storage', 'storage']);
  });
});

describe('SPEC §7 — the exact mini-app id pattern', () => {
  it.each(['com.example.hello', 'a.b', 'com.example.my-app', 'com.-app-', '123.456-789'])(
    'accepts %s',
    (id) => {
      expect(parseManifestFields(json({ id })).id).toBe(id);
    },
  );

  it.each([
    'hello',
    '.com.example',
    'com..example',
    'com.Example',
    'com.example_app',
    'com.example/',
    'com.example\n',
    'com.example\r\n',
    ' com.example',
    'com.example.',
  ])('rejects %j', (id) => {
    expect(rejection(json({ id })).field).toBe('id');
  });
});

describe('SPEC §7 / ADR 0010 — name length in Unicode code points', () => {
  it.each(['A', '한'.repeat(40), '😀'.repeat(40), 'e\u0301'.repeat(20)])(
    'accepts the valid code-point length of %j',
    (name) => {
      expect(parseManifestFields(json({ name })).name).toBe(name);
    },
  );

  it.each(['', 'x'.repeat(41), '😀'.repeat(41), 'e\u0301'.repeat(21)])(
    'rejects the invalid code-point length of %j',
    (name) => {
      expect(rejection(json({ name })).field).toBe('name');
    },
  );
});

describe('SPEC §7 — SemVer 2.0.0 syntax', () => {
  it.each([
    '0.0.0',
    '1.2.3',
    '1.2.3-alpha.1',
    '1.2.3+001',
    '1.2.3-alpha.1+build.001',
    '1.2.3-0A',
    '1.0.0-x-y-z.--',
    '9999999999999999999999999.0.0',
  ])('accepts %s without parsing its numeric components into JavaScript numbers', (version) => {
    expect(parseManifestFields(json({ version })).version).toBe(version);
  });

  it.each([
    '1',
    '1.2',
    'v1.2.3',
    '01.2.3',
    '1.02.3',
    '1.2.03',
    '1.2.3-01',
    '1.2.3-alpha..1',
    '1.2.3+',
    '1.2.3+build..1',
    '1.2.3-beta_1',
    '1.2.3\n',
    '1.2.3 ',
    ' 1.2.3',
    '1.2.3-α',
  ])('rejects %j', (version) => {
    expect(rejection(json({ version })).field).toBe('version');
  });
});
