import { startWrapper } from './portal-wrapper';

try {
  await startWrapper();
} catch (error) {
  const status = document.querySelector('#status');
  if (status !== null) {
    status.textContent = 'Portal startup rejected by host';
  }
  throw error;
}
