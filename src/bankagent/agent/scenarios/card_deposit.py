"""Explicit simulated funding through the existing confirmed lifecycle transaction."""
from bankagent.agent.scenarios import lifecycle
from bankagent.banking import bank_backend as bank

SCENARIO = 'card_deposit'
INTENTS = {'CARD_DEPOSIT': dict(keywords=['模拟入金'], slots={
    'card_name': r'为「([^」]+)」', 'amount': r'模拟入金\s*([0-9]+(?:\.[0-9]+)?)\s*元'},
    required=['card_name', 'amount'], operation='SIMULATE_CARD_DEPOSIT', effect='WRITE', risk='YELLOW')}
CLARIFY_LABELS = {'card_name': '本人已激活的卡', 'amount': '模拟入金金额（最多10000元）'}
TOOL_DESCRIPTIONS = {'SIMULATE_CARD_DEPOSIT': '仅在用户明确要求添加模拟测试资金时准备；不是实际充值、收入或借款。仅本人已激活卡可入金，每笔最多10000元，确认后执行。开户发卡激活不会自动入金。'}


def resolve(candidates, context):
    params = lifecycle.resolve(candidates, context)
    params.pop('category', None)
    return params


def validate(operation, params):
    return (operation == 'SIMULATE_CARD_DEPOSIT' and set(params) == {'card_id', 'amount_minor'}
        and isinstance(params['card_id'], str) and bool(params['card_id'])
        and type(params['amount_minor']) is int and 0 < params['amount_minor'] <= 1000000)


def confirmation(*, operation, params, candidate_params, context):
    card = next(c for c in bank.query_cards(context=context)['data']['cards'] if c['card_id'] == params['card_id'])
    return {'display_name': card['display_name'], 'amount_minor': params['amount_minor'], 'currency': 'CNY',
            'notice': '仅添加本地模拟资金，不是真实存款；需卡片已激活。'}


def execute(operation, params, context):
    return bank.simulate_card_deposit(context=context, **params)


def render(reply):
    if reply['status'] != 'COMPLETED':
        if reply['status'] == 'REJECTED':
            return '模拟入金已拒绝或取消，本次未入金。请确认卡片属于当前账户且已激活、未冻结，金额不超过10000元。'
        return '模拟入金结果尚未确认，请核对原操作和余额，不要重新发起入金。'
    data = reply['data']
    return f"已为{data['display_name']}模拟入金{data['amount_minor']//100}.{data['amount_minor']%100:02d}元（非真实存款）。"
