"""One confirmed transaction creates a fictional customer and their first account."""
from bankagent.banking import bank_backend as bank

SCENARIO = 'onboarding'
INTENTS = {'DEMO_CUSTOMER_CREATE': dict(keywords=['创建演示客户'],
    slots={'customer_name': r'创建演示客户「([^」]+)」', 'account_name': r'首账户「([^」]+)」'},
    required=['customer_name', 'account_name'], operation='CREATE_DEMO_CUSTOMER', effect='WRITE', risk='YELLOW')}
CLARIFY_LABELS = {'customer_name': '虚构客户名称', 'account_name': '首次开户名称'}


def resolve(candidate_params, context):
    return dict(candidate_params)


def validate(operation, params):
    return (operation == 'CREATE_DEMO_CUSTOMER' and set(params) == {'customer_name', 'account_name'}
            and all(isinstance(v, str) and bool(v.strip()) and len(v) <= 80 for v in params.values()))


def confirmation(*, operation, params, candidate_params, context):
    return {'display_name': params['customer_name'], 'account_name': params['account_name'],
            'opening_credit_minor': 100000, 'currency': 'CNY'}


def execute(operation, params, context):
    return bank.create_demo_customer(context=context, **params)


def render(result):
    if result['status'] != 'COMPLETED':
        return ('此入口未开放创建演示客户，本次没有创建客户或账户。'
                if result.get('error_code') == 'DEMO_CREATION_DISABLED' else '创建未完成，请核对结果后重试原确认操作。')
    data = result['data']
    return (f"已创建虚构客户“{data['customer_name']}”及首账户“{data['display_name']}”，"
            '已记入1,000.00元演示资金。请在演示客户列表切换，再申请并激活借记卡。')
