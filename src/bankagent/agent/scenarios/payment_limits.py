"""Per-card payment controls; account transfers do not consume card limits."""
import re
from bankagent.agent.scenarios.card import resolve as resolve_card
from bankagent.agent.scenarios.transfer import _to_minor, _money
from bankagent.banking import bank_backend as bank

SCENARIO = 'payment_limits'
INTENTS = {
    'LIMITS_QUERY': dict(keywords=['查询限额', '查看限额'],
        slots={'card_name': r'(?:查询|查看)限额「([^」]+)」'}, required=['card_name'],
        operation='QUERY_CARD_LIMITS', effect='READ', risk='GREEN'),
    'LIMITS_SET': dict(keywords=['设置限额'], slots={'card_name': r'设置限额「([^」]+)」',
        'single_limit': r'单笔\s*([0-9]+(?:\.[0-9]+)?)元',
        'daily_limit': r'每日\s*([0-9]+(?:\.[0-9]+)?)元'},
        required=['card_name', 'single_limit', 'daily_limit'],
        operation='SET_CARD_LIMITS', effect='WRITE', risk='YELLOW'),
}
CLARIFY_LABELS = {'card_name': '卡片名称', 'card_id': '唯一匹配的本人卡片',
                  'single_limit': '单笔限额（元）', 'daily_limit': '每日限额（元）'}


def resolve(candidate_params, context):
    params = resolve_card(candidate_params, context)
    for key in ('single_limit', 'daily_limit'):
        if key in candidate_params:
            value = candidate_params[key]
            zero = (type(value) is int and value == 0) or (
                isinstance(value, str) and re.fullmatch(r'0(?:\.0{1,2})?', value))
            minor = 0 if zero else _to_minor(value)
            if minor is None:
                raise ValueError('invalid limit amount')
            params[key + '_minor'] = minor
    return params


def validate(operation, params):
    if not isinstance(params.get('card_id'), str) or not params['card_id']:
        return False
    if operation == 'QUERY_CARD_LIMITS':
        return set(params) == {'card_id'}
    return (operation == 'SET_CARD_LIMITS' and set(params) == {'card_id', 'single_limit_minor', 'daily_limit_minor'}
        and type(params['single_limit_minor']) is int and type(params['daily_limit_minor']) is int
        and 0 <= params['single_limit_minor'] <= params['daily_limit_minor'] <= 100000000)


def execute(operation, params, context):
    method = bank.query_card_limits if operation == 'QUERY_CARD_LIMITS' else bank.set_card_limits
    return method(context=context, **params)


def confirmation(*, operation, params, candidate_params, context):
    data = bank.query_card_limits(context=context, card_id=params['card_id'])['data']
    return {'display_name': data['display_name'], 'currency': 'CNY',
            'single_limit_minor': params['single_limit_minor'], 'daily_limit_minor': params['daily_limit_minor']}


def render(result):
    if result['status'] != 'COMPLETED':
        return '限额操作未完成，请检查卡片和金额。'
    data = result['data']
    text = f"{data['display_name']}：单笔限额 {_money(data['single_limit_minor'])} 元，每日限额 {_money(data['daily_limit_minor'])} 元。"
    if result['operation'] == 'QUERY_CARD_LIMITS':
        text += f"业务日期 {data['business_date']}，今日该卡已消费 {_money(data['used_today_minor'])} 元。"
    else:
        text += '已保存；不影响账户转账，零限额会拒绝新的卡支付。'
    return text
