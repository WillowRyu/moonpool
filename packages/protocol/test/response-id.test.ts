/** T08 — an uncorrelated error id is distinct from a valid Moonpool request id. */
import {
  ERROR_CODES,
  isJsonRpcRequest,
  isJsonRpcRequestEnvelope,
  isJsonRpcResponse,
  type JsonRpcResponse,
  type JsonValue,
} from '@moonpool/protocol';
import { describe, expect, it } from 'vitest';

const UNCORRELATED: JsonRpcResponse = {
  jsonrpc: '2.0',
  id: null,
  error: { code: ERROR_CODES.INVALID_REQUEST, message: 'Invalid Request' },
};

const MALFORMED_NULL_IDS: JsonValue[] = [
  { jsonrpc: '2.0', id: null, result: {} },
  { jsonrpc: '2.0', id: null },
  { jsonrpc: '2.0', id: null, result: {}, error: { code: -32600, message: 'Invalid Request' } },
  { jsonrpc: '2.0', id: null, error: null },
  { jsonrpc: '2.0', id: null, error: { code: -32600 } },
  { jsonrpc: '2.0', id: null, error: { code: 'invalid', message: 'Invalid Request' } },
];

const NUMERIC_IDS: JsonValue[] = [
  { jsonrpc: '2.0', id: 1, result: false },
  { jsonrpc: '2.0', id: 2, error: { code: -32600, message: 'Invalid Request' } },
];

describe('JSON-RPC 2.0 §5 / SPEC §4.1 — response ids', () => {
  it('represents and recognizes an error without a request id', () => {
    expect(isJsonRpcResponse(UNCORRELATED)).toBe(true);
  });

  it.each(MALFORMED_NULL_IDS)('does not admit the malformed null-id response %j', (frame) => {
    expect(isJsonRpcResponse(frame)).toBe(false);
  });

  it('does not make a null id valid for requests or request envelopes', () => {
    const request = { jsonrpc: '2.0', id: null, method: 'portal.ping' };
    expect(isJsonRpcRequestEnvelope(request)).toBe(false);
    expect(isJsonRpcRequest(request)).toBe(false);
  });

  it.each(NUMERIC_IDS)('retains numeric response ids in %j', (frame) => {
    expect(isJsonRpcResponse(frame)).toBe(true);
  });
});
