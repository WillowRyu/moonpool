/** Host-only realm boundary, SPEC §8.1.1. Never apply this to inbound guest frames. */
import { isJsonValue, type JsonValue } from '@moonpool/protocol';

const invalid = () => new TypeError('expected public JSON data');

export function encodeJson(value: unknown): string {
  if (!isJsonValue(value)) {
    throw invalid();
  }

  const copies = new Map<object, JsonValue>();
  const work: Array<{ source: object; target: object }> = [];
  const copy = (current: unknown): JsonValue => {
    if (current === null || typeof current === 'string' || typeof current === 'boolean') {
      return current;
    }
    if (typeof current === 'number' && Number.isFinite(current)) {
      return current;
    }
    if (typeof current !== 'object' || current === null) {
      throw invalid();
    }
    const known = copies.get(current);
    if (known !== undefined) {
      return known;
    }
    const target: JsonValue = Array.isArray(current) ? [] : {};
    // Remove inherited toJSON, including on arrays, before using JSON.stringify.
    Object.setPrototypeOf(target, null);
    copies.set(current, target);
    work.push({ source: current, target });
    return target;
  };

  const snapshot = copy(value);
  while (work.length > 0) {
    const next = work.pop();
    if (next === undefined) {
      throw invalid();
    }
    for (const key of Reflect.ownKeys(next.source)) {
      if (Array.isArray(next.source) && key === 'length') {
        continue;
      }
      const descriptor = Object.getOwnPropertyDescriptor(next.source, key);
      if (
        typeof key !== 'string' ||
        descriptor === undefined ||
        !descriptor.enumerable ||
        !('value' in descriptor)
      ) {
        throw invalid();
      }
      Object.defineProperty(next.target, key, {
        value: copy(descriptor.value),
        enumerable: true,
        writable: true,
        configurable: true,
      });
    }
  }
  // Recheck the detached snapshot; reflective source data must not bypass validation.
  if (!isJsonValue(snapshot)) {
    throw invalid();
  }
  const text = JSON.stringify(snapshot);
  if (typeof text !== 'string') {
    throw invalid();
  }
  return text;
}

export function decodeJson(text: unknown): JsonValue {
  if (typeof text !== 'string') {
    throw invalid();
  }
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    throw invalid();
  }
  if (!isJsonValue(value)) {
    throw invalid();
  }
  return value;
}
