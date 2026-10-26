import test from 'node:test';
import assert from 'node:assert/strict';
import { money, readConfirmation, confirmationReady, readBills, readResult } from '../view-model.mjs';

test('卡片查询接受待激活状态，但不能把解冻当作激活', () => {
  const card = { card_id: 'new', display_name: '新卡', status: 'PENDING_ACTIVATION' };
  assert.equal(readResult({ operation: 'QUERY_CARDS', status: 'COMPLETED', error_code: null,
    data: { cards: [card] } }).data.cards[0].status, 'PENDING_ACTIVATION');
  assert.throws(() => readResult({ operation: 'UNFREEZE_CARD', status: 'COMPLETED', error_code: null,
    data: { ...card, status: 'ACTIVE', previous_status: 'PENDING_ACTIVATION', changed: true } }));
});

const confirmation = () => ({ operation: 'TRANSFER', recipient: '演示收款人', amount_minor: 30000,
  currency: 'CNY', risk_level: 'YELLOW', challenge_id: 'ch-test', operation_hash: 'hash-test',
  expires_at: '2026-10-18T12:05:00+08:00' });
const signal = () => ({ challenge_id: 'ch-test', operation_hash: 'hash-test', kind: 'CONFIRMATION' });
const bills = () => ({ start: '2026-10-01', end: '2026-11-01', currency: 'CNY', total_minor: 5000,
  by_category: { '订阅': 5000 }, transactions: ['t1', 't2'].map((id, index) => ({
    transaction_id: id, occurred_at: `2026-10-12T10:00:${index ? '30' : '00'}+08:00`,
    amount_minor: 2500, kind: 'EXPENSE', category: '订阅', merchant: '演示商户',
  })), anomalies: [{ type: 'POSSIBLE_DUPLICATE', evidence: ['t1', 't2'] }] });

test('金额展示全程按整数分，无浮点换算', () => {
  assert.equal(money(0), '0.00'); assert.equal(money(1), '0.01');
  assert.equal(money(30000), '300.00'); assert.equal(money(470000), '4,700.00');
  assert.equal(money(Number.MAX_SAFE_INTEGER), '90,071,992,547,409.91');
  for (const value of [true, '30000', -1, 0.1, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1]) {
    assert.throws(() => money(value));
  }
});

test('确认卡仅接受完整服务端业务字段', () => {
  const card = readConfirmation({ ...confirmation(), authorization_ref: 'must-not-copy' });
  assert.equal(card.recipient, '演示收款人'); assert.ok(!('authorization_ref' in card));
  for (const fields of [{ amount_minor: 0 }, { amount_minor: 300.01 }, { recipient: '' },
    { risk_level: 'GREEN' }, { currency: 'USD' }, { expires_at: 'invalid' },
    { challenge_id: '' }, { operation_hash: '' }]) {
    assert.throws(() => readConfirmation({ ...confirmation(), ...fields }));
  }
});

test('确认按钮需同时匹配卡片、interrupt 和等待状态', () => {
  const card = readConfirmation(confirmation());
  assert.ok(confirmationReady(card, signal(), 'AWAITING_CONFIRMATION'));
  assert.ok(!confirmationReady(card, null, 'AWAITING_CONFIRMATION'));
  assert.ok(!confirmationReady(card, signal(), 'PROCESSING'));
  assert.ok(!confirmationReady(card, signal(), 'AWAITING_CONFIRMATION', 'old-card'));
  assert.ok(!confirmationReady(card, { ...signal(), challenge_id: 'other' }, 'AWAITING_CONFIRMATION'));
  assert.ok(!confirmationReady(card, { ...signal(), operation_hash: 'changed' }, 'AWAITING_CONFIRMATION'));
  assert.ok(!confirmationReady(card, { ...signal(), kind: 'STRONG_AUTH' }, 'AWAITING_CONFIRMATION'));
  const red = readConfirmation({ ...confirmation(), risk_level: 'RED' });
  assert.ok(confirmationReady(red, { ...signal(), kind: 'STRONG_AUTH' }, 'AWAITING_AUTHENTICATION'));
  assert.ok(!confirmationReady(red, signal(), 'AWAITING_CONFIRMATION'));
  // Demo 的业务日期与浏览器当天可以不同；是否过期必须由服务端判定。
  assert.ok(confirmationReady(card, signal(), 'AWAITING_CONFIRMATION'));
});

test('疑似重复证据必须指向本期至少两笔不同交易', () => {
  assert.equal(readBills(bills()).anomalies.length, 1);
  for (const evidence of [['t1'], ['t1', 't1'], ['t1', 'missing']]) {
    const bad = bills(); bad.anomalies[0].evidence = evidence;
    assert.throws(() => readBills(bad));
  }
  const bad = bills(); bad.transactions[1].transaction_id = 't1';
  assert.throws(() => readBills(bad));
});

test('分类总额不一致、浮点金额和超限账单不展示', () => {
  for (const modify of [data => { data.total_minor++; },
    data => { data.by_category['订阅'] = 50.5; },
    data => { data.transactions[0].amount_minor = -1; },
    data => { data.transactions = Array.from({ length: 101 }, (_, i) => ({ ...data.transactions[0], transaction_id: `t${i}` })); }]) {
    const data = bills(); modify(data); assert.throws(() => readBills(data));
  }
  const empty = { ...bills(), total_minor: 0, by_category: {}, transactions: [], anomalies: [] };
  assert.equal(readBills(empty).total_minor, 0);
});

test('失败与拒绝保持原状态，不伪造成功；未知意图允许未分配操作名', () => {
  for (const status of ['REJECTED', 'FAILED', 'PENDING']) {
    const result = { operation: '', status, data: null, error_code: 'UNSUPPORTED_INTENT' };
    assert.equal(readResult(result).status, status);
  }
  assert.throws(() => readResult({ operation: '', status: 'COMPLETED', data: {}, error_code: null }));
  assert.throws(() => readResult({ operation: 'TRANSFER', status: 'COMPLETED', data: {}, error_code: 'ERROR' }));
});

test('成功转账必须包含真实结果所需字段和有效整数金额', () => {
  const result = { operation: 'TRANSFER', status: 'COMPLETED', error_code: null,
    data: { recipient: '演示收款人', amount_minor: 30000, remaining_balance_minor: 470000,
      currency: 'CNY', transaction_id: 'txn-test' } };
  assert.equal(readResult(result).data.remaining_balance_minor, 470000);
  for (const fields of [{ remaining_balance_minor: -1 }, { transaction_id: '' }, { amount_minor: true }]) {
    assert.throws(() => readResult({ ...result, data: { ...result.data, ...fields } }));
  }
});


test('连续筛选条件保留整数分与明确清空值，非法条件不展示', () => {
  const filters = { category: '餐饮', merchant: null, amount_gt_minor: 10000 };
  assert.deepEqual(readBills({ ...bills(), filters }).filters, filters);
  for (const bad of [null, [], { ...filters, amount_gt_minor: true },
    { ...filters, amount_gt_minor: 1.1 }, { ...filters, category: {} }]) {
    assert.throws(() => readBills({ ...bills(), filters: bad }));
  }
});
