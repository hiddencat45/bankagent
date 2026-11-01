"""Wealth forms and model tools share the trusted backend and confirmation gate."""
import re
from datetime import date, timedelta
from bankagent.banking import bank_backend as bank
from bankagent.banking.wealth import PRODUCTS, OPERATIONS, STATES, ERRORS, NOTICE, PROFILE_FIELDS, validate_profile, business_day, anchored_answers
from bankagent.agent.scenarios.transfer import _to_minor, _money

SCENARIO='wealth'
def declaration(keywords,slots,required,operation,write=False):
    return dict(keywords=keywords,slots=slots,required=required,operation=operation,
                effect='WRITE' if write else 'READ',risk='RED' if operation=='SUBSCRIBE_WEALTH' else 'YELLOW' if write else 'GREEN')

PROFILE_SLOTS={k:rf'{label}[:：]\s*([^，,；;\s]+)' for k,label in dict(budget='预算',free_cash='闲钱',horizon_days='期限',
    purpose='用途',liquidity='到账',loss='亏损',income='收入',debt='负债',experience='经验',priority='偏好').items()}
PROFILE_REQUIRED=list(PROFILE_SLOTS)
PROFILE_SLOTS.update({k:rf'{label}[:：]\s*([^，,；;\s]+)' for k,label in
    dict(need_on='用钱日期',early_redemption='提前赎回',reserve='备用金',impact='生活影响',loss_acceptance='亏损确认').items()})
INTENTS={
    'WEALTH_QUERY':declaration(['查看理财','查询理财','理财产品有哪些'],{},[],'QUERY_WEALTH'),
    'WEALTH_RECOMMEND':declaration(['推荐理财','理财推荐','比较理财'],{},[],'RECOMMEND_WEALTH'),
    'WEALTH_PROFILE':declaration(['保存理财问卷'],PROFILE_SLOTS,PROFILE_REQUIRED,'SAVE_WEALTH_PROFILE',True),
    'WEALTH_BUY':declaration(['模拟申购'],{'product_name':r'模拟申购「([^」]+)」','amount':r'」\s*([0-9]+(?:\.[0-9]+)?)\s*元'},['product_name','amount'],'SUBSCRIBE_WEALTH',True),
    'WEALTH_SELL':declaration(['模拟赎回'],{'product_name':r'模拟赎回「([^」]+)」','units':r'」\s*([0-9]+(?:\.[0-9]+)?)\s*份'},['product_name','units'],'REDEEM_WEALTH',True),
    'WEALTH_CANCEL':declaration(['撤销理财订单'],{'order_id':r'撤销理财订单\s*(W[a-f0-9]{16})'},['order_id'],'CANCEL_WEALTH_ORDER',True),
    'WEALTH_ADVANCE':declaration(['理财演示推进'],{'order_id':r'(W[a-f0-9]{16})',
        'event':r'(下一步|拒单|半数成交|延迟到账|模拟超时)','days':r'推进\s*([0-9]+)\s*天'},[],'ADVANCE_WEALTH_DEMO',True),
}
CLARIFY_LABELS={'product_name':'产品全名、简称或份额代码','amount':'申购金额（元）','units':'赎回份额（份，不能将金额当成份额）',
    'order_id':'当前账户的理财订单编号','budget':'理财总预算（元）','free_cash':'扣除必要支出及备用金后的闲钱（元）',
    'horizon_days':'最早用钱前的天数','purpose':'用途：闲置资金或必要支出','liquidity':'到账要求：可等待、当天到账或固定日期',
    'loss':'亏损态度：不能亏损、仅低风险或接受波动','income':'收入：稳定或不稳定','debt':'负债：无压力、有还款压力或借款理财',
    'experience':'经验：无经验或有经验','priority':'偏好：风险优先、流动性优先或综合比较'}
CLARIFY_LABELS.update(need_on='用钱日期：YYYY-MM-DD',early_redemption='提前赎回：可以、不可以或不确定',
    reserve='备用金：已预留、未预留或不确定',impact='生活影响：会、不会或不确定',loss_acceptance='亏损确认：可以、不可以或不确定')
TOOL_DESCRIPTIONS={
    'QUERY_WEALTH':'查询当前账户真实的模拟理财产品、问卷、持仓、订单事件、可赎回份额、冻结及待到账资金。产品非实时在售。',
    'RECOMMEND_WEALTH':'根据已确认问卷进行确定性初筛。问卷缺失或过期先补问，不能编造收益或正式评级。这里只是模拟候选。',
    'SAVE_WEALTH_PROFILE':'保存用户明确提供的全部需求回答，先逐项补问再提交确认。budget/free_cash为元字符串，horizon_days为天数字符串；其余枚举严格按槽位标签。仅模拟筛选，不是正式风险测评。',
    'SUBSCRIBE_WEALTH':'仅用户明确要求时准备模拟申购，product_name使用查询所得名称或代码，amount为元。提交仅冻结资金，尚未成交。',
    'REDEEM_WEALTH':'准备当前账户模拟赎回；先查可赎回份额，units为份数字符串，不是元。全部赎回必须说明尚未解锁的部分并确认。',
    'CANCEL_WEALTH_ORDER':'撤销当前账户已提交但尚未成交的模拟理财订单，先查询具体order_id。必须确认。',
    'ADVANCE_WEALTH_DEMO':'仅用户明确要求演示控制时使用，绝不为了完成购买自行推进。days为1至31天；或指定order_id与event（下一步/拒单/半数成交/延迟到账/模拟超时），两种方式互斥。下一步可能推进当前账户的模拟日期。',
}
TOOL_DESCRIPTIONS['SAVE_WEALTH_PROFILE'] += ' '+ '；'.join(f'{k}={CLARIFY_LABELS[k]}' for k in PROFILE_SLOTS)


def _snapshot(context):
    r=bank._configured().query_wealth(context=context)
    if r['status']!='COMPLETED': raise PermissionError('ACCOUNT_NOT_ACCESSIBLE')
    return r['data']


def resolve(candidate_params,context):
    c=dict(candidate_params); p={}
    if 'budget' in c:
        p={k:v for k,v in c.items() if k not in {'budget','free_cash','horizon_days'}}
        for key in ('budget','free_cash'):
            v=c.get(key)
            p[key+'_minor']=0 if v in ('0','0.00') else _to_minor(v)
        if not re.fullmatch(r'[0-9]{1,4}',str(c.get('horizon_days',''))): raise ValueError('days')
        p['horizon_days']=int(c['horizon_days'])
        if p.get('need_on'):
            p['horizon_days']=(date.fromisoformat(p['need_on'])-date.fromisoformat(_snapshot(context)['day'])).days
        else:
            p['need_on']=(date.fromisoformat(_snapshot(context)['day'])+timedelta(days=p['horizon_days'])).isoformat()
        return p
    if 'product_name' in c:
        matches=[v for v in PRODUCTS if c['product_name'] in (v['code'],v['name'],v['short_name'])]
        if len(matches)!=1: raise ValueError('product')
        p['product_code']=matches[0]['code']
        p['amount_minor']=_to_minor(c.get('amount',c.get('units')))
        return p
    if 'days' in c:
        if set(c)!={'days'} or not re.fullmatch(r'[0-9]{1,2}',str(c['days'])): raise ValueError('days')
        return dict(days=int(c['days']),expected_day=_snapshot(context)['day'])
    if 'order_id' in c:
        order=next((o for o in _snapshot(context)['orders'] if o['order_id']==c['order_id']),None)
        if not order: raise ValueError('order')
        p=dict(order_id=order['order_id'],version=order['version'])
        if 'event' in c:p['event']=c['event']
        return p
    return c


def validate(operation,p):
    if operation in {'QUERY_WEALTH','RECOMMEND_WEALTH'}:return not p
    if operation=='SAVE_WEALTH_PROFILE':return validate_profile(p)
    if operation in {'SUBSCRIBE_WEALTH','REDEEM_WEALTH'}:
        return set(p)=={'product_code','amount_minor'} and type(p['amount_minor']) is int and 0<p['amount_minor']<=10**10
    if operation=='ADVANCE_WEALTH_DEMO' and set(p)=={'days','expected_day'}:
        return type(p['days']) is int and 1<=p['days']<=31
    required={'order_id','version'} | ({'event'} if operation=='ADVANCE_WEALTH_DEMO' else set())
    return (operation in {'CANCEL_WEALTH_ORDER','ADVANCE_WEALTH_DEMO'} and set(p)==required
        and type(p['version']) is int and p['version']>0
        and (operation=='CANCEL_WEALTH_ORDER' or p['event'] in {'下一步','拒单','半数成交','延迟到账','模拟超时'}))


def execute(operation,params,context):
    b=bank._configured()
    if operation in {'QUERY_WEALTH','RECOMMEND_WEALTH'}:return b.query_wealth(context=context,recommend=operation=='RECOMMEND_WEALTH')
    if operation=='SAVE_WEALTH_PROFILE':return b.save_wealth_profile(context=context,**params)
    if operation in {'SUBSCRIBE_WEALTH','REDEEM_WEALTH'}:
        return b.wealth_order(context=context,side='BUY' if operation=='SUBSCRIBE_WEALTH' else 'SELL',**params)
    if operation=='ADVANCE_WEALTH_DEMO' and 'days' in params:return b.advance_wealth_days(context=context,**params)
    return b.change_wealth_order(context=context,operation=operation,**({'event':'撤单'} if operation=='CANCEL_WEALTH_ORDER' else {}),**params)


def confirmation(*,operation,params,candidate_params,context):
    title={'SAVE_WEALTH_PROFILE':'保存模拟需求问卷','SUBSCRIBE_WEALTH':'模拟申购','REDEEM_WEALTH':'模拟赎回',
           'CANCEL_WEALTH_ORDER':'撤销模拟订单','ADVANCE_WEALTH_DEMO':'演示控制（非真实交易）'}[operation]
    lines=[title]
    if 'product_code' in params:
        p=next(p for p in PRODUCTS if p['code']==params['product_code'])
        day=date.fromisoformat(_snapshot(context)['day'])
        confirmed=business_day(day,1)
        lines += [p['name']+' · '+p['code'],('申购金额：' if operation=='SUBSCRIBE_WEALTH' else '赎回份额：')+_money(params['amount_minor'])+('元' if operation=='SUBSCRIBE_WEALTH' else '份'),
                  f"管理人风险等级R{p['issuer_risk']}；不保本。演示持有期{p['hold_days']}天。",
                  '提交后先冻结资金或锁定份额；不等于成交或到账。']
        if operation=='SUBSCRIBE_WEALTH':
            lines.append(f"模拟确认日：{confirmed}；模拟最早可赎回日：{business_day(confirmed+timedelta(days=p['hold_days']))}。需手动演示推进。")
        else:
            lines.append(f"模拟确认日：{confirmed}；模拟到账日：{business_day(confirmed,2)}。需手动演示推进，非银行到账承诺。")
    elif operation=='SAVE_WEALTH_PROFILE':
        deadline=params.get('need_on') or (date.fromisoformat(_snapshot(context)['day'])+timedelta(days=params['horizon_days'])).isoformat()
        lines += [f"计划投入：{_money(params['budget_minor'])}元；已确认可用闲钱：{_money(params['free_cash_minor'])}元",
                  '用钱日期：'+deadline+'（保存后不随查询后移）',
                  f"用途：{params['purpose']}；到账要求：{params['liquidity']}",
                  f"风险偏好：{params['loss']}；经验：{params['experience']}；比较偏好：{params['priority']}",
                  f"还款与资金来源：{params['debt']}"]
        if params['income']!='不确定':lines.append('收入：'+params['income'])
        for k in ('reserve','impact','early_redemption','loss_acceptance'):
            if k in params:lines.append(CLARIFY_LABELS[k].split('：')[0]+'：'+params[k])
        lines.append('仅模拟需求筛选，非正式风险测评。保存需求不购买产品。')
    elif 'days' in params:lines += [f"从{params['expected_day']}推进当前账户模拟日期{params['days']}天；可能使持仓达到模拟可赎回日期。"]
    else:lines += [f"订单{params['order_id']}，版本{params['version']}，动作{params.get('event','撤单')}",
                  '下一步会处理该订单并可能推进账户演示日期；不会重复下单。']
    return dict(display_name=title,wealth_summary='\n'.join(lines),notice=NOTICE)


def render(result):
    if result['status']!='COMPLETED':
        return '模拟理财未完成：'+ERRORS.get(result.get('error_code'),'请核对原订单和账户；结果未知时不要重复下单。')
    d=result['data']
    if 'order' in d:
        o=d['order']; partial=0<o['filled_minor']<o['requested_minor']
        return (f"模拟订单{o['order_id']}：{STATES[o['state']]}"+('（部分成交）' if partial else '')+
                f"\n申请{_money(o['requested_minor'])}{'元' if o['side']=='BUY' else '份'}；已确认{_money(o['filled_minor'])}份。\n"+o['events'][-1]['message'])
    if result['operation']=='SAVE_WEALTH_PROFILE':return '已保存模拟需求问卷。可继续推荐理财；这不是银行正式风险测评，也未购买产品。'
    if result['operation']=='ADVANCE_WEALTH_DEMO':return '账户模拟日期已推进至'+d['day']+'；尚未自动提交或确认任何订单。'
    lines=[f"模拟日期{d['day']}；可用现金{_money(d['available_minor'])}元，申购冻结{_money(d['frozen_minor'])}元，持仓{_money(d['holdings_minor'])}元，待到账{_money(d['waiting_minor'])}元。"]
    if not d['profile_valid']:lines.append('请先填写或更新模拟需求问卷，不能根据流水推断正式风险等级。')
    else:
        a=anchored_answers(d['profile'])
        lines.append(f"已确认需求：总预算{_money(a['budget_minor'])}元，扣除必要支出和备用金后的闲钱{_money(a['free_cash_minor'])}元，期限{a['horizon_days']}天；"+
                     '、'.join(a[k] for k in ('purpose','liquidity','loss','income','debt','experience','priority'))+'。')
        lines.append('用钱日期：'+a['need_on']+'；按当前模拟日期计算剩余时间。')
    for p in d['products']:
        r=next((r for r in d['recommendations'] if r['product_code']==p['code']),None)
        if r and r.get('recommendation_rank'):
            lines.append(f"推荐{r['recommendation_rank']}：{p['short_name']}；"+'；'.join(r['recommendation_reasons'])+'；需要权衡：'+'；'.join(r['tradeoffs']))
        lines.append(p['short_name']+'（'+p['code']+'）'+('：'+r.get('comparison_group', '模拟候选' if r['eligible'] else '不匹配')+'；'+'；'.join(r['reasons']) if r else '：资料可查看，尚未筛选')+
                     f"。管理人R{p['issuer_risk']}，{_money(p['minimum_minor'])}元起，"+(f"最低持有{p['hold_days']}天" if p['hold_days'] else '无封闭期')+'；'+p['fee']+'。')
    if d['profile_valid']:
        lines.append(f"共{len(d['products'])}款真实产品资料，{sum(r['eligible'] for r in d['recommendations'])}款通过模拟初筛，优先推荐{sum(bool(r.get('recommendation_rank')) for r in d['recommendations'])}款。各产品持有期不同，均不保本；过往收益统计口径不同，不做收益排名。")
    for lot in d['lots']:lines.append(f"持仓{lot['lot_id']}：{lot['product_code']}，共{_money(lot['units_minor'])}份，可赎回{_money(lot['redeemable_minor'])}份，解锁日{lot['unlock_on']}。")
    for o in d['orders'][:10]:lines.append(f"订单{o['order_id']}：{STATES[o['state']]}，申请{_money(o['requested_minor'])}{'元' if o['side']=='BUY' else '份'}。")
    return '\n'.join(lines)
