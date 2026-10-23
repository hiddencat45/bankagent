import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { createAgentClient, readAgentStream } from '../agent-client.mjs';

const base = { thread_id: 'conv-test', request_id: 'req-test', mode: 'offline' };
const event = (name, data = {}) => `event: ${name}\ndata: ${JSON.stringify({ ...base, ...data })}\n\n`;
const start = () => event('status', { step: 'started', status: 'PROCESSING' });
const end = status => event('done', { status });
function stream(text, width = 1) {
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream({ start(controller) {
    for (let i = 0; i < bytes.length; i += width) controller.enqueue(bytes.slice(i, i + width));
    controller.close();
  } });
}
const response = text => new Response(stream(text, 11), { headers: { 'Content-Type': 'text/event-stream; charset=utf-8' } });
const collect = async text => {
  const frames = [];
  await readAgentStream(stream(text), frame => frames.push(frame));
  return frames;
};

test('分字节的中文、CRLF、注释心跳、多行 data 能完整读取', async () => {
  const text = ': ping\n\n' + start() + `event: message\ndata: {"thread_id":"conv-test",\ndata: "request_id":"req-test","mode":"offline","text":"账单证据"}\n\n` + end('COMPLETED');
  const frames = await collect(text.replaceAll('\n', '\r\n'));
  assert.equal(frames[1].data.text, '账单证据');
  assert.deepEqual(frames.map(frame => frame.event), ['status', 'message', 'done']);
});

for (const state of ['AWAITING_CONFIRMATION', 'AWAITING_AUTHENTICATION', 'NEEDS_CLARIFICATION', 'REJECTED', 'FAILED']) {
  test(`done 保留 ${state}，不会转换成成功`, async () => {
    const frames = await collect(start() + end(state));
    assert.equal(frames.at(-1).data.status, state);
  });
}

for (const [name, text] of [
  ['没有首个 status', end('COMPLETED')],
  ['串入其他请求', start() + event('message', { request_id: 'foreign', text: 'other' })],
  ['串入其他会话', start() + event('message', { thread_id: 'foreign', text: 'other' })],
  ['中途切换模型模式', start() + event('message', { mode: 'model', text: 'other' })],
  ['未知事件', start() + event('debug')],
  ['未知终态', start() + end('SUCCESS')],
  ['PROCESSING 不是结束状态', start() + end('PROCESSING')],
  ['done 后还有业务事件', start() + end('COMPLETED') + event('message', { text: 'late' })],
  ['非法 JSON', start() + 'event: done\ndata: {bad}\n\n'],
]) {
  test(`拒绝${name}`, async () => assert.rejects(collect(text), { code: 'INVALID_STREAM' }));
}

test('断流或缺少完整 done 不会被当作完成', async () => {
  await assert.rejects(collect(start()), { code: 'STREAM_INTERRUPTED' });
  await assert.rejects(collect(start() + end('COMPLETED').trimEnd()), { code: 'INVALID_STREAM' });
});

test('超大或非法 UTF-8 帧不会交给页面', async () => {
  const large = stream(start() + 'data: ' + 'x'.repeat(1024 * 1024), 65536);
  await assert.rejects(readAgentStream(large, () => {}), { code: 'INVALID_STREAM' });
  const invalid = new ReadableStream({ start(c) { c.enqueue(new Uint8Array([0xff])); c.close(); } });
  await assert.rejects(readAgentStream(invalid, () => {}), { code: 'STREAM_INTERRUPTED' });
});

test('POST 带会话认证但请求体不包含可信身份；不自动重试', async () => {
  let calls = 0;
  const token = randomUUID();
  const client = createAgentClient({ fetchImpl: async (url, options) => {
    calls++;
    assert.equal(url, '/agent/chat'); assert.equal(options.method, 'POST');
    assert.equal(options.headers.Authorization, `Bearer ${token}`);
    assert.deepEqual(JSON.parse(options.body), { thread_id: null, message: '查账单', resume: null });
    return response(start());
  } });
  await assert.rejects(client.send({ message: '查账单' }, { token, onEvent() {} }), { code: 'STREAM_INTERRUPTED' });
  assert.equal(calls, 1); assert.equal(client.busy, false);
});

test('双击只发一次；恢复请求只回传挑战和决定', async () => {
  let release, calls = 0;
  const wait = new Promise(resolve => { release = resolve; });
  const token = randomUUID();
  const client = createAgentClient({ fetchImpl: async (_, options) => {
    calls++; await wait;
    assert.deepEqual(JSON.parse(options.body), { thread_id: 'conv-test', message: null,
      resume: { challenge_id: 'ch-test', decision: 'reject' } });
    return response(start() + end('REJECTED'));
  } });
  const input = { thread_id: 'conv-test', resume: { challenge_id: 'ch-test', decision: 'reject' } };
  const first = client.send(input, { token, onEvent() {} });
  await assert.rejects(client.send(input, { token, onEvent() {} }), { code: 'RUN_BUSY' });
  release(); await first; assert.equal(calls, 1);
});

test('伪造可信字段、消息与恢复混用不会发出请求', async () => {
  let calls = 0;
  const client = createAgentClient({ fetchImpl() { calls++; } });
  for (const input of [{ message: 'hi', user_id: 'forged' },
    { thread_id: 'conv-test', message: 'hi', resume: { challenge_id: 'ch-test', decision: 'approve' } },
    { thread_id: 'conv-test', resume: { challenge_id: 'ch-test', decision: 'approve', authorized: true } }]) {
    await assert.rejects(client.send(input, { token: randomUUID(), onEvent() {} }), { code: 'INVALID_REQUEST' });
  }
  assert.equal(calls, 0);
});

test('HTTP 拒绝保留错误码，不显示服务端原文或重发', async () => {
  const client = createAgentClient({ fetchImpl: async () => new Response(JSON.stringify({
    code: 'RUN_BUSY', message: 'internal-details-must-not-display',
  }), { status: 409 }) });
  await assert.rejects(client.send({ message: 'hi' }, { token: randomUUID(), onEvent() {} }), error => {
    assert.equal(error.code, 'RUN_BUSY'); assert.ok(!error.message.includes('internal-details')); return true;
  });
});

test('错误内容类型、其他会话响应、取消均不重发', async () => {
  for (const fetchImpl of [async () => new Response('<html>unavailable</html>'),
    async () => response(start() + end('COMPLETED')),
    async () => { throw new DOMException('cancelled', 'AbortError'); }]) {
    const client = createAgentClient({ fetchImpl });
    await assert.rejects(client.send({ thread_id: 'another-thread', message: 'hi' },
      { token: randomUUID(), onEvent() {} }));
    assert.equal(client.busy, false);
  }
});
