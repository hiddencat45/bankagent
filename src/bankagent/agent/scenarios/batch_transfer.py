"""Atomic batch is a list candidate over the existing transfer service, not a second ledger."""
from bankagent.agent.scenarios import transfer
from bankagent.banking import bank_backend
from bankagent.banking.card_numbers import normalize
from bankagent.banking.bank_types import YELLOW_DAILY_LIMIT_MINOR

SCENARIO = 'batch_transfer'
INTENTS = {
    'BATCH_TRANSFER': dict(keywords=[], slots={'items': r'(?!)'}, required=['items'],
                          operation='BATCH_TRANSFER', effect='WRITE', risk='YELLOW'),
    'BATCH_RECEIPTS': dict(keywords=['批量回执'], slots={}, required=[],
                          operation='QUERY_TRANSFER_BATCHES', effect='READ', risk='GREEN'),
}
CANDIDATE_SCHEMA = {'items': {'type': 'array', 'minItems': 2, 'maxItems': 10, 'items': {
    'type': 'object', 'properties': {'recipient_name': {'type': 'string', 'maxLength': 80},
                                 'amount': {'type': 'string', 'maxLength': 80}},
    'additionalProperties': False}}}
CLARIFY_LABELS = {'items': '转账列表'}
TOOL_DESCRIPTIONS = {'QUERY_TRANSFER_BATCHES': '查询当前账户持久化的批量转账回执，包含完整收款列表、总额、整批提交结果及各项状态；重启后也可核对。'}
TOOL_DESCRIPTIONS['BATCH_TRANSFER'] = '向多张本地模拟卡批量转账，每项recipient_name填写完整卡号字符串，保留金额。姓名不足以确定卡时追问卡号。整批一次确认认证，全有或全无。'


def validate_candidates(args):
    return (isinstance(args, dict) and set(args) == {'items'} and isinstance(args['items'], list)
            and 2 <= len(args['items']) <= 10 and all(isinstance(row, dict)
                and not set(row) - {'recipient_name', 'amount'}
                and all(isinstance(v, str) and len(v) <= 80 for v in row.values()) for row in args['items']))


def resolve(candidates, context):
    if not candidates:
        return {}
    if not validate_candidates(candidates):
        return {'items': []}
    return {'items': [transfer.resolve(row, context) for row in candidates['items']]}


def missing_candidates(candidates, resolved):
    if not validate_candidates(candidates):
        return ['2至10项转账列表']
    missing = []
    for index, row in enumerate(resolved['items'], 1):
        if 'contact_id' not in row:
            missing.append(f'第{index}项可唯一识别的收款人')
        if 'amount_minor' not in row:
            missing.append(f'第{index}项有效金额')
    return missing


def validate(operation, params):
    if operation == 'QUERY_TRANSFER_BATCHES':
        return params == {}
    return (operation == 'BATCH_TRANSFER' and set(params) == {'items'}
            and isinstance(params['items'], list) and 2 <= len(params['items']) <= 10
            and all(transfer.validate('TRANSFER', row) for row in params['items']))


def risk(operation, params, context):
    if operation == 'QUERY_TRANSFER_BATCHES':
        return 'GREEN'
    if not validate(operation, params):
        return 'DENY'
    balance = bank_backend.get_balance(context=context)
    if balance['status'] != 'COMPLETED':
        raise ValueError('Cannot evaluate risk')
    total = balance['data']['daily_transfer_total_minor'] + sum(row['amount_minor'] for row in params['items'])
    return 'RED' if total > YELLOW_DAILY_LIMIT_MINOR else 'YELLOW'


def confirmation(*, operation, params, candidate_params, context):
    items = [transfer.confirmation(operation='TRANSFER', params=row, candidate_params=candidate, context=context)
             for row, candidate in zip(params['items'], candidate_params['items'])]
    return {'items': items, 'total_minor': sum(row['amount_minor'] for row in items),
            'currency': 'CNY', 'atomic': True}


def execute(operation, params, context):
    if operation == 'QUERY_TRANSFER_BATCHES':
        return bank_backend.query_transfer_batches(context=context)
    return bank_backend.execute_transfer_batch(context=context, **params)


def rejected_result(params, candidate_params, code):
    return {'operation': 'BATCH_TRANSFER', 'status': 'REJECTED', 'error_code': code,
            'data': {'atomic': True, 'committed': False, 'currency': 'CNY',
                     'items': [{'recipient': ('尾号' + normalize(candidate['recipient_name'])[-4:]) if normalize(candidate.get('recipient_name')) else candidate.get('recipient_name', '未指定'),
                                'amount_minor': row.get('amount_minor', 0),
                                'status': 'NOT_EXECUTED', 'error_code': code}
                               for row, candidate in zip(params.get('items', []), candidate_params.get('items', []))]}}


def render(result):
    if result.get('error_code') in {'SOURCE_CARD_REQUIRED', 'SOURCE_CARD_NOT_ACTIVE'}:
        return '当前没有可付款的已激活借记卡。请先办卡并激活或切换付款卡，整批未执行。'
    if result.get('error_code') == 'SOURCE_CARD_FROZEN':
        return '付款账户的银行卡已冻结，整批转账未执行。请先解冻；模拟认证不能解除冻结。'
    data = result.get('data') or {}
    if result['operation'] == 'QUERY_TRANSFER_BATCHES':
        return '\n\n'.join(render(row) for row in data.get('receipts', [])) or '当前账户没有批量转账回执。'
    if not data:
        return '整批结果尚未确认，请查询批量回执核对，勿重复发起付款。'
    lines = ['整批转账成功。' if data.get('committed') else '整批未提交，全部款项均未扣除。']
    if 'total_minor' in data:
        lines.append('整批合计：' + transfer._money(data['total_minor']) + ' 元')
    if data.get('batch_id'):
        lines.append('批量编号：' + data['batch_id'])
    labels = {'COMPLETED': '成功', 'FAILED': '失败', 'NOT_EXECUTED': '未执行'}
    errors = {'INSUFFICIENT_BALANCE': '余额不足', 'BATCH_ABORTED': '整批未提交',
              'SOURCE_CARD_FROZEN': '付款卡已冻结，请先解冻',
              'USER_CANCELLED': '用户取消', 'REAUTHORIZATION_REQUIRED': '需重新认证',
              'RECIPIENT_ACCOUNT_INVALID': '收款账户不可用', 'CONTACT_NOT_ACCESSIBLE': '收款人不可用'}
    for row in data.get('items', []):
        amount = transfer._money(row['amount_minor'])
        lines.append(f"{row['recipient']}：{amount} 元 — {labels[row['status']]}" +
                     (f"（{errors.get(row['error_code'], row['error_code'])}）" if row.get('error_code') else ''))
        if row.get('transaction_id'):
            lines.append(f"流水：{row['transaction_id']}；转账编号：{row['transfer_id']}")
    return '\n'.join(lines)
