"""Validated conversational drafts. No banking write or model-assigned risk level."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import re

from bankagent.banking.wealth import CHOICES, OPTIONAL_CHOICES, anchored_answers

FIELDS = {'budget','reserve','debt','horizon_days','need_on','liquidity','early_redemption',
          'loss','loss_acceptance','experience','impact','priority'}
SCHEMA = {'answers': {'type':'object','properties':{k:{'type':'string','maxLength':80} for k in sorted(FIELDS)},
                      'additionalProperties':False}, 'restart':{'type':'boolean'}}
DESCRIPTION = '''收集或修改理财需求，保存前必须走本人确认。首次推荐或修改需求先调用本工具，已有问卷由服务端带入，只补问缺项。
answers仅提取用户明确表达的字段，不猜测：budget=元数字字符串；reserve=已预留/未预留/不确定（生活开销、还款、备用金已扣除）；
debt=无压力/有还款压力/借款理财；horizon_days=大致不用钱的天数；need_on=明确用钱日期YYYY-MM-DD；
liquidity=可等待/当天到账/固定日期；early_redemption=可以/不可以/不确定（能否提前赎回）；
loss=不能亏损/仅低风险/接受小幅亏损/接受波动/不确定；loss_acceptance=可以/不可以/不确定（仅低风险仍须明确是否接受本金亏损）；experience=无经验/有经验（了解但没买过属于无经验）；
impact=会/不会/不确定（亏损或延期是否影响生活还款）；priority=风险优先/流动性优先/综合比较。
随时可能用钱不等于必须当天到账，先确认；“稳一点”不等于能接受亏损，需追问。用户强调收益时说明现有口径不能统一排名，询问是否综合比较。
未提供的字段省略，可先用answers={}开始。restart仅在用户明确要求从头重填时true。服务端返回下一问或准备确认，不自行保存或购买。'''


def seed(profile):
    if not profile:return {}
    a=profile['answers'];draft={k:str(v) for k,v in a.items() if k in FIELDS}
    draft['budget']=str(Decimal(a['budget_minor'])/100)
    if a['purpose']=='闲置资金' and a['free_cash_minor']>=a['budget_minor']:
        draft.setdefault('reserve','已预留')
    # A legacy fixed-date answer supplied only a duration, not a confirmed calendar date.
    if a['liquidity']!='固定日期' or a.get('need_on'):
        draft['need_on']=anchored_answers(profile)['need_on']
    return draft


def update(draft,patch,day):
    if not isinstance(patch,dict) or set(patch)-FIELDS:raise ValueError('fields')
    d=deepcopy(draft)
    for k,v in patch.items():
        if not isinstance(v,str) or not v.strip() or len(v)>80:raise ValueError(k)
        if k in CHOICES and v not in CHOICES[k]:raise ValueError(k)
        if k in OPTIONAL_CHOICES and v not in OPTIONAL_CHOICES[k]:raise ValueError(k)
        if k=='budget':
            try:
                if not re.fullmatch(r'[0-9]+(?:\.[0-9]{1,2})?',v) or not 0<Decimal(v)<=10**8:raise ValueError(k)
            except InvalidOperation:raise ValueError(k) from None
        if k=='horizon_days' and (not re.fullmatch(r'[0-9]{1,4}',v) or not 1<=int(v)<=3650):raise ValueError(k)
        if k=='need_on':
            if date.fromisoformat(v).isoformat()!=v or not 1<=(date.fromisoformat(v)-day).days<=3650:raise ValueError(k)
        d[k]=v
    if 'budget' in patch and draft.get('budget') and Decimal(patch['budget'])>Decimal(draft['budget']):
        # A previous cash-reserve answer did not cover a newly increased allocation.
        for key in ('reserve','impact'):
            if key not in patch:d.pop(key,None)
    if 'horizon_days' in patch and 'need_on' not in patch:
        d.pop('need_on',None)
        if 'liquidity' not in patch:d['liquidity']='可等待'
    if 'need_on' in patch and 'liquidity' not in patch:d['liquidity']='固定日期'
    if 'liquidity' in patch and patch['liquidity']!='固定日期':d.pop('early_redemption',None)
    if 'need_on' in patch:d['horizon_days']=str((date.fromisoformat(d['need_on'])-day).days)
    return d


def next_step(d,day):
    # Stop early when the current non-guaranteed catalog cannot serve the stated need.
    if d.get('loss')=='不能亏损' or d.get('loss_acceptance')=='不可以':
        return '你明确不能接受本金亏损，当前10款都是非保本产品，因此不推荐。无需继续填完，也不会保存或购买。可浏览资料，或按实际情况修改需求。',None
    if d.get('debt') in {'借款理财','有还款压力'} or d.get('impact')=='会':
        return '这笔资金涉及借款、还款压力或生活保障，目前不建议纳入这些非保本产品的候选。无需继续填写，不会保存或购买。',None
    questions=[('budget','这次计划拿多少钱理财？可以直接说“一万元”。'),
        ('reserve','这笔钱是否已经扣除了日常开销、近期还款和应急备用金？'),
        ('debt','这笔钱包含借款吗？目前是否有还款压力？'),
        ('liquidity','最早什么时候可能用到这笔钱？有明确日期、大致期限，还是随时可能用？')]
    for key,q in questions:
        if key not in d:return q,None
    if d['reserve']!='已预留':return '请先确认日常开销、还款和备用金。可以修改本次金额；不确定时也可以稍后继续，不必为了推荐选择“已预留”。',None
    if d['liquidity']=='当天到账':return '目前尚不能核实这些产品能否当天到账，不会承诺匹配。若当天到账是必要条件，可以先结束；如实际可以等待，请告诉我最早用钱时间。',None
    if d['liquidity']=='固定日期':
        if 'need_on' not in d:return '具体哪一天需要用钱？请告诉我年月日，避免日期随查询往后移动。',None
        if d.get('early_redemption')!='可以':return '为了赶在用钱日期前到账，是否可以提前办理赎回、预留等待时间？若不可以或不确定，暂不能确认匹配。',None
    if 'need_on' not in d and 'horizon_days' not in d:return '这笔钱最早多久后可能使用？例如30天、半年；有明确日期也可以直接告诉我。',None
    deadline=date.fromisoformat(d['need_on']) if d.get('need_on') else day+timedelta(days=int(d['horizon_days']))
    if deadline<=day:return '原先的用钱日期已经到达，请按实际情况更新日期或期限。',None
    if d.get('loss')=='仅低风险' and d.get('loss_acceptance')!='可以':
        return '低风险也不保本。你能接受本金发生小幅亏损吗？还是本金不能少？',None
    for key,q in [('loss','你能接受本金亏损吗？不能接受、能接受小幅亏损，还是能接受更明显的波动和亏损？不清楚也可以直说。'),
                  ('experience','你了解或购买过非保本理财吗？没有经验也没关系，我会提示需要了解的风险。'),
                  ('impact','如果这笔钱亏损或延期到账，会影响日常生活或还款吗？'),
                  ('priority','这次更在意降低风险、取用灵活，还是比较不同安排后再决定？')]:
        if key not in d or d[key]=='不确定':return q,None
    fields={k:d[k] for k in ('budget','debt','liquidity','loss','experience','priority','reserve','impact')}
    fields.update(free_cash=d['budget'],purpose='闲置资金',income='不确定',
                  horizon_days=str((deadline-day).days),need_on=deadline.isoformat())
    for key in ('early_redemption','loss_acceptance'):
        if key in d:fields[key]=d[key]
    return '',fields


def quick_replies(question):
    """Optional reply text only; clicking never confirms or saves a profile."""
    return {
        '这笔钱是否已经扣除了日常开销、近期还款和应急备用金？': ['已经扣除并预留','还没预留','暂时不确定'],
        '这笔钱包含借款吗？目前是否有还款压力？': ['没有借款，也没有还款压力','有还款压力','包含借款'],
        '低风险也不保本。你能接受本金发生小幅亏损吗？还是本金不能少？': ['可以接受小幅亏损，但仍只考虑低风险','本金不能少','暂时不确定'],
        '你能接受本金亏损吗？不能接受、能接受小幅亏损，还是能接受更明显的波动和亏损？不清楚也可以直说。': ['不能接受本金亏损','能接受小幅亏损','暂时不清楚'],
        '你了解或购买过非保本理财吗？没有经验也没关系，我会提示需要了解的风险。': ['尚不了解，也没买过','了解但没买过','买过非保本理财'],
        '如果这笔钱亏损或延期到账，会影响日常生活或还款吗？': ['不会影响生活或还款','会影响','暂时不确定'],
        '这次更在意降低风险、取用灵活，还是比较不同安排后再决定？': ['尽量降低风险','取用灵活','比较不同安排后再决定'],
        '为了赶在用钱日期前到账，是否可以提前办理赎回、预留等待时间？若不可以或不确定，暂不能确认匹配。': ['可以提前赎回','不能提前赎回','想先了解赎回规则'],
    }.get(question,[])
