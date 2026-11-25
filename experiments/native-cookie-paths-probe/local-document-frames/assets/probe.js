const NAVIGATION_TIMEOUT_MS = 6500;
const OBSERVATION_WINDOW_MS = 6500;

async function frameDocument(name) {
  const origin = window.origin;
  const protocol = window.location.protocol;
  const ready = { type: 'ready', name, origin, protocol };
  if (['blank', 'srcdoc', 'blank-navigation'].includes(name)) {
    Object.assign(ready, {
      url: window.location.href,
      secureContext: window.isSecureContext,
      serviceWorkerRegistration: typeof navigator.serviceWorker?.register === 'function',
    });
  }
  parent.postMessage(ready, '*');
  if (name === 'data') {
    return;
  }

  const script = new URL('/worker.js', origin).href;
  document.addEventListener('securitypolicyviolation', (event) => {
    if (event.effectiveDirective === 'worker-src') {
      parent.postMessage(
        {
          type: 'worker-violation',
          name,
          violation: {
            directive: event.effectiveDirective,
            disposition: event.disposition,
            blockedURI: event.blockedURI,
            trusted: event.isTrusted,
          },
        },
        '*',
      );
    }
  });
  const outcome = await new Promise((resolve) => {
    let worker;
    try {
      worker = new Worker(script);
    } catch {
      resolve('rejected');
      return;
    }
    function finish(result) {
      clearTimeout(deadline);
      worker.terminate();
      resolve(result);
    }
    const deadline = setTimeout(() => finish('timeout'), 4500);
    worker.addEventListener('message', (message) =>
      finish(message.data === 'local-frame-worker' ? 'message' : 'unexpected-message'),
    );
    worker.addEventListener('error', () => finish('rejected'));
  });
  parent.postMessage({ type: 'worker-result', name, outcome }, '*');
}

function insertFrameScript(child, source) {
  const script = child.createElement('script');
  script.textContent = source;
  child.body.append(script);
}

async function attachAndNavigateToBlank(frame, previousUrl, state) {
  const navigation = { previousUrl: null, replacementUrl: null, documentReplaced: false };
  state.navigation = navigation;
  let previousDocument;
  let finish;
  const replacement = new Promise((resolve) => {
    finish = resolve;
  });

  function observeNavigation() {
    const child = frame.contentDocument;
    if (!previousDocument) {
      if (child?.URL !== previousUrl || !child.getElementById('before-blank')) {
        return;
      }
      previousDocument = child;
      navigation.previousUrl = child.URL;
      state.trace.push('previous-document', 'blank-navigation');
      frame.src = 'about:blank';
      return;
    }
    if (
      child?.URL !== 'about:blank' ||
      child === previousDocument ||
      !child.body ||
      navigation.documentReplaced
    ) {
      return;
    }
    navigation.replacementUrl = child.URL;
    navigation.documentReplaced = true;
    state.trace.push('replacement-document');
    finish(child);
  }

  const deadline = setTimeout(() => finish(null), NAVIGATION_TIMEOUT_MS);
  frame.addEventListener('load', observeNavigation);
  try {
    document.body.append(frame);
    return await replacement;
  } finally {
    clearTimeout(deadline);
    frame.removeEventListener('load', observeNavigation);
  }
}

(async () => {
  if (window !== window.parent) {
    await frameDocument('same');
    return;
  }

  try {
    const kind = window.location.pathname.slice('/entry/'.length);
    const childScript = `(${frameDocument.toString()})(${JSON.stringify(kind)});`;
    const html = `<!doctype html><meta charset=utf-8><script>${childScript}</script>`;
    const previousUrl = `${window.origin}/before-blank`;
    const url = {
      same: () => `${window.origin}/same-frame`,
      blob: () => URL.createObjectURL(new Blob([html], { type: 'text/html' })),
      data: () => `data:text/html;charset=utf-8,${encodeURIComponent(html)}`,
      'blank-navigation': () => previousUrl,
    }[kind]?.();
    const frame = document.createElement('iframe');
    const state = {
      parentUrl: window.location.href,
      trace: [],
      starts: [],
      workers: [],
      workerViolations: [],
      frameViolations: [],
    };

    function read(event) {
      const data = event.data;
      if (event.source !== frame.contentWindow || data?.name !== kind) {
        return;
      }
      if (data.type === 'ready') {
        const start = {
          name: data.name,
          origin: data.origin,
          protocol: data.protocol,
          messageOrigin: event.origin,
        };
        if (['blank', 'srcdoc', 'blank-navigation'].includes(kind)) {
          Object.assign(start, {
            url: data.url,
            secureContext: data.secureContext,
            serviceWorkerRegistration: data.serviceWorkerRegistration,
          });
        }
        state.starts.push(start);
        state.trace.push('ready');
      }
      if (data.type === 'worker-result') {
        state.workers.push({
          outcome: data.outcome,
          messageOrigin: event.origin,
        });
        state.trace.push('worker-result');
      }
      if (data.type === 'worker-violation') {
        state.workerViolations.push({ ...data.violation, messageOrigin: event.origin });
        state.trace.push('worker-violation');
      }
    }

    function recordViolation(event) {
      if (event.effectiveDirective === 'frame-src') {
        const scheme = event.blockedURI ? event.blockedURI.split(':', 1)[0] : null;
        state.frameViolations.push({
          directive: event.effectiveDirective,
          disposition: event.disposition,
          scheme,
          trusted: event.isTrusted,
        });
        state.trace.push('frame-violation');
      }
    }

    window.addEventListener('message', read);
    document.addEventListener('securitypolicyviolation', recordViolation);
    if (kind === 'srcdoc') {
      frame.srcdoc = html;
    } else if (url !== undefined) {
      frame.src = url;
    }
    state.trace.push('attach');
    try {
      let shouldObserve = true;
      if (kind === 'blank-navigation') {
        const child = await attachAndNavigateToBlank(frame, previousUrl, state);
        shouldObserve = child !== null;
        if (child) {
          insertFrameScript(child, childScript);
        }
      } else {
        document.body.append(frame);
        if (kind === 'blank') {
          const child = frame.contentDocument;
          if (child?.URL !== 'about:blank' || !child.body) {
            throw new Error('Initial blank document is missing');
          }
          insertFrameScript(child, childScript);
        }
      }
      if (shouldObserve) {
        await new Promise((resolve) => setTimeout(resolve, OBSERVATION_WINDOW_MS));
      }
    } finally {
      window.removeEventListener('message', read);
      document.removeEventListener('securitypolicyviolation', recordViolation);
      frame.remove();
      state.trace.push('detach');
      if (kind === 'blob') {
        URL.revokeObjectURL(url);
      }
    }
    window.localFramesResult = state;
  } catch (error) {
    window.localFramesResult = { error: String(error) };
  }
})();
