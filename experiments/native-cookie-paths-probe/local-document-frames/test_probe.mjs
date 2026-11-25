import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { runInNewContext } from 'node:vm';

const script = readFileSync(new URL('./assets/probe.js', import.meta.url), 'utf8');
const origin = 'https://local-frames.invalid';

function eventTarget() {
  const listeners = new Map();
  return {
    addEventListener(type, listener) {
      listeners.set(type, listener);
    },
    removeEventListener(type) {
      listeners.delete(type);
    },
    dispatch(type, event) {
      listeners.get(type)?.(event);
    },
  };
}

test('a worker violation arriving after the worker result is retained by the parent', async () => {
  const timers = [];
  function schedule(callback, delay) {
    timers.push({ callback, delay });
  }

  const parent = {
    ...eventTarget(),
    origin,
    location: { pathname: '/entry/same', href: `${origin}/entry/same` },
  };
  parent.parent = parent;
  const child = { origin, location: { protocol: 'https:' }, parent };
  const frame = { contentWindow: child, remove() {} };
  const childDocument = eventTarget();
  const messages = [];
  const parentDone = runInNewContext(script, {
    window: parent,
    document: { ...eventTarget(), createElement: () => frame, body: { append() {} } },
    setTimeout: schedule,
  });
  const childDone = runInNewContext(script, {
    window: child,
    document: childDocument,
    parent: {
      postMessage(data) {
        messages.push(data.type);
        parent.dispatch('message', { source: child, origin, data: structuredClone(data) });
      },
    },
    URL,
    Worker: class {
      constructor() {
        throw new Error('Fixture worker was refused');
      }
    },
    setTimeout: schedule,
  });

  const delay = 350;
  await Promise.resolve();
  for (const timer of timers.filter((timer) => timer.delay <= delay)) {
    timer.callback();
  }
  await childDone;
  assert.deepEqual(messages, ['ready', 'worker-result']);
  childDocument.dispatch('securitypolicyviolation', {
    effectiveDirective: 'worker-src',
    disposition: 'enforce',
    blockedURI: `${origin}/worker.js`,
    isTrusted: true,
  });

  timers.find((timer) => timer.delay === 6500).callback();
  await parentDone;
  const page = structuredClone(parent.localFramesResult);
  assert.deepEqual(page.workerViolations, [
    {
      directive: 'worker-src',
      disposition: 'enforce',
      blockedURI: `${origin}/worker.js`,
      trusted: true,
      messageOrigin: origin,
    },
  ]);
  assert.deepEqual(page.workers, [{ outcome: 'rejected', messageOrigin: origin }]);
  assert.deepEqual(page.trace, ['attach', 'ready', 'worker-result', 'worker-violation', 'detach']);
});

for (const kind of ['blank', 'srcdoc']) {
  test(`${kind} uses its own inherited document without assigning src`, async () => {
    const window = {
      ...eventTarget(),
      origin,
      location: { pathname: `/entry/${kind}`, href: `${origin}/entry/${kind}` },
    };
    window.parent = window;
    let attached = false;
    let finish;
    const scripts = [];
    const frame = {
      remove() {},
      contentDocument: {
        URL: 'about:blank',
        createElement(tag) {
          assert.equal(tag, 'script');
          return {};
        },
        body: {
          append(element) {
            assert.equal(attached, true);
            scripts.push(element.textContent);
          },
        },
      },
    };
    const done = runInNewContext(script, {
      window,
      document: {
        ...eventTarget(),
        createElement: () => frame,
        body: {
          append(child) {
            assert.equal(child, frame);
            attached = true;
          },
        },
      },
      setTimeout(callback) {
        finish = callback;
      },
    });
    assert.equal(attached, true);
    assert.equal(frame.src, undefined);
    if (kind === 'blank') {
      assert.equal(frame.srcdoc, undefined);
      assert.equal(scripts.length, 1);
      assert.match(scripts[0], /\("blank"\);$/);
    } else {
      assert.equal(scripts.length, 0);
      assert.match(frame.srcdoc, /\("srcdoc"\);<\/script>$/);
    }
    finish();
    await done;
  });
}

function navigationClock() {
  let now = 0;
  const timers = new Map();
  return {
    setTimeout(callback, delay) {
      const token = Symbol();
      timers.set(token, { callback, at: now + delay });
      return token;
    },
    clearTimeout(token) {
      timers.delete(token);
    },
    async advanceTo(time) {
      for (;;) {
        const next = [...timers.entries()].sort((a, b) => a[1].at - b[1].at)[0];
        if (!next || next[1].at > time) {
          break;
        }
        now = next[1].at;
        timers.delete(next[0]);
        next[1].callback();
        await new Promise(setImmediate);
      }
      now = time;
    },
  };
}

function runBlankNavigation(clock) {
  const window = {
    ...eventTarget(),
    origin,
    location: { pathname: '/entry/blank-navigation', href: `${origin}/entry/blank-navigation` },
  };
  window.parent = window;
  const scripts = [];
  const documentBody = { append: (element) => scripts.push(element.textContent) };
  const createElement = () => ({});
  const contentWindow = {
    origin,
    location: { href: 'about:blank', protocol: 'about:' },
    isSecureContext: true,
  };
  const frame = {
    ...eventTarget(),
    remove() {},
    contentWindow,
    contentDocument: { URL: 'about:blank', body: documentBody, createElement },
  };
  const done = runInNewContext(script, {
    window,
    document: { ...eventTarget(), createElement: () => frame, body: { append() {} } },
    ...clock,
  });
  return { window, frame, scripts, documentBody, createElement, done };
}

test('a slow later navigation leaves the full worker window after replacement', async () => {
  const clock = navigationClock();
  const { window, frame, scripts, documentBody, createElement, done } = runBlankNavigation(clock);

  assert.equal(frame.src, `${origin}/before-blank`);
  frame.dispatch('load');
  assert.equal(frame.src, `${origin}/before-blank`);
  assert.deepEqual(scripts, []);

  await clock.advanceTo(2400);
  frame.contentDocument = {
    URL: frame.src,
    getElementById: (id) => (id === 'before-blank' ? {} : null),
    body: documentBody,
    createElement,
  };
  frame.dispatch('load');
  assert.equal(frame.src, 'about:blank');
  frame.contentDocument.URL = 'about:blank';
  frame.dispatch('load');
  assert.deepEqual(scripts, []);

  await clock.advanceTo(2500);
  let childDone;
  frame.contentDocument = {
    URL: 'about:blank',
    createElement,
    body: {
      append(element) {
        documentBody.append(element);
        childDone = runInNewContext(element.textContent, {
          window: frame.contentWindow,
          document: eventTarget(),
          navigator: {},
          parent: {
            postMessage(data) {
              window.dispatch('message', {
                source: frame.contentWindow,
                origin,
                data: structuredClone(data),
              });
            },
          },
          URL,
          Worker: class {
            events = eventTarget();
            constructor(url) {
              assert.equal(url, `${origin}/worker.js`);
              clock.setTimeout(
                () => this.events.dispatch('message', { data: 'local-frame-worker' }),
                4200,
              );
            }
            addEventListener(type, callback) {
              this.events.addEventListener(type, callback);
            }
            terminate() {}
          },
          ...clock,
        });
      },
    },
  };
  frame.dispatch('load');
  frame.dispatch('load');
  await new Promise(setImmediate);
  assert.equal(scripts.length, 1);
  assert.match(scripts[0], /\("blank-navigation"\);$/);
  await clock.advanceTo(6700);
  await childDone;
  await clock.advanceTo(8999);
  assert.equal(window.localFramesResult, undefined);
  await clock.advanceTo(9000);
  await done;
  assert.deepEqual(structuredClone(window.localFramesResult.navigation), {
    previousUrl: `${origin}/before-blank`,
    replacementUrl: 'about:blank',
    documentReplaced: true,
  });
  assert.deepEqual(structuredClone(window.localFramesResult.workers), [
    { outcome: 'message', messageOrigin: origin },
  ]);
});

test('a navigation with no replacement ends at the navigation deadline', async () => {
  const clock = navigationClock();
  const { window, frame, scripts, documentBody, createElement, done } = runBlankNavigation(clock);
  frame.contentDocument = { URL: frame.src, getElementById: () => ({}) };
  frame.dispatch('load');
  assert.equal(frame.src, 'about:blank');

  await clock.advanceTo(6500);
  await done;
  frame.contentDocument = { URL: 'about:blank', body: documentBody, createElement };
  frame.dispatch('load');
  assert.deepEqual(scripts, []);
  assert.equal(window.localFramesResult.navigation.documentReplaced, false);
  assert.deepEqual(structuredClone(window.localFramesResult.trace), [
    'attach',
    'previous-document',
    'blank-navigation',
    'detach',
  ]);
});
