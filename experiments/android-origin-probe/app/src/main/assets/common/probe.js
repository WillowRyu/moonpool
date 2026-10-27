// Public diagnostic results only. These page values never grant native authority.
const params = new URLSearchParams(location.search);
const profile = params.get('profile');
const app = document.body.dataset.app;
const key = `t23-${profile}`;
const other = app === 'a' ? 'b' : 'a';
const otherHost = location.hostname.replace(`.probe.${app}`, `.probe.${other}`);

function local(seed) {
  try {
    const before = localStorage.getItem(key);
    if (seed) {
      localStorage.setItem(key, app);
    }
    return { before, after: localStorage.getItem(key) };
  } catch (error) {
    return { error: `${error.name}: ${error.message}` };
  }
}

function indexed(seed) {
  return new Promise((resolve) => {
    let request;
    try {
      request = indexedDB.open(key, 1);
    } catch (error) {
      resolve({ error: `${error.name}: ${error.message}` });
      return;
    }
    request.onupgradeneeded = () => request.result.createObjectStore('markers');
    request.onerror = () => resolve({ error: String(request.error) });
    request.onsuccess = () => {
      const database = request.result;
      const transaction = database.transaction('markers', 'readwrite');
      const store = transaction.objectStore('markers');
      let before = null;
      store.get('marker').onsuccess = (event) => {
        before = event.target.result ?? null;
        if (seed) {
          store.put(app, 'marker');
        }
      };
      transaction.oncomplete = () => {
        database.close();
        resolve({ before, after: seed ? app : before });
      };
      transaction.onerror = () => {
        database.close();
        resolve({ error: String(transaction.error) });
      };
    };
  });
}

function cookies(seed) {
  try {
    const before = document.cookie;
    if (seed) {
      // biome-ignore lint/suspicious/noDocumentCookie: This probe measures the document.cookie facility itself.
      document.cookie = `${key}=${app}; SameSite=Lax; Path=/`;
    }
    return { before, after: document.cookie };
  } catch (error) {
    return { error: `${error.name}: ${error.message}` };
  }
}

async function fetchResult(url) {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(2500), cache: 'no-store' });
    return { status: response.status, type: response.type, body: await response.text() };
  } catch (error) {
    return { error: `${error.name}: ${error.message}` };
  }
}

function frameResult(url) {
  return new Promise((resolve) => {
    const frame = document.createElement('iframe');
    let finished = false;
    const finish = (event) => {
      if (finished || (event && event.source !== frame.contentWindow)) {
        return;
      }
      finished = true;
      const result = {
        loadedMarker: event?.data?.marker ?? null,
        messageOrigin: event?.origin ?? null,
      };
      try {
        result.domMarker = frame.contentWindow.document.body.dataset.app;
      } catch (error) {
        result.domError = `${error.name}: ${error.message}`;
      }
      removeEventListener('message', finish);
      frame.remove();
      resolve(result);
    };
    addEventListener('message', finish);
    setTimeout(() => finish(null), 2000);
    frame.src = url;
    document.body.append(frame);
  });
}

window.t23Collect = async (seed) => {
  const image = document.querySelector('img');
  if (!image.complete) {
    await new Promise((resolve) => {
      image.addEventListener('load', resolve, { once: true });
      image.addEventListener('error', resolve, { once: true });
      setTimeout(resolve, 2000);
    });
  }
  const cross = `${location.protocol}//${otherHost}/assets/`;
  const observation = {
    app,
    href: location.href,
    origin: location.origin,
    secureContext: isSecureContext,
    cssMarker: getComputedStyle(document.body).backgroundColor,
    imageLoaded: image.complete && image.naturalWidth > 0,
    localStorage: local(seed),
    indexedDB: await indexed(seed),
    cookies: cookies(seed),
  };
  const values = await Promise.all([
    fetchResult('data.json'),
    fetchResult(`${cross}data.json`),
    fetchResult('missing.json'),
    fetchResult('../outside.json'),
    fetchResult('%2e%2e/outside.json'),
    fetchResult(`${location.protocol}//com.example.probe.unknown.test/assets/data.json`),
    fetchResult('http://127.0.0.1:8877/cors'),
    fetchResult('http://127.0.0.1:8877/no-cors'),
    frameResult('frame.html'),
    frameResult(`${cross}frame.html`),
  ]);
  [
    observation.selfFetch,
    observation.crossFetch,
    observation.missingFetch,
    observation.escapeFetch,
    observation.encodedEscapeFetch,
    observation.unknownAppFetch,
    observation.corsFetch,
    observation.noCorsFetch,
    observation.selfFrame,
    observation.crossFrame,
  ] = values;
  document.querySelector('pre').textContent = JSON.stringify(observation, null, 2);
  window.t23Report = observation;
};

void window.t23Collect(params.get('seed') === 'true');
