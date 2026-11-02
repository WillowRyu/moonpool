/* Bounded test fixture. Both local app hosts are deliberately resolvable here only
 * to measure browser origin enforcement independently of production containment. */
(async () => {
  const query = new URLSearchParams(location.search);
  const app = query.get('app');
  const seed = query.get('seed') === 'true';
  const tag = query.get('tag');
  document.getElementById('marker').textContent = `loaded-${app}`;
  const database = await new Promise((resolve, reject) => {
    const request = indexedDB.open('t28-public-markers', 1);
    request.onupgradeneeded = () => request.result.createObjectStore('markers');
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(new Error(request.error.name));
  });
  const idb = (mode, value) =>
    new Promise((resolve, reject) => {
      const transaction = database.transaction('markers', mode);
      const store = transaction.objectStore('markers');
      const request = mode === 'readwrite' ? store.put(value, 'owner') : store.get('owner');
      request.onsuccess = () => {
        if (mode === 'readonly') {
          resolve(request.result ?? null);
        }
      };
      transaction.oncomplete = () => {
        if (mode === 'readwrite') {
          resolve(value);
        }
      };
      transaction.onerror = () => reject(new Error(transaction.error.name));
    });
  const before = {
    localStorage: localStorage.getItem('t28-owner'),
    indexedDB: await idb('readonly'),
    cookie: document.cookie,
  };
  if (seed) {
    localStorage.setItem('t28-owner', `${tag}-${app}`);
    await idb('readwrite', `${tag}-${app}`);
    // biome-ignore lint/suspicious/noDocumentCookie: Deliberately measure document.cookie browser enforcement.
    document.cookie = `t28_local=${tag}-${app}; Path=/; Max-Age=86400; Secure; SameSite=Lax`;
    // biome-ignore lint/suspicious/noDocumentCookie: Deliberately measure document.cookie browser enforcement.
    document.cookie = `t28_parent=must-reject; Domain=invalid; Path=/; Max-Age=86400; Secure; SameSite=Lax`;
    // biome-ignore lint/suspicious/noDocumentCookie: Deliberately measure document.cookie browser enforcement.
    document.cookie = `t28_sibling=must-reject; Domain=${query.get('other')}; Path=/; Max-Age=86400; Secure; SameSite=Lax`;
  }
  const frame = (host, name) =>
    new Promise((resolve) => {
      const child = document.createElement('iframe');
      child.src = `https://${host}/frame.html?app=${name}`;
      const ready = (event) => {
        if (
          event.source !== child.contentWindow ||
          event.origin !== `https://${host}` ||
          event.data?.marker !== `loaded-${name}`
        ) {
          return;
        }
        window.removeEventListener('message', ready);
        let access;
        try {
          access = {
            marker: child.contentWindow.document.body.firstChild.textContent,
            localStorage: child.contentWindow.localStorage.getItem('t28-owner'),
          };
        } catch (error) {
          access = { error: error.name };
        }
        resolve({
          url: child.src,
          loaded: true,
          ready: { origin: event.origin, marker: event.data.marker },
          access,
        });
      };
      window.addEventListener('message', ready);
      document.body.append(child);
    });
  const ownFrame = await frame(location.hostname, app);
  const crossFrame = await frame(query.get('other'), app === 'a' ? 'b' : 'a');
  window.t28 = {
    app,
    seed,
    tag,
    documentToken: crypto.randomUUID(),
    href: location.href,
    origin: location.origin,
    secureContext: isSecureContext,
    before,
    after: {
      localStorage: localStorage.getItem('t28-owner'),
      indexedDB: await idb('readonly'),
      cookie: document.cookie,
    },
    ownFrame,
    crossFrame,
  };
  database.close();
})().catch((error) => {
  window.t28 = { error: error.name, message: error.message };
});
