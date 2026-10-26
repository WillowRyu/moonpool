import { describe, expect, it } from 'vitest';
import { browserPolicy } from '../src/browser-policy';

describe('host-served browser CSP (§8.1.1)', () => {
  it.each(['/', '/index.html', '/containment-check.html'])(
    'root %s permits host wrappers only',
    (path) => {
      expect(browserPolicy(path)).toBe(
        "frame-src http://localhost:5173; object-src 'none'; base-uri 'none'",
      );
    },
  );
  it.each([
    ['com.example.hello', 'http://localhost:5174'],
    ['com.example.second', 'http://localhost:5175'],
  ])('pins wrapper policy for %s', (app, origin) => {
    expect(browserPolicy(`/portal-wrapper.html?app=${app}&instance=1`)).toBe(
      `frame-src ${origin}; object-src 'none'; base-uri 'none'`,
    );
  });
  it.each([
    '/portal-wrapper.html',
    '/portal-wrapper.html?app=unknown',
    '/portal-wrapper.html?app=https://evil.example',
  ])('fails closed for %s', (path) => {
    expect(browserPolicy(path)).toBe("frame-src 'none'; object-src 'none'; base-uri 'none'");
  });
  it('does not inject a guest allowlist or derive policy from a caller origin parameter', () => {
    expect(
      browserPolicy('/portal-wrapper.html?app=com.example.hello&origin=http://localhost:5175'),
    ).not.toContain('5175');
    expect(browserPolicy('/src/main.ts')).toBeUndefined();
  });
});
