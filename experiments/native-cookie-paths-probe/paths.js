(() => {
  const { run, base, origin, view: initialView, frame } = window.c09Config;
  const cookie = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie');
  const read = (operation) => {
    try {
      return operation();
    } catch (error) {
      return String(error.name);
    }
  };
  const snapshot = () => ({
    direct: read(() => document.cookie),
    prototype: cookie ? read(() => cookie.get.call(document)) : 'unsupported',
  });
  const first = snapshot();
  read(() => {
    // biome-ignore lint/suspicious/noDocumentCookie: Exercise the actual browser cookie setter.
    document.cookie = 'c09_js=1; Path=/; Secure';
    cookie?.set.call(document, 'c09_prototype=1; Path=/; Secure');
  });
  const afterWrite = snapshot();
  if (frame) {
    window.c09Frame = afterWrite;
    return;
  }

  let view = initialView;
  if (view === 'initial') {
    const seen = sessionStorage.getItem('c09-run');
    sessionStorage.setItem('c09-run', run);
    if (seen === run) {
      view = 'reload';
    }
  }
  const query = new URLSearchParams({ run, view });
  const target = (surface) => `${base}/denied?${query}&surface=${surface}`;
  const violations = new Set();
  document.addEventListener('securitypolicyviolation', (event) => {
    violations.add(event.effectiveDirective);
  });
  const wait = (start) =>
    new Promise((resolve) => {
      const deadline = setTimeout(() => resolve('timeout'), 2500);
      const complete = (value) => {
        clearTimeout(deadline);
        resolve(value);
      };
      try {
        start(complete);
      } catch (error) {
        complete(error.name);
      }
    });
  const image = (url) =>
    wait((done) => {
      const img = new Image();
      img.onload = () => done('loaded');
      img.onerror = () => done('rejected');
      img.src = url;
    });
  const storage = async () => {
    const previousLocal = localStorage.getItem('c09');
    localStorage.setItem('c09', run);
    const database = await new Promise((resolve, reject) => {
      const open = indexedDB.open('public-c09', 1);
      open.onupgradeneeded = () => open.result.createObjectStore('values');
      open.onsuccess = () => resolve(open.result);
      open.onerror = () => reject(open.error);
    });
    const previousIndexed = await new Promise((resolve, reject) => {
      const transaction = database.transaction('values', 'readwrite');
      const values = transaction.objectStore('values');
      const entry = values.get('c09');
      entry.onsuccess = () => values.put(run, 'c09');
      transaction.oncomplete = () => resolve(entry.result ?? null);
      transaction.onabort = () => reject(transaction.error);
    });
    database.close();
    return { previousLocal, previousIndexed, local: localStorage.getItem('c09'), indexed: run };
  };

  const main = async () => {
    const attempts = {};
    const iframe = document.createElement('iframe');
    iframe.hidden = true;
    const frameResult = wait((done) => {
      iframe.onload = () => done(read(() => iframe.contentWindow.c09Frame));
      iframe.src = `${origin}/frame?${query}`;
      document.body.append(iframe);
    });
    const foreign = document.createElement('iframe');
    foreign.hidden = true;
    foreign.name = 'c09-form-target';
    foreign.src = target('frame');
    document.body.append(foreign);
    attempts.frame = 'attempted';
    const form = document.createElement('form');
    form.action = target('form');
    form.method = 'POST';
    form.target = foreign.name;
    document.body.append(form);
    attempts.form = read(() => {
      form.submit();
      return 'attempted';
    });
    attempts.beacon = navigator.sendBeacon
      ? read(() => (navigator.sendBeacon(target('beacon'), 'public') ? 'queued' : 'refused'))
      : 'unsupported';
    attempts.popup = read(() => (window.open(target('popup')) ? 'opened' : 'blocked'));

    const checks = {
      fetch: wait((done) =>
        fetch(target('fetch'), { credentials: 'include' }).then(
          () => done('resolved'),
          () => done('rejected'),
        ),
      ),
      xhr: wait((done) => {
        const xhr = new XMLHttpRequest();
        xhr.open('GET', target('xhr'));
        xhr.withCredentials = true;
        xhr.onload = () => done('resolved');
        xhr.onerror = () => done('rejected');
        xhr.send();
      }),
      socket: !window.WebSocket
        ? 'unsupported'
        : wait((done) => {
            const socket = new WebSocket(target('socket').replace(/^https:/, 'wss:'));
            socket.onopen = () => {
              socket.close();
              done('opened');
            };
            socket.onerror = () => {
              socket.close();
              done('rejected');
            };
          }),
      events: !window.EventSource
        ? 'unsupported'
        : wait((done) => {
            const stream = new EventSource(target('events'), { withCredentials: true });
            stream.onopen = () => {
              stream.close();
              done('opened');
            };
            stream.onerror = () => {
              stream.close();
              done('rejected');
            };
          }),
      worker: !window.Worker
        ? 'unsupported'
        : wait((done) => {
            const worker = new Worker(`${origin}/worker.js?${query}`);
            worker.onmessage = () => {
              worker.terminate();
              done('executed');
            };
            worker.onerror = () => {
              worker.terminate();
              done('rejected');
            };
          }),
      'redirect-other': image(`${base}/static/redirect-other?${query}`),
      'redirect-same': image(`${base}/static/redirect-same?${query}`),
    };
    const resources = {
      local: await image(`${origin}/local.gif?${query}`),
      seed: await image(`${base}/static/seed.gif?${query}`),
      echo: await image(`${base}/static/echo.gif?${query}`),
    };
    const stored = await storage();
    for (const [name, result] of Object.entries(checks)) {
      attempts[name] = await result;
    }
    window.c09Result = {
      view,
      origin: location.protocol + '//' + location.host,
      first,
      afterWrite,
      last: snapshot(),
      frame: (await frameResult) ?? null,
      storage: stored,
      resources,
      attempts,
      violations: [...violations].sort(),
      serviceWorker: navigator.serviceWorker ? 'exposed' : 'unsupported',
    };
  };
  window.addEventListener(
    'DOMContentLoaded',
    () => {
      main().catch((error) => {
        window.c09Result = { view, error: String(error) };
      });
    },
    { once: true },
  );
})();
