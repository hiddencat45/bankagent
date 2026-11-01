"""Structured form input is untrusted; only registered actions/slots may enter resolution."""
from bankagent.api.contracts import ApiError
from bankagent.agent.scenarios import ScenarioError

FORM_ACTIONS = {
    'QUERY_WEALTH': ('wealth', 'WEALTH_QUERY'),
    'RECOMMEND_WEALTH': ('wealth', 'WEALTH_RECOMMEND'),
    'SAVE_WEALTH_PROFILE': ('wealth', 'WEALTH_PROFILE'),
    'SUBSCRIBE_WEALTH': ('wealth', 'WEALTH_BUY'),
    'REDEEM_WEALTH': ('wealth', 'WEALTH_SELL'),
    'CANCEL_WEALTH_ORDER': ('wealth', 'WEALTH_CANCEL'),
    'ADVANCE_WEALTH_DEMO': ('wealth', 'WEALTH_ADVANCE'),
    'SIMULATE_CARD_DEPOSIT': ('card_deposit', 'CARD_DEPOSIT'),
    'CREATE_DEMO_CUSTOMER': ('onboarding', 'DEMO_CUSTOMER_CREATE'),
    'OPEN_ACCOUNT': ('lifecycle', 'ACCOUNT_OPEN'),
    'ISSUE_DEBIT_CARD': ('lifecycle', 'DEBIT_ISSUE'),
    'ACTIVATE_DEBIT_CARD': ('lifecycle', 'DEBIT_ACTIVATE'),
    'PAY_BY_CARD': ('lifecycle', 'CARD_PAYMENT'),
    'FREEZE_CARD': ('card', 'CARD_FREEZE'),
    'UNFREEZE_CARD': ('card', 'CARD_UNFREEZE'),
    'SET_CARD_LIMITS': ('payment_limits', 'LIMITS_SET'),
    'QUERY_CARD_LIMITS': ('payment_limits', 'LIMITS_QUERY'),
    'TRANSFER': ('transfer', 'TRANSFER'),
}


def parse_form(payload, registry):
    def invalid():
        raise ApiError('INVALID_REQUEST', '表单操作或字段不合法，请核对输入。', 400)
    if not isinstance(payload, dict) or set(payload) != {'action', 'fields'}:
        invalid()
    action, fields = payload['action'], payload['fields']
    if not isinstance(action, str) or action not in FORM_ACTIONS or not isinstance(fields, dict):
        invalid()
    scenario, intent = FORM_ACTIONS[action]
    try:
        declaration = registry.get(scenario).intents[intent]
    except (ScenarioError, KeyError):
        invalid()
    if (declaration['operation'] != action or set(fields) - set(declaration['slots'])
            or set(declaration['required']) - set(fields)
            or any(not isinstance(v, str) or not v.strip() or len(v) > 80 for v in fields.values())):
        invalid()
    return {'scenario': scenario, 'intent': intent,
            'candidate_params': {key: value.strip() for key, value in fields.items()}}
