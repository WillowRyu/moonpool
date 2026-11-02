import { readFileSync } from 'node:fs';
import { createContext, runInContext } from 'node:vm';
import { describe, expect, it } from 'vitest';

const bundle = () => readFileSync(new URL('./build/kernel-probe.js', import.meta.url), 'utf8');
const scheduler = () => readFileSync(new URL('./timer-adapter.js', import.meta.url), 'utf8');

describe('trusted runtime common-kernel contract', () => {
  it('runs the real kernel without DOM globals and reports its observable outcomes', async () => {
    const context = createContext({ setTimeout, clearTimeout });
    runInContext(scheduler(), context);
    runInContext(bundle(), context);
    expect(runInContext('typeof __t27.start', context)).toBe('function');
    runInContext(
      `__t27.start(JSON.stringify({appId:'com.example.runtime.a',platform:'ios',initialValue:null,writeValue:'A'}))`,
      context,
    );
    const deadline = Date.now() + 2000;
    let report = { complete: false, checks: [], globals: { window: false } };
    while (Date.now() < deadline) {
      runInContext('__t27Scheduler.tick()', context);
      report = JSON.parse(runInContext('__t27.report()', context));
      if (report.complete) {
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 5));
    }
    expect(report.complete).toBe(true);
    expect(report.error).toBeUndefined();
    expect(report.checks.every((check) => check.passed)).toBe(true);
    expect(report.storedValue).toBe('A');
    expect(report.globals.window).toBe(false);
    runInContext('__t27.close()', context);
    expect(JSON.parse(runInContext('__t27.report()', context)).closed).toBe(true);
    expect(runInContext('__t27.start("{}")', context)).toBe(false);
  });

  it('keeps the kernel control global out of a separate guest context', () => {
    const host = createContext({ setTimeout, clearTimeout });
    const guest = createContext({});
    runInContext(bundle(), host);
    expect(runInContext('typeof __t27', host)).toBe('object');
    expect(runInContext('typeof __t27', guest)).toBe('undefined');
  });
});
