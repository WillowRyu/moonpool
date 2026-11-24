(async () => {
  const waitForActivation = async (registration) => {
    const worker = registration.installing ?? registration.waiting ?? registration.active;
    if (!worker) {
      throw new Error('The registration has no worker');
    }
    await new Promise((resolve, reject) => {
      const deadline = setTimeout(() => {
        worker.removeEventListener('statechange', changed);
        reject(new Error('The worker did not activate'));
      }, 5000);
      function changed() {
        if (worker.state !== 'activated') {
          return;
        }
        clearTimeout(deadline);
        worker.removeEventListener('statechange', changed);
        resolve();
      }
      worker.addEventListener('statechange', changed);
      changed();
    });
  };

  const attempt = async (scope) => {
    const origin = window.origin;
    const workerURL = new URL(`${scope}worker.js`, origin).href;
    let receive;
    const violated = new Promise((resolve) => {
      receive = (event) =>
        resolve({
          directive: event.effectiveDirective,
          disposition: event.disposition,
          blockedURI: event.blockedURI,
        });
      document.addEventListener('securitypolicyviolation', receive);
    });
    let deadline;
    try {
      let registration;
      try {
        registration = await navigator.serviceWorker.register(workerURL, { scope });
      } catch (error) {
        const violation = await Promise.race([
          violated,
          new Promise((resolve) => {
            deadline = setTimeout(() => resolve(null), 1000);
          }),
        ]);
        return { origin, outcome: 'rejected', error: error.name, violation };
      }
      await waitForActivation(registration);
      return { origin, outcome: 'activated', scope: registration.scope };
    } finally {
      clearTimeout(deadline);
      document.removeEventListener('securitypolicyviolation', receive);
    }
  };

  const childAttempt = () =>
    new Promise((resolve, reject) => {
      const child = document.createElement('iframe');
      child.src = '/child/frame';
      const deadline = setTimeout(() => {
        window.removeEventListener('message', receive);
        reject(new Error('The same-origin frame did not report'));
      }, 7000);
      function receive(event) {
        if (event.source !== child.contentWindow || event.origin !== window.origin) {
          return;
        }
        clearTimeout(deadline);
        window.removeEventListener('message', receive);
        resolve(event.data);
      }
      window.addEventListener('message', receive);
      document.body.append(child);
    });

  try {
    if (window.parent !== window) {
      window.parent.postMessage(await attempt('/child/'), window.origin);
      return;
    }
    const [main, frame] = await Promise.all([attempt('/'), childAttempt()]);
    const registrations = await navigator.serviceWorker.getRegistrations();
    window.workerPreventionResult = {
      origin: window.origin,
      entryScript: true,
      marker: await window.workerAdmissionData(window.workerPreventionWrite),
      attempts: { main, frame },
      scopes: registrations.map(({ scope }) => scope).sort(),
      controller: navigator.serviceWorker.controller?.scriptURL ?? null,
    };
  } catch (error) {
    window.workerPreventionResult = { error: String(error) };
  }
})();
