/** SPEC §8.1.1 / ADR 0022 — host data crosses realms as inspected snapshots. */
import { describe, expect, it, vi } from 'vitest';
import { decodeJson, encodeJson } from '../src/json-boundary';

describe('host-only JSON boundary', () => {
  it.each([null, false, 0, '', 12, 'hello', [null, false, { nested: [1, 'x'] }]])(
    'round-trips valid JSON without changing falsy/null values: %j',
    (value) => expect(decodeJson(encodeJson(value))).toEqual(value),
  );

  it('keeps __proto__ and constructor as data and detaches mutable values', () => {
    const value = JSON.parse('{"__proto__":{"polluted":true},"constructor":7,"items":[1]}');
    const text = encodeJson(value);
    value.items.push(2);
    const result = decodeJson(text);
    expect(result).toEqual(
      JSON.parse('{"__proto__":{"polluted":true},"constructor":7,"items":[1]}'),
    );
    expect(Reflect.get({}, 'polluted')).toBeUndefined();
  });

  it('accepts null-prototype records and shared acyclic values', () => {
    const shared = { n: 1 };
    const value = Object.assign(Object.create(null), { a: shared, b: shared });
    expect(decodeJson(encodeJson(value))).toEqual({ a: { n: 1 }, b: { n: 1 } });
  });

  it.each([
    undefined,
    NaN,
    Infinity,
    -Infinity,
    1n,
    Symbol('x'),
    () => {},
    new Date(),
    new Map(),
    new Set(),
    /x/,
    new Uint8Array([1]),
    { nested: undefined },
    { nested: NaN },
    [undefined],
    Array(2),
    Object.defineProperty({}, 'hidden', { value: 1 }),
    { [Symbol('x')]: 1 },
  ])('rejects non-JSON input before encoding: %s', (value) => {
    expect(() => encodeJson(value)).toThrow(TypeError);
  });

  it('does not execute getters or own toJSON functions', () => {
    const getter = vi.fn(() => 1);
    const toJSON = vi.fn(() => 'repaired');
    expect(() =>
      encodeJson({
        get value() {
          return getter();
        },
      }),
    ).toThrow(TypeError);
    expect(() => encodeJson({ toJSON })).toThrow(TypeError);
    expect(getter).not.toHaveBeenCalled();
    expect(toJSON).not.toHaveBeenCalled();
  });

  it('does not invoke inherited toJSON during snapshot encoding', () => {
    const convert = vi.fn(() => 'changed');
    Object.defineProperty(Object.prototype, 'toJSON', { value: convert, configurable: true });
    let text: string;
    try {
      text = encodeJson({ items: [1, { n: 2 }] });
    } finally {
      Reflect.deleteProperty(Object.prototype, 'toJSON');
    }
    expect(convert).not.toHaveBeenCalled();
    expect(text).toBe('{"items":[1,{"n":2}]}');
  });

  it('rejects cycles rather than removing or replacing them', () => {
    const value: { self?: unknown } = {};
    value.self = value;
    expect(() => encodeJson(value)).toThrow(TypeError);
  });

  it.each(['{', '{"value":1e999}', undefined, 123])('rejects invalid incoming text: %s', (text) => {
    expect(() => decodeJson(text)).toThrow(TypeError);
  });
});
