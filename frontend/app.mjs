import { createAgentClient } from './agent-client.mjs';
import { money, readBills, readConfirmation, confirmationReady, readResult } from './view-model.mjs';

const $ = id => document.getElementById(id);
const node = (tag, cls, text) => {
  const value = document.createElement(tag);
  if (cls) value.className = cls;
  if (text !== undefined) value.textContent = text;
  return value;
};
const client = createAgentClient();
const state = { token: null, thread: null, phase: 'IDLE', pending: null, signal: null,
  busy: false, healthy: false, uncertain: false, decision: null };
const phases = { IDLE: '等待请求', PROCESSING: '正在办理', COMPLETED: '办理完成',
  REJECTED: '已拒绝或取消', FAILED: '办理失败', PENDING: '已提交待处理',
  NEEDS_CLARIFICATION: '等待补充信息', AWAITING_CONFIRMATION: '等待本人确认',
  AWAITING_AUTHENTICATION: '需要独立认证' };
const steps = { started: '服务端已接收请求', understood: '已识别业务意图',
  validated: '已校验业务信息', awaiting_confirmation: '已生成确认操作',
  awaiting_authentication: '需要独立认证', executing: '正在执行操作', finished: '本轮处理结束' };
const cardStatus = { PENDING_ACTIVATION: '待激活', ACTIVE: '可用', FROZEN: '已冻结' };
let pendingNode;

function notice(text, warning = false) {
  $('notice').textContent = text; $('notice').classList.toggle('warning', warning);
}
function bubble(text, user = false) {
  $('messages').querySelector('.welcome')?.remove();
  $('messages').append(node('div', `bubble${user ? ' user' : ''}`, text));
}
function trace(text, detail) {
  $('trace').querySelector('.empty-trace')?.remove();
  const item = node('li', '', text); item.append(node('small', '', detail));
  $('trace').append(item);
  if ($('trace').children.length > 30) $('trace').firstElementChild.remove();
}
function controls() {
  const ready = state.token && state.healthy && !state.busy;
  const canChat = ready && !state.pending && !state.uncertain;
  $('send').disabled = $('input').disabled = !canChat;
  document.querySelectorAll('[data-query],#example,#new').forEach(button => { button.disabled = !canChat; });
  $('connect').disabled = state.busy || Boolean(state.token);
  $('connect').textContent = state.token ? '演示已连接' : '开始演示';
  $('reset').disabled = !state.token || state.busy;
  $('phase').textContent = phases[state.phase] ?? '等待连接';
  document.querySelectorAll('.decision').forEach(button => {
    const confirmed = confirmationReady(state.pending, state.signal, state.phase, button.dataset.challenge);
    button.disabled = !ready || !confirmed || state.uncertain
      || (button.dataset.decision === 'approve' && state.pending?.risk_level === 'RED');
  });
  document.querySelectorAll('.retry').forEach(button => {
    button.hidden = !(state.uncertain && state.pending && state.decision
      && button.dataset.challenge === state.pending.challenge_id);
    button.disabled = !ready;
  });
}
function card(title, cls = '') {
  $('messages').querySelector('.welcome')?.remove();
  const box = node('section', `business-card ${cls}`); box.append(node('h3', '', title));
  $('messages').append(box); return box;
}
function evidence(data) {
  readBills(data);
  const box = card('本期账单 · 以交易为依据');
  box.append(node('p', '', `${data.start} 至 ${data.end}（结束日不含）`),
    node('div', 'amount', `¥ ${money(data.total_minor)}`), node('p', '', '消费合计 · 收入与转账不计入消费'));
  if (data.filters) {
    const filters = [];
    if (data.filters.category !== null) filters.push(`类别：${data.filters.category}`);
    if (data.filters.merchant !== null) filters.push(`商户包含：${data.filters.merchant}`);
    if (data.filters.amount_gt_minor !== null) filters.push(`金额严格大于 ¥ ${money(data.filters.amount_gt_minor)}`);
    box.append(node('p', '', filters.length ? filters.join(' · ') : '全部消费类别 · 不限金额'));
  }
  for (const [name, amount] of Object.entries(data.by_category)) {
    const row = node('div', 'category'); row.append(node('span', '', name), node('strong', '', `¥ ${money(amount)}`)); box.append(row);
  }
  for (const anomaly of data.anomalies) {
    const group = node('div', 'evidence', '疑似重复扣款，尚未认定欺诈：');
    for (const id of anomaly.evidence) {
      const row = data.transactions.find(transaction => transaction.transaction_id === id);
      group.append(node('div', '', `${row.merchant} · ¥ ${money(row.amount_minor)} · ${row.occurred_at}`));
    }
    box.append(group);
  }
  const detail = node('details'); detail.append(node('summary', '', `查看 ${data.transactions.length} 笔交易明细`));
  for (const row of data.transactions) {
    const kind = { INCOME: '收入', EXPENSE: '消费', TRANSFER_OUT: '转出', TRANSFER_IN: '转入', WEALTH_RESERVE: '申购冻结', WEALTH_RELEASE: '理财解冻', WEALTH_CREDIT: '赎回到账' }[row.kind];
    const item = node('div', 'transaction', `${kind} · ${row.category} · ${row.merchant ?? '未提供商户'} · ¥ ${money(row.amount_minor)}`);
    item.append(node('small', '', `${row.occurred_at} · ${row.transaction_id}`)); detail.append(item);
  }
  box.append(detail);
}
function confirmation(payload) {
  const value = readConfirmation(payload);
  if (state.pending?.challenge_id === value.challenge_id) {
    if (JSON.stringify(state.pending) !== JSON.stringify(value)) throw new Error('确认卡内容发生变化。');
    return;
  }
  state.pending = value; state.signal = null;
  const transfer = value.operation === 'TRANSFER';
  const action = transfer ? '转账' : value.operation === 'FREEZE_CARD' ? '冻结卡片' : '解冻卡片';
  pendingNode = card(`${action}需要本人确认`, 'confirm-card');
  if (transfer) {
    pendingNode.append(node('p', '', `收款人：${value.recipient}`), node('div', 'amount', `¥ ${money(value.amount_minor)}`));
  } else {
    pendingNode.append(node('p', '', `卡片：${value.display_name}`),
      node('p', '', `${cardStatus[value.current_status]} → ${cardStatus[value.target_status]}`),
      node('p', '', '仅变更模拟卡片状态，不涉及余额或历史账单；尚未模拟刷卡扣款。'));
  }
  pendingNode.append(node('p', '', value.risk_level === 'RED'
    ? '高风险：独立认证尚未接入，当前不能批准；可以取消。'
    : transfer ? '请核对收款人与金额。确认前不会扣款，有效期由服务端重新校验。'
      : '请核对卡片和目标状态。确认前不会变更，有效期由服务端重新校验。'));
  const actions = node('div', 'actions');
  for (const [decision, label] of [['reject', `取消${action}`], ['approve', `确认${action}`]]) {
    const button = node('button', `decision ${decision === 'approve' ? 'approve' : 'quiet'}`, label);
    button.dataset.decision = decision; button.dataset.challenge = value.challenge_id; button.disabled = true;
    button.addEventListener('click', () => respond(decision, false, value.challenge_id)); actions.append(button);
  }
  const retry = node('button', 'retry', '核对并重试本次确认'); retry.hidden = true;
  retry.dataset.challenge = value.challenge_id;
  retry.addEventListener('click', () => respond(state.decision, true, value.challenge_id)); actions.append(retry); pendingNode.append(actions);
}
function accept({ event, data }) {
  if (event === 'status') {
    state.thread = data.thread_id; state.phase = data.status;
    $('mode').textContent = `${data.mode === 'offline' ? '离线规则' : '模型模式'} · 本地模拟银行`;
    trace(steps[data.step] ?? '服务端状态', phases[data.status] ?? data.status);
  } else if (event === 'message') bubble(data.text);
  else if (event === 'card') {
    if (data.type === 'confirm') confirmation(data.payload);
    else if (data.type === 'evidence') evidence(data.payload.data);
    else if (data.type === 'result') {
      const result = readResult(data.payload);
      if (result.status === 'COMPLETED') {
        if (result.operation === 'GET_BALANCE') $('balance').textContent = money(result.data.balance_minor);
        if (result.operation === 'TRANSFER') {
          $('balance').textContent = money(result.data.remaining_balance_minor);
          const box = card('转账已完成'); box.append(node('div', 'amount', `¥ ${money(result.data.amount_minor)}`),
            node('p', '', `收款人：${result.data.recipient}`), node('p', '', `交易流水：${result.data.transaction_id}`));
        }
        if (result.operation === 'QUERY_CARDS') {
          const box = card('卡片状态 · 本次查询结果');
          if (result.data.cards.length === 0) box.append(node('p', '', '本账户暂无卡片。'));
          for (const row of result.data.cards) {
            box.append(node('p', '', `${row.display_name} · ${cardStatus[row.status]}`));
          }
        }
        if (['FREEZE_CARD', 'UNFREEZE_CARD'].includes(result.operation)) {
          const box = card('卡片操作回执');
          box.append(node('p', '', `${result.data.display_name} · ${cardStatus[result.data.status]}`),
            node('p', '', result.data.changed ? '本次请求已完成状态变更。' : '办理时已是目标状态，本次未重复变更。'),
            node('p', '', '这是该请求的办理回执。后续操作可能已改变状态，请重新查询卡片核对当前状态。'));
        }
      } else trace(phases[result.status], result.error_code === 'USER_CANCELLED'
        ? '本次操作已取消，账户未发生变动。' : '请查看对话中的办理说明。');
    }
  } else if (event === 'interrupt') {
    state.signal = { kind: data.kind, challenge_id: data.challenge_id, operation_hash: data.operation_hash };
    if (!confirmationReady(state.pending, state.signal, state.phase)) throw new Error('确认卡与服务端暂停信息不一致。');
  } else if (event === 'error') notice(data.message, true);
  else if (event === 'done') {
    state.phase = data.status;
    if (['COMPLETED', 'REJECTED', 'NEEDS_CLARIFICATION'].includes(data.status)) {
      state.pending = state.signal = null; state.decision = null;
      state.uncertain = false;
    }
    if (data.status === 'FAILED' && state.decision) state.uncertain = true;
    if (data.status === 'NEEDS_CLARIFICATION') notice('请按上面的提示补充信息或重新描述请求。');
    else if (data.status !== 'FAILED') notice(phases[data.status]);
  }
  controls();
}
async function send(input) {
  if (state.busy) return;
  const retrying = state.uncertain && state.pending
    && input?.resume?.challenge_id === state.pending.challenge_id
    && input.resume.decision === state.decision;
  state.busy = true; state.uncertain = Boolean(retrying); controls();
  notice('正在等待服务端处理…');
  try { await client.send(input, { token: state.token, onEvent: accept }); }
  catch (error) {
    if (['STREAM_INTERRUPTED', 'CONNECTION_FAILED', 'INVALID_STREAM'].includes(error.code)) {
      state.uncertain = true;
      notice('连接或响应中断，结果尚未确认。不会自动重发；可重试同一确认，或重置演示后再开始。', true);
    } else {
      notice(({ RUN_BUSY: '请先处理当前确认卡，或等待正在办理的业务结束。',
        UNAUTHENTICATED: '演示会话已失效，请重新开始演示。', CHALLENGE_INVALID: '确认卡已失效或未获准，请重新发起。',
        CHALLENGE_STATE_MISMATCH: '操作信息已变化，旧确认卡不能继续使用。' })[error.code] ?? '请求未被接受，请检查连接或重试。', true);
      if (error.code === 'UNAUTHENTICATED') state.token = null;
      if (['CHALLENGE_INVALID', 'CHALLENGE_STATE_MISMATCH', 'CONVERSATION_NOT_FOUND'].includes(error.code)) {
        state.pending = state.signal = null; state.thread = null; state.decision = null; state.phase = 'REJECTED';
        state.uncertain = false;
      }
    }
  } finally { state.busy = false; controls(); $('messages').scrollTop = $('messages').scrollHeight; }
}
function respond(decision, retry, challengeId) {
  if (!state.pending || state.pending.challenge_id !== challengeId || state.busy
      || !['approve', 'reject'].includes(decision)) return;
  if (retry && (!state.uncertain || decision !== state.decision)) return;
  if (!retry && (!confirmationReady(state.pending, state.signal, state.phase) || state.uncertain)) return;
  if (decision === 'approve' && state.pending.risk_level === 'RED') return;
  state.decision = decision;
  return send({ thread_id: state.thread, message: null, resume: { challenge_id: state.pending.challenge_id, decision } });
}
async function health() {
  try {
    const response = await fetch('/health', { cache: 'no-store' });
    const data = await response.json();
    state.healthy = response.ok && data.status === 'ok' && data.backend === 'ok';
    $('health').textContent = state.healthy ? '服务已连接' : '服务暂不可用';
  } catch { state.healthy = false; $('health').textContent = '服务未连接'; }
  $('health').classList.toggle('ok', state.healthy); controls();
}
async function connect() {
  if (state.busy) return;
  state.busy = true; controls();
  try {
    await health(); if (!state.healthy) throw new Error();
    const response = await fetch('/demo/session', { method: 'POST', cache: 'no-store' });
    const data = await response.json();
    if (!response.ok || typeof data.token !== 'string' || !data.token
        || !['offline', 'model'].includes(data.mode)) throw new Error();
    $('mode').textContent = `${data.mode === 'offline' ? '离线规则' : '模型模式'} · 本地模拟银行`;
    state.token = data.token; state.thread = null; state.pending = state.signal = null;
    state.uncertain = false; state.decision = null; state.phase = 'IDLE';
  } catch { notice('无法建立本地演示会话，请检查服务启动方式。', true); }
  finally { state.busy = false; controls(); }
  if (state.token) await send({ message: '查询余额' });
}
$('connect').addEventListener('click', connect);
$('refresh').addEventListener('click', health);
$('composer').addEventListener('submit', event => {
  event.preventDefault(); const message = $('input').value.trim();
  if (!message || $('send').disabled) return;
  bubble(message, true); $('input').value = '';
  send({ thread_id: state.thread, message });
});
document.querySelectorAll('[data-query]').forEach(button => button.addEventListener('click', () => {
  bubble(button.dataset.query, true); send({ thread_id: state.thread, message: button.dataset.query });
}));
$('example').addEventListener('click', () => { $('input').value = '给张伟转 300 元'; $('input').focus(); });
$('new').addEventListener('click', () => { state.thread = null; state.phase = 'IDLE'; $('messages').replaceChildren(); notice('已开始新对话，模拟账本保持当前状态。'); controls(); });
function clearSessionView() {
  state.token = state.pending = state.signal = null; state.thread = null; state.decision = null;
  state.uncertain = false; state.phase = 'IDLE';
  $('messages').replaceChildren(); $('trace').replaceChildren(); $('balance').textContent = '—';
}
$('reset').addEventListener('click', () => $('reset-dialog').showModal());
$('reset-dialog').addEventListener('close', async () => {
  if ($('reset-dialog').returnValue !== 'confirm' || state.busy) return;
  state.busy = true; controls();
  try {
    const response = await fetch('/demo/reset', { method: 'POST', cache: 'no-store', headers: { Authorization: `Bearer ${state.token}` } });
    if (response.status === 401) {
      clearSessionView();
      notice('演示会话已失效，重置结果尚未确认。请点击「开始演示」重新连接并查询余额。', true);
      return;
    }
    if (!response.ok || (await response.json()).status !== 'COMPLETED') throw new Error();
    clearSessionView();
    notice('演示数据已恢复，旧确认卡已失效。');
  } catch { notice('尚未确认重置结果，请检查连接或会话；当前展示可能已经过期。', true); }
  finally { state.busy = false; controls(); }
  if (!state.token) await connect();
});
health();
