(async () => {
  const { run, scope } = window.workerProbe;
  try {
    const data = await window.workerAdmissionData(run);
    if (scope) {
      await navigator.serviceWorker.register(`${scope}worker.js`, { scope });
      const registration = await navigator.serviceWorker.ready;
      window.workerSeed = {
        origin: window.origin,
        data,
        scope: registration.scope,
      };
    } else {
      window.workerSeed = { origin: window.origin, data, scope: null };
    }
  } catch (error) {
    window.workerSeed = { error: String(error) };
  }
})();
