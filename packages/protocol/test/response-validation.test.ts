/** T12 — a response guard proves JSON data and the JSON-RPC response shape. */
import { ERROR_CODES, isJsonRpcResponse, type JsonValue } from '@moonpool/protocol';
import { describe, expect, it, vi } from 'vitest';

function success(result: unknown = null) {
  return { jsonrpc: '2.0', id: 1, result };
}

function failure(error: unknown = { code: -32603, message: 'Internal error' }) {
  return { jsonrpc: '2.0', id: 1, error };
}

const malformed: Array<[string, unknown]> = [
  ['undefined frame', undefined],
  ['null frame', null],
  ['scalar frame', false],
  ['batch', [success()]],
  ['missing version', { id: 1, result: null }],
  ['wrong version', { ...success(), jsonrpc: '1.0' }],
  ['missing id', { jsonrpc: '2.0', result: null }],
  ['string id', { ...success(), id: '1' }],
  ['NaN id', { ...success(), id: Number.NaN }],
  ['infinite id', { ...failure(), id: Number.POSITIVE_INFINITY }],
  ['null success id', { ...success(), id: null }],
  ['neither outcome', { jsonrpc: '2.0', id: 1 }],
  ['both outcomes', { ...success(), error: { code: -32603, message: 'Internal error' } }],
  ['undefined result', { ...success(), result: undefined }],
  ['undefined error alongside result', { ...success(), error: undefined }],
  ['undefined result alongside error', { ...failure(), result: undefined }],
  ['null error', failure(null)],
  ['array error', failure([])],
  ['scalar error', failure('Internal error')],
  ['missing error code', failure({ message: 'Internal error' })],
  ['string error code', failure({ code: '-32603', message: 'Internal error' })],
  ['fractional error code', failure({ code: -32603.5, message: 'Internal error' })],
  ['NaN error code', failure({ code: Number.NaN, message: 'Internal error' })],
  ['infinite error code', failure({ code: Number.NEGATIVE_INFINITY, message: 'Internal error' })],
  ['missing error message', failure({ code: -32603 })],
  ['non-string error message', failure({ code: -32603, message: 42 })],
  ['undefined error data', failure({ code: -32603, message: 'Internal error', data: undefined })],
  ['non-JSON extra envelope member', { ...success(), extra: new Date(0) }],
  ['non-JSON extra error member', failure({ code: -32603, message: 'Internal error', extra: 1n })],
  ['inherited response members', Object.create(success())],
  ['inherited error members', failure(Object.create({ code: -32603, message: 'Internal error' }))],
];

describe('SPEC §4.3 / JSON-RPC §5 — response validation', () => {
  it.each(malformed)('rejects %s', (_name, value) => {
    expect(isJsonRpcResponse(value)).toBe(false);
  });

  const nonJson: Array<[string, () => unknown]> = [
    ['undefined leaf', () => ({ nested: undefined })],
    ['non-finite leaf', () => ({ nested: Number.NaN })],
    ['Date', () => new Date(0)],
    ['Map', () => new Map()],
    ['function', () => () => null],
    ['bigint', () => 1n],
    ['symbol', () => Symbol('invalid')],
    ['sparse array', () => Array(1)],
    [
      'cycle',
      () => {
        const value: Record<string, unknown> = {};
        value.self = value;
        return value;
      },
    ],
  ];

  it.each(nonJson)('rejects %s in result and error.data', (_name, make) => {
    expect(isJsonRpcResponse(success(make()))).toBe(false);
    expect(
      isJsonRpcResponse(failure({ code: -32603, message: 'Internal error', data: make() })),
    ).toBe(false);
  });

  it.each(['jsonrpc', 'id', 'result', 'error'])('does not evaluate a %s getter', (key) => {
    const getter = vi.fn(() => {
      throw new Error('must not execute');
    });
    const frame = success();
    Object.defineProperty(frame, key, { enumerable: true, get: getter });
    expect(isJsonRpcResponse(frame)).toBe(false);
    expect(getter).not.toHaveBeenCalled();
  });

  it('does not evaluate nested accessors or toJSON', () => {
    const getter = vi.fn(() => null);
    const toJSON = vi.fn(() => null);
    const value = Object.defineProperty({}, 'nested', { enumerable: true, get: getter });
    expect(isJsonRpcResponse(success(value))).toBe(false);
    expect(
      isJsonRpcResponse(failure({ code: -32603, message: 'Internal error', data: value })),
    ).toBe(false);
    expect(isJsonRpcResponse(success({ toJSON }))).toBe(false);
    expect(getter).not.toHaveBeenCalled();
    expect(toJSON).not.toHaveBeenCalled();
  });

  it('rejects hidden and symbol members', () => {
    const hidden = Object.defineProperty(success(), 'extra', { value: null });
    expect(isJsonRpcResponse(hidden)).toBe(false);
    expect(isJsonRpcResponse({ ...success(), [Symbol('extra')]: null })).toBe(false);
  });

  it('returns false when structural inspection throws', () => {
    const pair = Proxy.revocable(success(), {});
    pair.revoke();
    expect(isJsonRpcResponse(pair.proxy)).toBe(false);
    expect(
      isJsonRpcResponse(
        new Proxy(success(), {
          ownKeys() {
            throw new Error('uninspectable');
          },
        }),
      ),
    ).toBe(false);
  });

  it.each([null, false, 0, '', [], {}, { nested: [null, false, 0, ''] }])(
    'accepts the JSON result %j',
    (result) => {
      expect(isJsonRpcResponse(success(result))).toBe(true);
    },
  );

  it.each([...Object.values(ERROR_CODES), 0, 1234])(
    'accepts integer error code %i without a whitelist',
    (code) => {
      expect(isJsonRpcResponse(failure({ code, message: '' }))).toBe(true);
    },
  );

  it.each([null, false, 0, '', [], {}, { scope: 'profile' }])(
    'accepts optional JSON error data %j',
    (data) => {
      expect(isJsonRpcResponse(failure({ code: -32000, message: 'Permission denied', data }))).toBe(
        true,
      );
    },
  );

  it.each([null, 0, -1, 1.5, Number.MAX_VALUE])('preserves diagnostic error id %s', (id) => {
    // The host can echo invalid finite request ids. Only pending Map keys correlate.
    expect(isJsonRpcResponse({ ...failure(), id })).toBe(true);
  });

  it('accepts JSON extras, null prototypes, and an own __proto__ data member', () => {
    const frame = {
      ...failure({ code: -32000, message: 'Permission denied', extra: [] }),
      extra: null,
    };
    Object.setPrototypeOf(frame, null);
    Object.setPrototypeOf(frame.error, null);
    Object.defineProperty(frame, '__proto__', { enumerable: true, value: { valid: true } });
    expect(isJsonRpcResponse(frame)).toBe(true);
  });

  it('preserves frozen shared data and accepts deep JSON without recursion', () => {
    const shared = Object.freeze({ enabled: true });
    const frame = Object.freeze(success(Object.freeze({ left: shared, right: shared })));
    expect(isJsonRpcResponse(frame)).toBe(true);
    expect(frame.result).toEqual({ left: shared, right: shared });
    let deep: JsonValue = null;
    for (let i = 0; i < 10_000; i += 1) {
      deep = { nested: deep };
    }
    expect(isJsonRpcResponse(success(deep))).toBe(true);
  });
});
