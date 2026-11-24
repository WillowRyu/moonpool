(async () => {
  const read = async (context) => {
    const outcome = { contextOrigin: context.origin, api: false, controller: null, scopes: [] };
    try {
      const container = context.navigator.serviceWorker;
      outcome.api = typeof container?.getRegistrations === 'function';
      if (outcome.api) {
        outcome.scopes = (await container.getRegistrations())
          .map((registration) => registration.scope)
          .sort();
        outcome.controller = container.controller?.scriptURL ?? null;
      }
    } catch (error) {
      outcome.error = String(error);
    }
    return outcome;
  };
  const inline = await read(window);
  let evidence = inline;
  let method = 'inline';
  let frameRead = null;
  if (window.origin !== 'null' && (!inline.api || inline.error)) {
    const frame = document.createElement('iframe');
    frame.setAttribute('sandbox', 'allow-same-origin');
    frame.srcdoc = '<!doctype html><p>Host-owned inspection frame</p>';
    const loaded = new Promise((resolve) => {
      const deadline = setTimeout(() => resolve(false), 2000);
      frame.addEventListener(
        'load',
        () => {
          clearTimeout(deadline);
          resolve(true);
        },
        { once: true },
      );
    });
    (document.body ?? document.documentElement).append(frame);
    try {
      frameRead = (await loaded)
        ? await read(frame.contentWindow)
        : { error: 'Inspection frame did not load' };
    } catch (error) {
      frameRead = { error: String(error) };
    } finally {
      frame.remove();
    }
    if (frameRead.api && !frameRead.error) {
      evidence = frameRead;
      method = 'srcdoc';
    }
  }
  window.workerProbeResult = {
    source: 'host',
    nonce: window.workerProbe.nonce,
    origin: window.origin,
    locationOrigin: location.origin,
    method,
    ...evidence,
    inline,
    frame: frameRead,
    data: window.origin === 'null' ? null : await window.workerAdmissionData(),
    pageScriptRan: window.workerTrap === true,
  };
})();
