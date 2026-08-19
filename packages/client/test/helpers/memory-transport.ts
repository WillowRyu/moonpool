import type { JsonValue, Transport } from '@moonpool/protocol';

export interface TransportPair {
  /** The end the mini app (the test) holds. */
  a: Transport;
  /** The end the host holds. */
  b: Transport;
}

/** Lets queued microtasks (message deliveries, promise chains) settle. */
export async function flush(turns = 20): Promise<void> {
  for (let i = 0; i < turns; i += 1) {
    await Promise.resolve();
  }
}

export function createLinkedTransports(): TransportPair {
  const handlersA = new Set<(message: JsonValue) => void>();
  const handlersB = new Set<(message: JsonValue) => void>();

  const makeEnd = (
    own: Set<(message: JsonValue) => void>,
    peer: Set<(message: JsonValue) => void>,
  ): Transport => ({
    send(message) {
      void Promise.resolve().then(() => {
        for (const handler of peer) {
          handler(message);
        }
      });
    },
    onMessage(handler) {
      own.add(handler);
      return () => {
        own.delete(handler);
      };
    },
    close() {
      own.clear();
    },
  });

  return { a: makeEnd(handlersA, handlersB), b: makeEnd(handlersB, handlersA) };
}
