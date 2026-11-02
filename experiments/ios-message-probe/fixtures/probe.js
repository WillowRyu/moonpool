// Public diagnostic payloads only; these are not Moonpool protocol fields.
(() => {
  const params = new URLSearchParams(location.search);
  const doc = params.get('doc');
  const instance = `page-${Math.random().toString(36).slice(2)}`;
  const inFrame = params.get('frame') === '1';
  const retained = window.webkit.messageHandlers.t26Page;
  const report = {
    doc,
    instance,
    origin: location.origin,
    href: location.href,
    mainFrame: window === top,
    replies: [],
    rejected: [],
    heldResults: [],
    legacyMessages: [],
    legacyResult: null,
    frames: [],
    handlerLookupErrors: {},
    removalAttempted: false,
    removedReference: [],
    early: window.t26Early,
    ready: false,
  };
  let resolveLegacy;
  new Promise((resolve) => {
    resolveLegacy = resolve;
  }).then((value) => {
    report.legacyResult = value;
    render();
  });
  function render() {
    const pre = document.querySelector('pre');
    if (pre) {
      pre.textContent = JSON.stringify(report, null, 2);
    }
  }
  async function send(kind, id = 3) {
    try {
      const value = await retained.postMessage({
        kind,
        id,
        doc,
        instance,
        claimedOrigin: 'moonpool://forged.invalid',
        claimedMainFrame: true,
      });
      if (kind === 'hold') {
        report.heldResults.push(value);
      } else {
        report.replies.push({ kind, value });
      }
    } catch (error) {
      report.rejected.push({ kind, message: String(error.message) });
    }
    render();
  }
  window.t26Hold = () => {
    void send('hold', 2);
  };
  window.t26Send = send;
  window.t26ReceiveLegacy = (response) => {
    report.legacyMessages.push(response);
    if (response.id === 2 && resolveLegacy) {
      const resolve = resolveLegacy;
      resolveLegacy = null;
      resolve(response.marker);
    }
    render();
    return { doc, instance };
  };
  window.t26TryRemoved = () => {
    report.removalAttempted = true;
    try {
      retained.postMessage({ kind: 'after-remove', doc, instance }).then(
        (value) => report.removedReference.push({ resolved: value }),
        (error) => report.removedReference.push({ rejected: String(error.message) }),
      );
    } catch (error) {
      report.removedReference.push({ threw: String(error.message) });
    }
  };
  window.t26Collect = () => {
    function visible(name) {
      try {
        return typeof window.webkit.messageHandlers[name] !== 'undefined';
      } catch (error) {
        report.handlerLookupErrors[name] = String(error.message);
        return false;
      }
    }
    report.pageHandlerVisible = visible('t26Page');
    report.isolatedHandlerVisible = visible('t26Isolated');
    report.isolatedGlobalVisible = typeof window.__t26WorldValue !== 'undefined';
    report.sharedDOMMarker = document.documentElement.dataset.t26World || null;
    return report;
  };
  addEventListener('message', (event) => {
    if (event.data?.kind !== 'frame-ready') {
      return;
    }
    const frame = [...document.querySelectorAll('iframe')].find(
      (item) => item.contentWindow === event.source,
    );
    if (frame) {
      report.frames.push({ ...event.data, messageOrigin: event.origin });
    }
    render();
  });
  void send('ready');
  void send('normal');
  if (!inFrame) {
    window.t26Hold();
  }
  addEventListener('DOMContentLoaded', () => {
    if (inFrame) {
      parent.postMessage(
        {
          kind: 'frame-ready',
          doc,
          origin: location.origin,
          pageHandlerVisible: typeof window.webkit.messageHandlers.t26Page !== 'undefined',
        },
        params.get('parent'),
      );
    } else {
      for (const [label, origin] of [
        ['self', params.get('self')],
        ['foreign', params.get('other')],
      ]) {
        const frame = document.createElement('iframe');
        const target = new URL(`${origin}/assets/index.html`);
        target.search = new URLSearchParams({
          doc: `${doc}:${label}`,
          frame: '1',
          parent: location.origin,
        }).toString();
        frame.src = target.href;
        document.body.append(frame);
      }
    }
    report.ready = true;
    render();
  });
})();
