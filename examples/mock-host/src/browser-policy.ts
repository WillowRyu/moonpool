import { HOST_ORIGIN, MINI_APP_ORIGINS } from './development-origins';

/** HTTP response policy, selected by the trusted server rather than guest claims. */
export function browserPolicy(requestUrl: string): string | undefined {
  const url = new URL(requestUrl, HOST_ORIGIN);
  let origin: string;
  if (url.pathname === '/portal-wrapper.html') {
    origin = MINI_APP_ORIGINS.get(url.searchParams.get('app') ?? '') ?? "'none'";
  } else if (['/', '/index.html', '/containment-check.html'].includes(url.pathname)) {
    origin = HOST_ORIGIN;
  } else {
    return;
  }
  return `frame-src ${origin}; object-src 'none'; base-uri 'none'`;
}
