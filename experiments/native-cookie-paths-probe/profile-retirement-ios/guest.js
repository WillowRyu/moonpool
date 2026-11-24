(async () => {
  const { name, marker } = window.retirementConfig;
  const instance = Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
  window.retirementFixture = {
    name,
    origin: window.origin,
    instance,
    pulse: 0,
    cookie: document.cookie,
    marker: await window.workerAdmissionData(marker),
  };
})();
