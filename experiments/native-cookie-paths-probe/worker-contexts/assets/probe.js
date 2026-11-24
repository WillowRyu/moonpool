async function observeWorkerContext(name) {
  const origin = window.origin;
  const violations = [];
  document.addEventListener('securitypolicyviolation', (event) => {
    violations.push({
      directive: event.effectiveDirective,
      disposition: event.disposition,
      blockedURI: event.blockedURI,
    });
  });

  const dedicatedResult = () =>
    new Promise((resolve) => {
      let worker;
      try {
        worker = new Worker(new URL('/dedicated.js', origin));
      } catch (error) {
        resolve({ outcome: 'rejected', error: error.name });
        return;
      }
      function finish(result) {
        clearTimeout(deadline);
        worker.terminate();
        resolve(result);
      }
      const deadline = setTimeout(() => finish({ outcome: 'timeout' }), 5000);
      worker.addEventListener('message', (event) =>
        finish({ outcome: 'message', value: event.data }),
      );
      worker.addEventListener('error', () => finish({ outcome: 'rejected', error: 'ErrorEvent' }));
    });

  const serviceResult = async () => {
    if (typeof navigator.serviceWorker?.register !== 'function') {
      return { outcome: 'unavailable', error: 'NoRegistrationAPI' };
    }
    let registration;
    try {
      registration = await navigator.serviceWorker.register(new URL('/service.js', origin), {
        scope: new URL(`/scope/${name}/`, origin).href,
      });
    } catch (error) {
      return { outcome: 'rejected', error: error.name };
    }
    const worker = registration.active ?? registration.waiting ?? registration.installing;
    if (!worker) {
      return { outcome: 'missing' };
    }
    return new Promise((resolve) => {
      const deadline = setTimeout(() => {
        worker.removeEventListener('statechange', changed);
        resolve({ outcome: 'timeout' });
      }, 5000);
      function changed() {
        if (worker.state !== 'activated') {
          return;
        }
        clearTimeout(deadline);
        worker.removeEventListener('statechange', changed);
        resolve({ outcome: 'activated', scope: registration.scope });
      }
      worker.addEventListener('statechange', changed);
      changed();
    });
  };

  const [dedicated, service] = await Promise.all([dedicatedResult(), serviceResult()]);
  await new Promise((resolve) => setTimeout(resolve, 200));
  return {
    name,
    origin,
    url: location.href,
    secure: isSecureContext,
    dedicated,
    service,
    violations,
  };
}

(async () => {
  const childResult = (name) =>
    new Promise((resolve, reject) => {
      const frame = document.createElement('iframe');
      const script = `(${observeWorkerContext.toString()})(${JSON.stringify(name)}).then(result => parent.postMessage(result, window.origin));`;
      const deadline = setTimeout(() => {
        window.removeEventListener('message', receive);
        reject(new Error(`No report from ${name}`));
      }, 10000);
      function receive(event) {
        if (
          event.source !== frame.contentWindow ||
          event.origin !== window.origin ||
          event.data?.name !== name
        ) {
          return;
        }
        clearTimeout(deadline);
        window.removeEventListener('message', receive);
        resolve(event.data);
      }
      window.addEventListener('message', receive);
      if (name === 'srcdoc') {
        frame.srcdoc = `<!doctype html><meta charset=utf-8><script>${script}</script>`;
      }
      document.body.append(frame);
      if (name === 'blank') {
        const child = frame.contentDocument;
        const element = child.createElement('script');
        element.textContent = script;
        child.body.append(element);
      }
    });

  try {
    const [entry, blank, srcdoc] = await Promise.all([
      observeWorkerContext('entry'),
      childResult('blank'),
      childResult('srcdoc'),
    ]);
    const registrations = await navigator.serviceWorker.getRegistrations();
    window.workerContextsResult = {
      documents: { entry, blank, srcdoc },
      scopes: registrations.map(({ scope }) => scope).sort(),
    };
  } catch (error) {
    window.workerContextsResult = { error: String(error) };
  }
})();
