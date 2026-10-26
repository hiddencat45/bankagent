const object = value => value && typeof value === 'object' && !Array.isArray(value);
const text = value => typeof value === 'string' && value.trim().length > 0;
const minor = value => Number.isSafeInteger(value) && value >= 0;
const invalid = () => { throw new Error('服务返回的业务信息不完整，已停止展示或确认。'); };

export function money(value) {
  if (!minor(value)) invalid();
  const amount = BigInt(value);
  const yuan = (amount / 100n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return `${yuan}.${(amount % 100n).toString().padStart(2, '0')}`;
}

export function readConfirmation(value) {
  if (!object(value) || !['YELLOW', 'RED'].includes(value.risk_level) || !text(value.challenge_id)
      || !text(value.operation_hash) || !text(value.expires_at)
      || !Number.isFinite(Date.parse(value.expires_at))) invalid();
  let fields;
  if (value.operation === 'TRANSFER') {
    if (!text(value.recipient) || !minor(value.amount_minor) || value.amount_minor === 0
        || value.currency !== 'CNY') invalid();
    fields = ['recipient', 'amount_minor', 'currency'];
  } else if (['FREEZE_CARD', 'UNFREEZE_CARD'].includes(value.operation)) {
    const target = value.operation === 'FREEZE_CARD' ? 'FROZEN' : 'ACTIVE';
    if (!text(value.display_name) || !['ACTIVE', 'FROZEN'].includes(value.current_status)
        || value.target_status !== target) invalid();
    fields = ['display_name', 'current_status', 'target_status'];
  } else invalid();
  const keys = ['operation', ...fields, 'risk_level', 'challenge_id', 'operation_hash', 'expires_at'];
  return Object.fromEntries(keys.map(key => [key, value[key]]));
}

export function confirmationReady(card, signal, phase, challengeId = card?.challenge_id) {
  if (!card || !signal || card.challenge_id !== signal.challenge_id
      || card.challenge_id !== challengeId
      || card.operation_hash !== signal.operation_hash) return false;
  return card.risk_level === 'YELLOW'
    ? phase === 'AWAITING_CONFIRMATION' && signal.kind === 'CONFIRMATION'
    : card.risk_level === 'RED' && phase === 'AWAITING_AUTHENTICATION' && signal.kind === 'STRONG_AUTH';
}

export function readBills(data) {
  if (!object(data) || data.currency !== 'CNY' || !minor(data.total_minor)
      || !text(data.start) || !text(data.end) || !object(data.by_category)
      || !Array.isArray(data.transactions) || data.transactions.length > 100
      || !Array.isArray(data.anomalies)) invalid();
  if (data.filters !== undefined) {
    if (!object(data.filters)
        || !['category', 'merchant'].every(key => data.filters[key] === null || text(data.filters[key]))
        || !(data.filters.amount_gt_minor === null || minor(data.filters.amount_gt_minor))) invalid();
  }
  const ids = new Set();
  let total = 0n;
  for (const value of Object.values(data.by_category)) {
    if (!minor(value)) invalid();
    total += BigInt(value);
  }
  if (total !== BigInt(data.total_minor)) invalid();
  for (const row of data.transactions) {
    if (!object(row) || !text(row.transaction_id) || ids.has(row.transaction_id)
        || !minor(row.amount_minor) || !text(row.occurred_at) || !text(row.category)
        || !['INCOME', 'EXPENSE', 'TRANSFER_OUT'].includes(row.kind)
        || (row.merchant !== null && !text(row.merchant))) invalid();
    ids.add(row.transaction_id);
  }
  for (const anomaly of data.anomalies) {
    if (!object(anomaly) || anomaly.type !== 'POSSIBLE_DUPLICATE'
        || !Array.isArray(anomaly.evidence) || new Set(anomaly.evidence).size < 2
        || anomaly.evidence.some(id => !ids.has(id))) invalid();
  }
  return data;
}

export function readResult(result) {
  if (!object(result) || typeof result.operation !== 'string'
      || !['COMPLETED', 'REJECTED', 'FAILED', 'PENDING'].includes(result.status)) invalid();
  if (result.status !== 'COMPLETED') {
    if (!text(result.error_code)) invalid();
    return result;
  }
  if (!text(result.operation) || result.error_code !== null || !object(result.data)) invalid();
  const data = result.data;
  if (result.operation === 'GET_BALANCE') {
    if (!minor(data.balance_minor) || data.currency !== 'CNY') invalid();
  } else if (result.operation === 'TRANSFER') {
    if (!minor(data.amount_minor) || !data.amount_minor || !minor(data.remaining_balance_minor)
        || data.currency !== 'CNY' || !text(data.recipient) || !text(data.transaction_id)) invalid();
  } else if (result.operation === 'QUERY_CARDS') {
    if (!Array.isArray(data.cards)) invalid();
    const ids = new Set();
    for (const card of data.cards) {
      readCard(card);
      if (ids.has(card.card_id)) invalid();
      ids.add(card.card_id);
    }
  } else if (['FREEZE_CARD', 'UNFREEZE_CARD'].includes(result.operation)) {
    readCard(data);
    const target = result.operation === 'FREEZE_CARD' ? 'FROZEN' : 'ACTIVE';
    if (data.status !== target || !['ACTIVE', 'FROZEN'].includes(data.previous_status)
        || typeof data.changed !== 'boolean'
        || data.changed !== (data.previous_status !== data.status)) invalid();
  } else if (result.operation === 'QUERY_BILLS') readBills(data);
  else invalid();
  return result;
}

function readCard(value) {
  if (!object(value) || !text(value.card_id) || !text(value.display_name)
      || !['PENDING_ACTIVATION', 'ACTIVE', 'FROZEN'].includes(value.status)) invalid();
}
