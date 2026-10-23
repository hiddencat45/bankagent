import test, { afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { readConfirmation, readResult } from '../view-model.mjs';
import { loadWorkbench } from './helpers/workbench.mjs';

const originalFetch = globalThis.fetch, originalDocument = globalThis.document;
afterEach(() => { globalThis.fetch = originalFetch; globalThis.document = originalDocument; });
const card = { card_id: 'card-001', display_name: '日常消费卡', status: 'ACTIVE' };
const confirmation = { operation: 'FREEZE_CARD', display_name: card.display_name,
  current_status: 'ACTIVE', target_status: 'FROZEN', risk_level: 'YELLOW',
  challenge_id: 'ch-card', operation_hash: 'hash-card', expires_at: '2026-10-18T12:05:00+08:00' };
const result = (operation, data) => ({ operation, data, status: 'COMPLETED', error_code: null });
const frame = (event, data) => `event: ${event}\ndata: ${JSON.stringify({
  thread_id: 'card-conversation', request_id: 'card-request', mode: 'offline', ...data })}\n\n`;
const stream = events => new Response(events, { headers: { 'content-type': 'text/event-stream' } });
const output = payload => stream(frame('status', { step: 'started', status: 'PROCESSING' })
  + frame('card', { type: 'result', payload }) + frame('done', { status: 'COMPLETED' }));

test('卡片确认明确限定操作目标，不允许前端改写或继承实体ID', () => {
  const value = readConfirmation({ ...confirmation, card_id: 'must-not-copy', authorized: true });
  assert.equal(value.target_status, 'FROZEN');
  assert.ok(!('card_id' in value) && !('authorized' in value));
  assert.equal(readConfirmation({ ...confirmation, operation: 'UNFREEZE_CARD', target_status: 'ACTIVE' }).target_status, 'ACTIVE');
  for (const fields of [{ operation: 'DELETE_CARD' }, { target_status: 'ACTIVE' },
    { current_status: 'LOST' }, { display_name: '' }, { risk_level: 'GREEN' }]) {
    assert.throws(() => readConfirmation({ ...confirmation, ...fields }));
  }
});

test('卡片结果支持空列表，拒绝重复ID、非法状态和矛盾回执', () => {
  assert.equal(readResult(result('QUERY_CARDS', { cards: [] })).data.cards.length, 0);
  assert.equal(readResult(result('QUERY_CARDS', { cards: [card] })).data.cards[0].status, 'ACTIVE');
  for (const rows of [[card, card], [{ ...card, status: 'LOST' }], [{ ...card, card_id: '' }]]) {
    assert.throws(() => readResult(result('QUERY_CARDS', { cards: rows })));
  }
  const receipt = { ...card, status: 'FROZEN', previous_status: 'ACTIVE', changed: true };
  assert.equal(readResult(result('FREEZE_CARD', receipt)).data.changed, true);
  for (const fields of [{ changed: false }, { status: 'ACTIVE' }, { previous_status: 'LOST' }]) {
    assert.throws(() => readResult(result('FREEZE_CARD', { ...receipt, ...fields })));
  }
});

test('冻结确认沿用挑战与决定，回执和重新查询的当前状态分别展示', async () => {
  const sent = [];
  let response;
  const { app, doc } = await loadWorkbench(async (url, options) => {
    if (url === '/health') return new Response(JSON.stringify({ status: 'ok', backend: 'ok', mode: 'offline', model: 'not_configured' }));
    sent.push(JSON.parse(options.body)); return response();
  });
  app.state.token = randomUUID(); app.state.healthy = true;
  doc.elements.balance.textContent = '5,000.00';
  response = () => stream(frame('status', { step: 'started', status: 'PROCESSING' })
    + frame('status', { step: 'awaiting_confirmation', status: 'AWAITING_CONFIRMATION' })
    + frame('card', { type: 'confirm', payload: confirmation })
    + frame('interrupt', { kind: 'CONFIRMATION', challenge_id: 'ch-card', operation_hash: 'hash-card' })
    + frame('done', { status: 'AWAITING_CONFIRMATION' }));
  await app.send({ message: '冻结日常消费卡' });
  assert.equal(app.state.phase, 'AWAITING_CONFIRMATION');
  const buttons = doc.querySelectorAll('.decision');
  assert.equal(buttons.find(b => b.dataset.decision === 'approve').textContent, '确认冻结卡片');
  assert.ok(buttons.every(b => !b.disabled));
  response = () => output(result('FREEZE_CARD', { ...card, status: 'FROZEN', previous_status: 'ACTIVE', changed: true }));
  await app.respond('approve', false, 'ch-card');
  assert.deepEqual(sent[1].resume, { challenge_id: 'ch-card', decision: 'approve' });
  assert.equal(app.state.phase, 'COMPLETED');
  assert.equal(doc.elements.balance.textContent, '5,000.00');
  assert.ok(doc.elements.messages.all().some(n => n.textContent.includes('这是该请求的办理回执')));
  response = () => output(result('QUERY_CARDS', { cards: [card] }));
  await app.send({ message: '我的卡片' });
  assert.ok(doc.elements.messages.all().some(n => n.textContent === '日常消费卡 · 可用'));
  assert.ok(doc.elements.messages.all().some(n => n.textContent === '日常消费卡 · 已冻结'));
});
