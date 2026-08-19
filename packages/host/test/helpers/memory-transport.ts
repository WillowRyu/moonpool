import type { Transport } from '@moonpool/protocol';

export interface TransportPair {
  /** The end the mini app (the test) holds. */
  a: Transport;
  /** The end the host holds. */
  b: Transport;
}

/** Lets queued microtasks (message deliveries, promise chains) settle. */
export async function flush(turns = 20): Promise<void> {
  for (let i = 0; i < turns; i += 1) await Promise.resolve();
}
