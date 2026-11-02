(async () => {
  const documentToken = `${Date.now()}-${Math.random()}`;
  const params = new URLSearchParams(location.search);
  const marker = `${location.hostname}:${params.get('run')}`;
  const key = 't28-local';
  document.querySelector('#marker').textContent = location.hostname;
  const readDB = () =>
    new Promise((resolve, reject) => {
      const request = indexedDB.open('t28-contract', 1);
      request.onupgradeneeded = () => request.result.createObjectStore('markers');
      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const db = request.result;
        const transaction = db.transaction(
          'markers',
          params.get('seed') === 'true' ? 'readwrite' : 'readonly',
        );
        const store = transaction.objectStore('markers');
        if (params.get('seed') === 'true') {
          store.put(marker, key);
        }
        const get = store.get(key);
        let value = null;
        get.onsuccess = () => {
          value = get.result ?? null;
        };
        transaction.oncomplete = () => {
          db.close();
          resolve(value);
        };
        transaction.onerror = () => {
          db.close();
          reject(transaction.error);
        };
      };
    });
  const frame = async (host) => {
    const child = document.createElement('iframe');
    const loaded = new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('No loaded frame control')), 5000);
      addEventListener('message', function ready(event) {
        if (event.source !== child.contentWindow || event.data?.kind !== 't28-frame') {
          return;
        }
        removeEventListener('message', ready);
        clearTimeout(timer);
        resolve({ ...event.data, eventOrigin: event.origin });
      });
    });
    child.src = `moonpool://${host}/frame.html`;
    document.body.append(child);
    const result = { loaded: await loaded };
    try {
      result.dom = child.contentDocument.querySelector('#marker').textContent;
    } catch (error) {
      result.domError = error.name;
    }
    try {
      result.storage = child.contentWindow.localStorage.getItem(key);
    } catch (error) {
      result.storageError = error.name;
    }
    child.remove();
    return result;
  };
  try {
    const before = localStorage.getItem(key);
    if (params.get('seed') === 'true') {
      localStorage.setItem(key, marker);
    }
    // biome-ignore lint/suspicious/noDocumentCookie: The research control measures custom-scheme document.cookie availability.
    document.cookie = `t28_custom=${marker}; Max-Age=3600; Path=/`;
    const other =
      location.hostname === 'com.example.probe.a' ? 'com.example.probe.b' : 'com.example.probe.a';
    window.t28Report = {
      documentToken,
      href: location.href,
      origin: location.origin,
      host: location.hostname,
      localBefore: before,
      local: localStorage.getItem(key),
      idb: await readDB(),
      customCookie: document.cookie,
      self: await frame(location.hostname),
      cross: await frame(other),
    };
  } catch (error) {
    window.t28Report = { documentToken, error: `${error.name}: ${error.message}` };
  }
  window.webkit.messageHandlers.observe.postMessage({ kind: 'local', report: window.t28Report });
})();
