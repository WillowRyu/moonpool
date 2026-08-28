/**
 * @moonpool/transport-iframe — browser development transport
 * (iframe + window.postMessage, SPEC §3.1).
 *
 * This is the only browser-side package allowed to touch platform APIs.
 * The host and the Portal both use this one factory; what differs is only
 * which window each passes as its peer, and that is the caller's knowledge.
 */

import type { JsonValue, Transport } from '@moonpool/protocol';
import { isFromPeer } from './peer';

export { isFromPeer } from './peer';

/** The only part of a Window this transport needs from its peer. */
export interface PeerWindow {
  postMessage(message: unknown, targetOrigin: string): void;
}

export interface IframeTransportConfig {
  /** The window on the other end: `iframe.contentWindow`, or `window.parent`. */
  peerWindow: PeerWindow;
  /** SPEC §8.1/§9.1 — the peer's exact serialised origin. Never `'*'`. */
  peerOrigin: string;
  /** The window whose `message` events are the inbound side. Defaults to `window`. */
  localWindow?: Window;
}

export function createIframeTransport(config: IframeTransportConfig): Transport {
  const { peerWindow, peerOrigin } = config;
  const localWindow = config.localWindow ?? window;

  const handlers = new Set<(message: JsonValue) => void>();

  const onWindowMessage = (event: MessageEvent): void => {
    // SPEC §9.1: `window`'s message event is a public mailbox — any frame on
    // the page can post to it. Everything that is not the peer is dropped.
    if (!isFromPeer(event, { origin: peerOrigin, window: peerWindow })) {
      return;
    }

    // Snapshot: a handler may unsubscribe while we are iterating.
    for (const handler of [...handlers]) {
      try {
        handler(event.data as JsonValue);
      } catch (error) {
        // Isolate the handlers from each other the way the browser isolates
        // its listeners — but do not swallow. Re-thrown with no caller above
        // it, this surfaces as an uncaught error / window.onerror instead of
        // vanishing into the bridge.
        queueMicrotask(() => {
          throw error;
        });
      }
    }
  };

  localWindow.addEventListener('message', onWindowMessage);

  return {
    send(message) {
      // The second argument is a browser-enforced delivery condition: if the
      // Portal has navigated away, the frame is not delivered at all. `'*'`
      // would hand every frame to whoever happens to be there instead.
      peerWindow.postMessage(message, peerOrigin);
    },

    onMessage(handler) {
      handlers.add(handler);
      return () => {
        handlers.delete(handler);
      };
    },

    close() {
      localWindow.removeEventListener('message', onWindowMessage);
      handlers.clear();
    },
  };
}
