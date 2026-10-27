"""Lifecycle candidates use the existing authorization graph, never direct writes."""
from bankagent.agent.scenarios.transfer import _to_minor
from bankagent.banking import bank_backend as bank

SCENARIO = 'lifecycle'
INTENTS = {
    'ACCOUNT_OPEN': dict(keywords=['开户', '开立账户'],
        slots={'display_name': r'(?:开户|开立账户)\s*「([^」]+)」'}, required=['display_name'],
        operation='OPEN_ACCOUNT', effect='WRITE', risk='YELLOW'),
    'DEBIT_ISSUE': dict(keywords=['办理借记卡', '申请借记卡'],
        slots={'display_name': r'(?:办理|申请)借记卡\s*「([^」]+)」'}, required=['display_name'],
        operation='ISSUE_DEBIT_CARD', effect='WRITE', risk='YELLOW'),
    'DEBIT_ACTIVATE': dict(keywords=['激活'], slots={'card_name': r'激活\s*「([^」]+)」'},
        required=['card_name'], operation='ACTIVATE_DEBIT_CARD', effect='WRITE', risk='YELLOW'),
    'CARD_PAYMENT': dict(keywords=['刷卡', '刷卡支付'], slots={
        'card_name': r'使用\s*「([^」]+)」', 'merchant': r'商户\s*「([^」]+)」',
        'amount': r'刷卡(?:支付)?\s*([0-9]+(?:\.[0-9]+)?)\s*元',
        'category': r'分类\s*「([^」]+)」'}, required=['card_name', 'merchant', 'amount'],
        operation='PAY_BY_CARD', effect='WRITE', risk='YELLOW'),
}
CLARIFY_LABELS = {'display_name': '名称（例如：开户「日常账户」）',
    'card_name': '卡片名称（使用「卡名」）', 'merchant': '商户名称', 'amount': '支付金额'}
LABELS = {'OPEN_ACCOUNT': '开立模拟账户', 'ISSUE_DEBIT_CARD': '办理借记卡',
          'ACTIVATE_DEBIT_CARD': '激活借记卡', 'PAY_BY_CARD': '模拟消费'}
TOOL_DESCRIPTIONS = {'ISSUE_DEBIT_CARD': '为当前无卡账户申请唯一普通借记卡。先查询卡片；已有卡时告知用户先开户并在页面切换账户，不能再发共享余额卡。',
                    'OPEN_ACCOUNT': '新开独立账户，确认后有1000元演示入账；需用户在页面切换后才可为此账户发卡。'}


def resolve(candidate_params, context):
    params = {}
    if set(candidate_params) - {'display_name', 'card_name', 'merchant', 'amount', 'category'}:
        raise ValueError('unexpected candidate fields')
    for key in ('display_name', 'merchant'):
        if key in candidate_params:
            if (not isinstance(candidate_params[key], str) or not candidate_params[key].strip()
                    or len(candidate_params[key]) > 80):
                raise ValueError('invalid name')
            params[key] = candidate_params[key]
    if 'card_name' in candidate_params:
        cards = bank.query_cards(context=context)
        if cards['status'] != 'COMPLETED':
            raise PermissionError('ACCOUNT_NOT_ACCESSIBLE')
        matches = [c for c in cards['data']['cards'] if c['display_name'] == candidate_params['card_name']]
        if len(matches) != 1:
            raise ValueError('card name must identify exactly one owned card')
        params['card_id'] = matches[0]['card_id']
    if 'amount' in candidate_params or 'merchant' in candidate_params:
        params['amount_minor'] = _to_minor(candidate_params.get('amount'))
        params['category'] = candidate_params.get('category', '其他')
        if 'amount' in candidate_params and params['amount_minor'] is None:
            raise ValueError('invalid amount')
        if not isinstance(params['category'], str) or params['category'] not in {'餐饮', '交通', '购物', '居住', '其他'}:
            raise ValueError('invalid category')
    return params


def validate(operation, params):
    text = lambda v: isinstance(v, str) and bool(v.strip()) and len(v) <= 80
    if operation in {'OPEN_ACCOUNT', 'ISSUE_DEBIT_CARD'}:
        return set(params) == {'display_name'} and text(params['display_name'])
    if operation == 'ACTIVATE_DEBIT_CARD':
        return set(params) == {'card_id'} and text(params['card_id'])
    return (operation == 'PAY_BY_CARD' and set(params) == {'card_id', 'amount_minor', 'merchant', 'category'}
        and text(params['card_id']) and text(params['merchant'])
        and type(params['amount_minor']) is int and params['amount_minor'] > 0
        and isinstance(params['category'], str) and params['category'] in {'餐饮', '交通', '购物', '居住', '其他'})


def confirmation(*, operation, params, candidate_params, context):
    details = {'action_label': LABELS[operation]}
    if 'display_name' in params:
        details['display_name'] = params['display_name']
    else:
        cards = bank.query_cards(context=context)
        card = next(c for c in cards['data']['cards'] if c['card_id'] == params['card_id'])
        details['display_name'] = card['display_name']
    if operation == 'OPEN_ACCOUNT':
        details.update(opening_credit_minor=100000, currency='CNY')
    if operation == 'ISSUE_DEBIT_CARD':
        details['account_policy'] = '当前账户仅允许一张普通卡；已有卡请先开户并切换。余额属于该独立账户，不复制其他账户资金。'
    if operation == 'PAY_BY_CARD':
        details.update({k: params[k] for k in ('amount_minor', 'merchant', 'category')})
        details['currency'] = 'CNY'
    return details


def execute(operation, params, context):
    methods = {'OPEN_ACCOUNT': bank.open_account, 'ISSUE_DEBIT_CARD': bank.issue_debit_card,
               'ACTIVATE_DEBIT_CARD': bank.activate_debit_card, 'PAY_BY_CARD': bank.pay_by_card}
    return methods[operation](context=context, **params)


def render(result):
    if result['status'] != 'COMPLETED':
        code = result.get('error_code')
        return {'ACCOUNT_ALREADY_HAS_CARD': '当前账户已有普通借记卡。请先开立独立账户、切换到该账户，再申请新卡；不会共享或复制原余额。',
                'CARD_NOT_ACTIVE': '卡片尚未激活或已冻结，本次未扣款。',
                'CARD_SINGLE_LIMIT_EXCEEDED': '超过该卡单笔消费限额，本次未扣款。可以查询或调整消费限额。',
                'CARD_DAILY_LIMIT_EXCEEDED': '超过该卡当日累计消费限额，本次未扣款。可以查询或调整消费限额。',
                'INSUFFICIENT_BALANCE': '账户余额不足，本次未扣款。',
                'CARD_NOT_PENDING_ACTIVATION': '此卡不是待激活状态，本次未变更。'}.get(code, '本次业务未完成，请检查名称、卡片状态和输入信息。')
    data, op = result['data'], result['operation']
    if op == 'OPEN_ACCOUNT':
        return f"模拟账户“{data['display_name']}”已开立，已记入 1,000.00 元演示资金。请在账户列表切换后办理新卡。"
    if op == 'ISSUE_DEBIT_CARD':
        return f"借记卡“{data['display_name']}”已办理，请激活后使用。"
    if op == 'ACTIVATE_DEBIT_CARD':
        return f"借记卡“{data['display_name']}”已激活。"
    amount = data['amount_minor']
    return f"已向“{data['merchant']}”模拟支付 {amount // 100}.{amount % 100:02d} 元。"
