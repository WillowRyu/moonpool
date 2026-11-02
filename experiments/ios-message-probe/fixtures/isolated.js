// Native-injected named-world marker only; no trusted kernel or capability.
window.__t26WorldValue = 'isolated-public-marker';
window.__t26IsolatedReplies = [];
window.webkit.messageHandlers.t26Isolated
  .postMessage({
    kind: 'world-start',
    doc: new URLSearchParams(location.search).get('doc'),
    claimedOrigin: 'moonpool://forged.invalid',
    claimedMainFrame: true,
  })
  .then(
    (value) => window.__t26IsolatedReplies.push(value),
    (error) => window.__t26IsolatedReplies.push({ rejected: String(error.message) }),
  );
addEventListener('DOMContentLoaded', () => {
  document.documentElement.dataset.t26World = 'shared-dom-marker';
});
