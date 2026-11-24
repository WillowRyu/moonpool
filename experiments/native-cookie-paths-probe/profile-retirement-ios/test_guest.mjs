import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { Script } from 'node:vm';

test('the same fixture script identifies each document execution independently', async () => {
  const source = readFileSync(new URL('./guest.js', import.meta.url), 'utf8');
  const script = new Script(source);
  const runDocument = async () => {
    const window = {
      origin: 'moonpool://com.example.retirement.test.b',
      retirementConfig: { name: 'b1' },
      workerAdmissionData: async () => 'test-b',
    };
    await script.runInNewContext({ window, document: { cookie: '' }, crypto: webcrypto });
    return window.retirementFixture;
  };

  const first = await runDocument();
  const second = await runDocument();
  assert.equal(first.marker, second.marker);
  assert.ok(first.instance);
  assert.ok(second.instance);
  assert.notEqual(first.instance, second.instance);
});
