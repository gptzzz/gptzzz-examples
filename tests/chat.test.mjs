import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { configuration, chat } from '../scripts/chat.mjs';

const env = { GPTZZZ_API_KEY: 'local-test-key', GPTZZZ_MODEL: 'test-model' };
async function stub(t, handler) {
  const server = http.createServer(handler);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  return configuration({ ...env, GPTZZZ_BASE_URL: `http://127.0.0.1:${server.address().port}/v1` });
}

test('requires a model and protects the credential destination', () => {
  assert.throws(() => configuration({ GPTZZZ_API_KEY: 'local-test-key' }), /GPTZZZ_MODEL/);
  for (const base of ['http://example.com/v1', 'https://u:p@example.com/v1', 'https://example.com/v1?key=test', 'https://example.com/v1#x', 'https://example.com/v1?', 'https://example.com/v1#', 'https://example.com/v1/%63hat/completions', 'https://example.com/v1/chat/completions']) {
    assert.throws(() => configuration({ ...env, GPTZZZ_BASE_URL: base }));
  }
});
test('sends the documented request and reads Chinese text', async t => {
  let request;
  const config = await stub(t, (req, res) => {
    let body = ''; req.on('data', part => { body += part; });
    req.on('end', () => {
      request = { path: req.url, method: req.method, auth: req.headers.authorization, body: JSON.parse(body) };
      res.setHeader('Content-Type', 'application/json');
      res.end(JSON.stringify({ choices: [{ message: { content: '本地模拟回答' } }] }));
    });
  });
  assert.equal(await chat(config, '本地测试'), '本地模拟回答');
  assert.deepEqual(request, { path: '/v1/chat/completions', method: 'POST', auth: 'Bearer local-test-key', body: { model: 'test-model', messages: [{ role: 'user', content: '本地测试' }], stream: false } });
});
test('does not follow a redirect or leak error response bodies', async t => {
  let calls = 0;
  const config = await stub(t, (req, res) => { calls++; res.writeHead(302, { Location: '/leak' }); res.end('local-test-key private body'); });
  await assert.rejects(chat(config, '测试'), error => /HTTP 302/.test(error.message) && !/local-test-key|private body/.test(error.message));
  assert.equal(calls, 1);
});
test('rejects malformed JSON and empty responses', async t => {
  for (const body of ['invalid', '{"choices":[]}', '{"choices":[{"message":{"content":""}}]}']) {
    const config = await stub(t, (req, res) => res.end(body));
    await assert.rejects(chat(config, '测试'));
  }
});
test('times out without retrying', async t => {
  let calls = 0;
  const config = await stub(t, () => { calls++; });
  await assert.rejects(chat(config, '测试', 0.1), /请求超时/);
  assert.equal(calls, 1);
});
