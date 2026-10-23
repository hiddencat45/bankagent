import test, { afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { readConfirmation, readResult } from '../view-model.mjs';
import { loadWorkbench } from './helpers/workbench.mjs';

const originalFetch = globalThis.fetch, originalDocument = globalThis.document;
afterEach(() => { globalThis.fetch = originalFetch; globalThis.document = originalDocument; });
const record = { subscription_id: 'subscription-001', display_name: '演示订阅', status: 'ACTIVE',
  amount_minor: 2500, currency: 'CNY', next_payment_date: '2026-11-12' };
const summary = { ...record, paid_minor: 5000, payments: [
  { transaction_id: 'txn-005', occurred_at: '2026-10-12T10:00:00+08:00', amount_minor: 2500 },
  { transaction_id: 'txn-006', occurred_at: '2026-10-12T10:00:30+08:00', amount_minor: 2500 },
] };
const query = () => ({ operation: 'QUERY_SUBSCRIPTIONS', status: 'COMPLETED', error_code: null,
  data: { start: '2026-10-01', end: '2026-11-01', currency: 'CNY', total_minor: 5000, subscriptions: [structuredClone(summary)] } });
const confirmation = { operation: 'PAUSE_SUBSCRIPTION', display_name: record.display_name,
  current_status: 'ACTIVE', target_status: 'PAUSED', risk_level: 'YELLOW', challenge_id: 'ch-sub',
  operation_hash: 'hash-sub', expires_at: '2026-10-18T12:05:00+08:00' };
const frame = (event, data) => `event: ${event}\ndata: ${JSON.stringify({
  thread_id: 'sub-thread', request_id: 'sub-request', mode: 'offline', ...data })}\n\n`;
const stream = events => new Response(events, { headers: { 'content-type': 'text/event-stream' } });
const resultStream = payload => stream(frame('status', { step: 'started', status: 'PROCESSING' })
  + frame('card', { type: 'result', payload }) + frame('done', { status: payload.status }));

test('订阅按实际流水核对金额，拒绝虚构合计和跨协议重复证据', () => {
  assert.equal(readResult(query()).data.subscriptions[0].paid_minor, 5000);
  for (const change of [r => r.data.total_minor++, r => r.data.subscriptions[0].paid_minor++,
    r => r.data.subscriptions[0].payments.push({ ...summary.payments[0] }),
    r => r.data.subscriptions.push({ ...structuredClone(summary), subscription_id: 'other' })]) {
    const bad = query(); change(bad); assert.throws(() => readResult(bad));
  }
  const empty = query(); empty.data.subscriptions = []; empty.data.total_minor = 0;
  assert.equal(readResult(empty).data.total_minor, 0);
});

test('暂停确认限定协议状态，已暂停协议无后续扣费日期', () => {
  const card = readConfirmation({ ...confirmation, subscription_id: 'do-not-copy' });
  assert.ok(!('subscription_id' in card));
  for (const fields of [{ current_status: 'FROZEN' }, { target_status: 'ACTIVE' }]) {
    assert.throws(() => readConfirmation({ ...confirmation, ...fields }));
  }
  const paused = { operation: 'PAUSE_SUBSCRIPTION', status: 'COMPLETED', error_code: null,
    data: { ...record, status: 'PAUSED', next_payment_date: null, previous_status: 'ACTIVE', changed: true } };
  assert.equal(readResult(paused).data.status, 'PAUSED');
  assert.throws(() => readResult({ ...paused, data: { ...paused.data, next_payment_date: '2026-11-12' } }));
});

test('订阅证据填入暂停申请后仍需发送并确认，回执不改余额或历史扣费', async () => {
  let response;
  const sent = [];
  const { app, doc } = await loadWorkbench(async (url, options) => {
    if (url === '/health') return new Response(JSON.stringify({ status: 'ok', backend: 'ok', mode: 'offline', model: 'not_configured' }));
    sent.push(JSON.parse(options.body)); return response();
  });
  app.state.token = randomUUID(); app.state.healthy = true;
  doc.elements.balance.textContent = '5,000.00';
  response = () => resultStream(query());
  await app.send({ message: '查询订阅' });
  assert.ok(doc.elements.messages.all().some(n => n.textContent.includes('本期 2 笔，共 ¥ 50.00')));
  const requestButton = doc.elements.messages.all().find(n => n.textContent === '申请暂停此代扣');
  await requestButton.emit('click');
  assert.equal(sent.length, 1);
  assert.equal(doc.elements.input.value, '暂停演示订阅的代扣');
  response = () => stream(frame('status', { step: 'started', status: 'PROCESSING' })
    + frame('status', { step: 'awaiting_confirmation', status: 'AWAITING_CONFIRMATION' })
    + frame('card', { type: 'confirm', payload: confirmation })
    + frame('interrupt', { kind: 'CONFIRMATION', challenge_id: 'ch-sub', operation_hash: 'hash-sub' })
    + frame('done', { status: 'AWAITING_CONFIRMATION' }));
  await app.send({ message: doc.elements.input.value });
  assert.equal(app.state.phase, 'AWAITING_CONFIRMATION');
  assert.equal(doc.querySelectorAll('.decision').find(b => b.dataset.decision === 'approve').textContent, '确认暂停代扣');
  response = () => resultStream({ operation: 'PAUSE_SUBSCRIPTION', status: 'COMPLETED', error_code: null,
    data: { ...record, status: 'PAUSED', next_payment_date: null, previous_status: 'ACTIVE', changed: true } });
  await app.respond('approve', false, 'ch-sub');
  assert.deepEqual(sent[2].resume, { challenge_id: 'ch-sub', decision: 'approve' });
  assert.equal(doc.elements.balance.textContent, '5,000.00');
  const after = query(); Object.assign(after.data.subscriptions[0], { status: 'PAUSED', next_payment_date: null });
  response = () => resultStream(after);
  await app.send({ message: '查询订阅' });
  assert.ok(doc.elements.messages.all().some(n => n.textContent.includes('本期 2 笔，共 ¥ 50.00')));
  const buttons = doc.elements.messages.all().filter(n => n.textContent === '申请暂停此代扣');
  assert.equal(buttons.at(-1).disabled, true);
});
