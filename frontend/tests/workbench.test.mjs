import test, { afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { loadWorkbench } from './helpers/workbench.mjs';

const originalFetch = globalThis.fetch, originalDocument = globalThis.document;
afterEach(() => { globalThis.fetch = originalFetch; globalThis.document = originalDocument; });
const json = (data, status = 200) => new Response(JSON.stringify(data), { status,
  headers: { 'content-type': 'application/json' } });
const health = () => json({ status: 'ok', backend: 'ok', mode: 'offline', model: 'not_configured' });
const base = { thread_id: 'conv-test', request_id: 'req-test', mode: 'offline' };
const frame = (event, data, mode = 'offline') => `event: ${event}\ndata: ${JSON.stringify({ ...base, mode, ...data })}\n\n`;
const stream = body => new Response(body, { headers: { 'content-type': 'text/event-stream' } });
const confirmation = { operation: 'TRANSFER', recipient: '张伟', amount_minor: 30000, currency: 'CNY',
  risk_level: 'YELLOW', challenge_id: 'ch-test', operation_hash: 'hash-test', expires_at: '2026-10-18T12:05:00+08:00' };
function waiting() {
  return stream(frame('status', { step: 'started', status: 'PROCESSING' })
    + frame('status', { step: 'awaiting_confirmation', status: 'AWAITING_CONFIRMATION' })
    + frame('card', { type: 'confirm', payload: confirmation })
    + frame('interrupt', { kind: 'CONFIRMATION', challenge_id: confirmation.challenge_id, operation_hash: confirmation.operation_hash })
    + frame('done', { status: 'AWAITING_CONFIRMATION' }));
}
function completed() {
  return stream(frame('status', { step: 'started', status: 'PROCESSING' })
    + frame('card', { type: 'result', payload: { operation: 'TRANSFER', status: 'COMPLETED', error_code: null,
      data: { recipient: '张伟', amount_minor: 30000, remaining_balance_minor: 470000, currency: 'CNY', transaction_id: 'txn-test' } } })
    + frame('done', { status: 'COMPLETED' }));
}
async function interruptedConfirmation() {
  const sent = [];
  let next;
  const loaded = await loadWorkbench(async (url, options) => {
    if (url === '/health') return health();
    sent.push(JSON.parse(options.body));
    return next();
  });
  const { app } = loaded;
  app.state.token = randomUUID(); app.state.healthy = true;
  next = waiting;
  await app.send({ message: '给张伟转300元' });
  next = () => stream(frame('status', { step: 'started', status: 'PROCESSING' }));
  await app.respond('approve', false, confirmation.challenge_id);
  assert.equal(app.state.uncertain, true);
  return { ...loaded, sent, respondWith: fn => { next = fn; } };
}

test('断流后重试遇 RUN_BUSY 仍保留同挑战/同决定，恢复后可继续重试', async () => {
  const { app, doc, sent, respondWith } = await interruptedConfirmation();
  respondWith(() => json({ code: 'RUN_BUSY' }, 409));
  await app.respond('approve', true, confirmation.challenge_id);
  assert.equal(app.state.uncertain, true);
  assert.equal(doc.querySelectorAll('.retry')[0].hidden, false);
  assert.ok(doc.querySelectorAll('.decision').every(button => button.disabled));
  assert.deepEqual(sent[2], sent[1]);
  respondWith(completed);
  await app.respond('approve', true, confirmation.challenge_id);
  assert.deepEqual(sent[3], sent[1]);
  assert.equal(app.state.phase, 'COMPLETED');
  assert.equal(app.state.uncertain, false);
  assert.equal(app.state.pending, null);
  assert.equal(doc.elements.balance.textContent, '4,700.00');
  assert.equal(doc.elements.send.disabled, false);
});

test('确认重试的瞬时 HTTP 失败不丢失未决状态，也不自动重发', async () => {
  const { app, doc, sent, respondWith } = await interruptedConfirmation();
  respondWith(() => json({ code: 'HTTP_503' }, 503));
  await app.respond('approve', true, confirmation.challenge_id);
  assert.equal(sent.length, 3);
  assert.equal(app.state.uncertain, true);
  assert.equal(doc.querySelectorAll('.retry')[0].hidden, false);
});

for (const code of ['CHALLENGE_INVALID', 'CHALLENGE_STATE_MISMATCH', 'CONVERSATION_NOT_FOUND']) {
test(`明确 ${code} 后清除旧卡和未决标记，允许重新描述请求`, async () => {
  const { app, doc, respondWith } = await interruptedConfirmation();
  respondWith(() => json({ code }, code === 'CONVERSATION_NOT_FOUND' ? 404 : 409));
  await app.respond('approve', true, confirmation.challenge_id);
  assert.equal(app.state.pending, null);
  assert.equal(app.state.uncertain, false);
  assert.equal(doc.elements.send.disabled, false);
});

}

for (const mode of ['offline', 'model']) {
  test(`接受合法 ${mode} 会话并显示服务端模式`, async () => {
    const token = randomUUID();
    let requests = 0;
    const { app, doc } = await loadWorkbench(async url => {
      if (url === '/health') return json({ status: 'ok', backend: 'ok', mode, model: mode === 'model' ? 'ok' : 'not_configured' });
      if (url === '/demo/session') return json({ token, mode });
      requests++;
      return stream(frame('status', { step: 'started', status: 'PROCESSING' }, mode)
        + frame('done', { status: 'COMPLETED' }, mode));
    });
    await app.connect();
    assert.equal(app.state.token, token);
    assert.equal(requests, 1);
    assert.ok(doc.elements.mode.textContent.includes(mode === 'model' ? '模型模式' : '离线规则'));
  });
}

test('未知模式会话继续拒绝，不发送业务请求', async () => {
  let requests = 0;
  const { app } = await loadWorkbench(async url => {
    if (url === '/health') return health();
    if (url === '/demo/session') return json({ token: randomUUID(), mode: 'unknown' });
    requests++;
  });
  await app.connect();
  assert.equal(app.state.token, null);
  assert.equal(requests, 0);
});

test('澄清提示允许按服务器问题补充，后续仍沿用同 thread', async () => {
  const sent = [];
  const { app, doc } = await loadWorkbench(async (url, options) => {
    if (url === '/health') return health();
    sent.push(JSON.parse(options.body));
    if (sent.length > 1) return waiting();
    return stream(frame('status', { step: 'started', status: 'PROCESSING' })
      + frame('message', { text: '还需要确认：金额。' }) + frame('done', { status: 'NEEDS_CLARIFICATION' }));
  });
  app.state.token = randomUUID(); app.state.healthy = true;
  await app.send({ message: '给张伟转钱' });
  assert.equal(app.state.phase, 'NEEDS_CLARIFICATION');
  assert.equal(doc.elements.send.disabled, false);
  assert.ok(doc.elements.notice.textContent.includes('补充'));
  assert.ok(!doc.elements.notice.textContent.includes('尚未接入'));
  await app.send({ thread_id: app.state.thread, message: '300元' });
  assert.equal(sent[1].thread_id, base.thread_id);
  assert.equal(app.state.phase, 'AWAITING_CONFIRMATION');
});


test('未决批准只能以相同决定重试，旧卡按钮不能作用于新卡', async () => {
  const { app, sent, respondWith } = await interruptedConfirmation();
  respondWith(completed);
  await app.respond('reject', true, confirmation.challenge_id);
  await app.respond('approve', true, 'old-challenge');
  assert.equal(sent.length, 2);
  assert.equal(app.state.decision, 'approve');
  await app.respond('approve', true, confirmation.challenge_id);
  assert.equal(sent.length, 3);
});


test('重置响应丢失后收到401可清理旧确认，手动重连并查询真实余额', async () => {
  const oldToken = randomUUID(), freshToken = randomUUID();
  let resets = 0, sessions = 0;
  const chatBodies = [];
  const { app, doc } = await loadWorkbench(async (url, options) => {
    if (url === '/health') return health();
    if (url === '/demo/reset') {
      resets++;
      if (resets === 1) throw new TypeError('reset response lost');
      return json({ code: 'UNAUTHENTICATED' }, 401);
    }
    if (url === '/demo/session') { sessions++; return json({ token: freshToken, mode: 'offline' }); }
    assert.equal(url, '/agent/chat');
    chatBodies.push(JSON.parse(options.body));
    if (sessions === 0) return waiting();
    assert.equal(options.headers.Authorization, `Bearer ${freshToken}`);
    return stream(frame('status', { step: 'started', status: 'PROCESSING' })
      + frame('card', { type: 'result', payload: { operation: 'GET_BALANCE', status: 'COMPLETED',
        error_code: null, data: { balance_minor: 500000, currency: 'CNY' } } })
      + frame('done', { status: 'COMPLETED' }));
  });
  app.state.token = oldToken; app.state.healthy = true;
  await app.send({ message: '给张伟转300元' });
  app.state.uncertain = true; app.state.decision = 'approve'; app.controls();
  doc.elements.balance.textContent = '4,700.00';
  doc.elements['reset-dialog'].returnValue = 'confirm';
  await doc.elements['reset-dialog'].emit('close');
  assert.equal(resets, 1); // 断网不自动重发或假称重置成功。
  assert.equal(app.state.token, oldToken);
  assert.equal(app.state.pending.challenge_id, confirmation.challenge_id);
  assert.equal(app.state.uncertain, true);
  assert.ok(doc.elements.notice.textContent.includes('尚未确认重置结果'));
  await doc.elements['reset-dialog'].emit('close');
  assert.equal(resets, 2);
  for (const key of ['token', 'thread', 'pending', 'signal', 'decision']) assert.equal(app.state[key], null);
  assert.equal(app.state.uncertain, false);
  assert.equal(app.state.phase, 'IDLE');
  assert.equal(doc.elements.balance.textContent, '—');
  assert.equal(doc.elements.messages.children.length, 0);
  assert.equal(doc.elements.connect.disabled, false);
  assert.equal(doc.elements.send.disabled, true);
  assert.equal(sessions, 0); // 401 只恢复入口，由用户决定重连。
  assert.ok(doc.elements.notice.textContent.includes('会话已失效'));
  assert.ok(!doc.elements.notice.textContent.includes('已恢复'));
  await doc.elements.connect.emit('click');
  assert.equal(sessions, 1);
  assert.equal(app.state.token, freshToken);
  assert.deepEqual(chatBodies[1], { thread_id: null, message: '查询余额', resume: null });
  assert.equal(doc.elements.balance.textContent, '5,000.00');
  assert.equal(doc.elements.send.disabled, false);
});
