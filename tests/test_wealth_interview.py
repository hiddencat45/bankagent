"""Conversational needs are drafts; confirmation, eligibility and account scope remain trusted."""
from copy import deepcopy
from datetime import date,timedelta
import pytest
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from bankagent.agent import wealth_interview as interview
from bankagent.banking.wealth import PRODUCTS,screen,anchored_answers,recommend_products
from test_wealth import ANSWERS,FIELDS,confirm,tools,setup,NOW
from test_query_loop import Scripted,call,CLOCK
from test_api_http import login,chat
from test_bank_forms import form

DAY=date(2026,10,18)
COMPLETE=dict(budget='10000',reserve='已预留',debt='无压力',liquidity='固定日期',need_on='2027-10-18',
    early_redemption='可以',loss='仅低风险',loss_acceptance='可以',experience='无经验',impact='不会',priority='风险优先')


def test_interview_preserves_answers_and_asks_only_missing_fields():
    d=interview.update({},dict(budget='10000',horizon_days='365'),DAY)
    q,fields=interview.next_step(d,DAY)
    assert '备用金' in q and fields is None and d['budget']=='10000'
    d=interview.update(d,COMPLETE,DAY)
    _,fields=interview.next_step(d,DAY)
    assert fields['budget']=='10000' and fields['need_on']=='2027-10-18'
    assert fields['free_cash']=='10000' and fields['income']=='不确定'
    changed=interview.update(d,{'budget':'5000','priority':'流动性优先'},DAY)
    _,new=interview.next_step(changed,DAY)
    assert new['budget']==new['free_cash']=='5000' and new['need_on']==fields['need_on']
    assert d['budget']=='10000'


def test_explicit_date_without_redundant_model_enum_does_not_repeat_time_question():
    d=interview.update({'budget':'10000','reserve':'已预留','debt':'无压力'},
                       {'need_on':'2027-11-01','early_redemption':'可以'},DAY)
    assert d['liquidity']=='固定日期'
    assert '接受本金亏损' in interview.next_step(d,DAY)[0]


def test_increasing_budget_reconfirms_reserves_and_impact():
    d=interview.update(COMPLETE,{'budget':'100000'},DAY)
    assert 'reserve' not in d and 'impact' not in d
    assert '备用金' in interview.next_step(d,DAY)[0]


@pytest.mark.parametrize('patch',[{'budget':'nan'},{'budget':'-1'},{'need_on':'2026-02-30'},
    {'need_on':'2026-01-01'},{'horizon_days':'0'},{'risk_level':'R2'},{'loss':'保本高收益'}])
def test_invalid_model_patch_does_not_change_draft(patch):
    d={'budget':'1234'}
    with pytest.raises(ValueError):interview.update(d,patch,DAY)
    assert d=={'budget':'1234'}


def test_early_stop_and_uncertainty_do_not_generate_complete_profile():
    for patch in ({'loss':'不能亏损'},{'debt':'借款理财'},{'impact':'会'},
                  {'reserve':'不确定'},{'loss':'不确定'},{'early_redemption':'不可以'}):
        q,fields=interview.next_step({**COMPLETE,**patch},DAY)
        assert q and fields is None
    low_only={k:v for k,v in COMPLETE.items() if k!='loss_acceptance'}
    assert '低风险也不保本' in interview.next_step(low_only,DAY)[0]


def test_legacy_fixed_date_is_followup_not_automatic_rejection_or_silent_migration():
    old=dict(answers={**ANSWERS,'liquidity':'固定日期','loss':'仅低风险','experience':'无经验','horizon_days':365},
             recorded_at='2026-10-18T12:00:00+08:00')
    original=deepcopy(old);d=interview.seed(old)
    assert 'need_on' not in d and d['budget']=='20000'
    assert '具体哪一天' in interview.next_step(d,DAY)[0]
    r=recommend_products(anchored_answers(old),DAY)
    assert sum(x['match_status']=='review' for x in r)==2
    assert sum(x['match_status']=='excluded' for x in r)==8
    assert not any(x['eligible'] for x in r)
    assert old==original


def test_explicit_date_and_early_redemption_can_match_cash_but_not_365_days():
    a={**ANSWERS,'horizon_days':365,'need_on':'2027-10-18','early_redemption':'可以',
       'liquidity':'固定日期','loss':'仅低风险','loss_acceptance':'可以','experience':'无经验'}
    assert screen(PRODUCTS[0],a,DAY)['eligible']
    assert screen(PRODUCTS[3],a,DAY)['eligible']
    assert screen(PRODUCTS[-1],a,DAY)['match_status']=='excluded'
    assert any('期限不足' in s for s in screen(PRODUCTS[-1],a,DAY)['reasons'])


def test_deadline_stays_fixed_after_clock_advances_and_purchase_rechecks(setup):
    _,_,write,query,_=tools(setup)
    initial=query();deadline=initial['needs_deadline']
    write('ADVANCE_WEALTH_DEMO',dict(days=31,expected_day=initial['day']))
    later=query()
    assert later['needs_deadline']==deadline
    assert later['recommendations'][0]['remaining_days']==initial['recommendations'][0]['remaining_days']-31
    write('SAVE_WEALTH_PROFILE',{**ANSWERS,'need_on':later['day'],'liquidity':'可等待'})
    assert write('SUBSCRIBE_WEALTH',dict(product_code=PRODUCTS[0]['code'],amount_minor=100))['error_code']=='WEALTH_NOT_MATCHED'
    assert query()['orders']==[]


def test_preferences_change_comparison_groups_not_purchase_eligibility():
    risk=recommend_products({**ANSWERS,'priority':'风险优先'},DAY)
    comprehensive=recommend_products({**ANSWERS,'priority':'综合比较'},DAY)
    liquid=recommend_products({**ANSWERS,'priority':'流动性优先'},DAY)
    codes=lambda rows:{r['product_code'] for r in rows if r['eligible']}
    preferred=lambda rows:{r['product_code'] for r in rows if r['comparison_group']=='优先比较'}
    assert codes(risk)==codes(comprehensive)==codes(liquid)
    assert preferred(risk)!=preferred(comprehensive)
    assert all('最低持有期' in r['preference_reason'] for r in liquid)
    assert any(r['eligible'] and r['comparison_group']=='其他备选' for r in risk)


def test_model_multiturn_modify_confirm_then_recommend_without_order(tmp_path):
    model=Scripted(call('update_wealth_needs',{'answers':{'budget':'10000'}},'a1'),
        call('update_wealth_needs',{'answers':{k:v for k,v in COMPLETE.items() if k!='budget'}},'a2'),
        call('update_wealth_needs',{'answers':{'budget':'5000'}},'a3'))
    with TestClient(create_app(demo=True,clock=CLOCK,database_path=tmp_path/'interview.sqlite3',query_model=model),base_url='http://localhost') as c:
        auth=login(c)
        out=chat(c,auth,message='想拿一万元理财');thread=out[0][1]['thread_id']
        assert out[-1][1]['status']=='NEEDS_CLARIFICATION' and '备用金' in str(out)
        assert c.get('/bank/wealth',headers=auth).json()['data']['profile'] is None
        pending=chat(c,auth,thread_id=thread,message='已留备用金，无借款还款压力，明年10月18日用，可提前赎回，可接受小幅亏损但仅低风险，无经验，不影响生活，风险优先')
        assert pending[-1][1]['status']=='AWAITING_CONFIRMATION'
        changed=chat(c,auth,thread_id=thread,message='金额改成五千')
        assert changed[-1][1]['status']=='AWAITING_CONFIRMATION'
        assert '5000.00' in str(changed)
        assert c.get('/bank/wealth',headers=auth).json()['data']['profile'] is None
        old=next(v for e,v in pending if e=='interrupt')
        stale=c.post('/agent/chat',headers=auth,json={'thread_id':thread,
            'resume':{'challenge_id':old['challenge_id'],'decision':'approve'}})
        assert stale.status_code==409
        done=confirm(c,auth,changed)
        receipts=[v['payload'] for e,v in done if e=='card' and v['type']=='result']
        assert [r['operation'] for r in receipts]==['SAVE_WEALTH_PROFILE','RECOMMEND_WEALTH']
        data=c.get('/bank/wealth',headers=auth).json()['data']
        assert data['profile']['answers']['budget_minor']==500000
        assert data['needs_deadline']=='2027-10-18'
        assert sum(r['eligible'] for r in data['recommendations'])==2
        assert data['orders']==[] and data['available_minor']==500000 and data['frozen_minor']==0


def test_cancel_discards_draft_and_restart_does_not_reuse_old_answers(tmp_path):
    model=Scripted(call('update_wealth_needs',{'answers':{'budget':'10000'}},'b1'),call('cancel_task',{},'b2'),
        call('update_wealth_needs',{'answers':{}},'b3'))
    with TestClient(create_app(demo=True,clock=CLOCK,database_path=tmp_path/'cancel.sqlite3',query_model=model),base_url='http://localhost') as c:
        auth=login(c);out=chat(c,auth,message='一万元理财');thread=out[0][1]['thread_id']
        cancelled=chat(c,auth,thread_id=thread,message='取消')
        assert cancelled[-1][1]['status']=='REJECTED'
        again=chat(c,auth,thread_id=thread,message='重新了解理财需求')
        assert '计划拿多少钱' in str(again)
        assert c.get('/bank/wealth',headers=auth).json()['data']['profile'] is None


def test_form_explicit_date_is_preserved_and_review_not_buyable(tmp_path):
    with TestClient(create_app(demo=True,clock=CLOCK,database_path=tmp_path/'form.sqlite3'),base_url='http://localhost') as c:
        auth=login(c)
        pending=form(c,auth,'SAVE_WEALTH_PROFILE',**{**FIELDS,'need_on':'2027-10-18','liquidity':'固定日期'})
        confirm(c,auth,pending)
        data=c.get('/bank/wealth',headers=auth).json()['data']
        assert data['needs_deadline']=='2027-10-18' and any(r['match_status']=='review' for r in data['recommendations'])
        buy=form(c,auth,'SUBSCRIBE_WEALTH',product_name=PRODUCTS[0]['code'],amount='100')
        if buy[-1][1]['status'] in {'AWAITING_AUTHENTICATION','AWAITING_CONFIRMATION'}:buy=confirm(c,auth,buy)
        assert 'WEALTH_NOT_MATCHED' in str(buy)
        assert c.get('/bank/wealth',headers=auth).json()['data']['orders']==[]
