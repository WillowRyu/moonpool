// Probe-only private-runtime scheduler. Native owners drive tick on their
// serialized executor. This is not a production polling/timer policy.
(() => {
  const timers = new Map();
  const hostErrors = [];
  let next = 0;
  globalThis.setTimeout = (callback, milliseconds) => {
    const id = ++next;
    timers.set(id, { callback, deadline: Date.now() + milliseconds });
    return id;
  };
  globalThis.clearTimeout = (id) => {
    timers.delete(id);
  };
  globalThis.queueMicrotask = (callback) => {
    void Promise.resolve()
      .then(callback)
      .catch((error) => {
        hostErrors.push(error);
      });
  };
  globalThis.__t27Scheduler = {
    tick() {
      const now = Date.now();
      for (const [id, timer] of [...timers]) {
        if (timer.deadline <= now) {
          timers.delete(id);
          try {
            timer.callback();
          } catch (error) {
            hostErrors.push(error);
          }
        }
      }
    },
    snapshot() {
      return { pendingTimers: timers.size, hostDiagnosticCount: hostErrors.length };
    },
    clear() {
      timers.clear();
    },
  };
})();
