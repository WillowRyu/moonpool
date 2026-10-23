/** Internal receive inspection. Transport's JsonValue type is not runtime proof. */
import {
  isJsonObject,
  isJsonRpcRequestEnvelope,
  isJsonValue,
  type JsonRpcRequestEnvelope,
  type JsonValue,
} from '@moonpool/protocol';

type IncomingRequest = {
  kind: 'request';
  id: number;
  header: JsonRpcRequestEnvelope | undefined;
  envelopeIsJson: boolean;
  params: unknown;
  paramsShapeValid: boolean;
};
type Incoming = IncomingRequest | { kind: 'batch' } | { kind: 'unaddressable' };

function storedValue(descriptor: PropertyDescriptor | undefined): unknown {
  return descriptor !== undefined && Object.hasOwn(descriptor, 'value')
    ? descriptor.value
    : undefined;
}

function invalidEnvelope(id: number): IncomingRequest {
  return {
    kind: 'request',
    id,
    header: undefined,
    envelopeIsJson: false,
    params: undefined,
    paramsShapeValid: false,
  };
}

function isParamsContainer(value: unknown): boolean {
  try {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
  } catch {
    return false;
  }
}

/** SPEC §4.1 / §4.2 / ADR 0016 — no getters, coercion, or mutation of received data. */
export function inspectIncomingRequest(value: unknown): Incoming {
  let id: unknown;
  try {
    if (Array.isArray(value)) {
      return { kind: 'batch' };
    }
    if ((typeof value !== 'object' && typeof value !== 'function') || value === null) {
      return { kind: 'unaddressable' };
    }

    // Recover only an own stored id before inspecting the remaining structure.
    id = storedValue(Object.getOwnPropertyDescriptor(value, 'id'));
    if (typeof id !== 'number') {
      return { kind: 'unaddressable' };
    }

    const descriptors = Object.getOwnPropertyDescriptors(value);
    const jsonrpc = storedValue(
      Object.hasOwn(descriptors, 'jsonrpc') ? descriptors.jsonrpc : undefined,
    );
    const method = storedValue(
      Object.hasOwn(descriptors, 'method') ? descriptors.method : undefined,
    );
    const hasParams = Object.hasOwn(descriptors, 'params');
    const paramsDescriptor = hasParams ? descriptors.params : undefined;
    const params = storedValue(paramsDescriptor);
    const paramsDescriptorValid =
      !hasParams ||
      (paramsDescriptor !== undefined &&
        paramsDescriptor.enumerable === true &&
        Object.hasOwn(paramsDescriptor, 'value'));

    // This view is only for inspecting the envelope. Validate the original params
    // later, at their approved precedence; never dispatch a repaired payload.
    delete descriptors.params;
    const envelope: unknown = Object.create(Object.getPrototypeOf(value), descriptors);
    const envelopeIsJson = paramsDescriptorValid && isJsonValue(envelope);

    let header: JsonRpcRequestEnvelope | undefined;
    if (typeof jsonrpc === 'string' && typeof method === 'string') {
      const routing = { jsonrpc, id, method };
      if (isJsonRpcRequestEnvelope(routing)) {
        header = routing;
      }
    }
    return {
      kind: 'request',
      id,
      header,
      envelopeIsJson,
      params,
      paramsShapeValid: !hasParams || isParamsContainer(params),
    };
  } catch {
    // A recovered id still follows sequence/error rules. Unknown ids stay silent.
    return typeof id === 'number' ? invalidEnvelope(id) : { kind: 'unaddressable' };
  }
}

/** Call after the container gate: undefined here means actual omission. */
export function isJsonParams(value: unknown): value is Record<string, JsonValue> | undefined {
  return value === undefined || (isJsonValue(value) && isJsonObject(value));
}
