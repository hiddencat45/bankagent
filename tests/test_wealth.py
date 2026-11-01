"""Real SQLite sandbox accounting, isolation, concurrency and confirmed API paths."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from bankagent.banking.bank_types import TrustedContext
from bankagent.banking.wealth import screen, PRODUCTS
from test_account_lifecycle import setup, NOW
from test_api_http import result, login, chat, decision
from test_bank_forms import form


def confirm(client, auth, frames, choice='approve'):
    signal=next(d for e,d in frames if e=='interrupt')
    extra={}
    if signal['kind']=='STRONG_AUTH' and choice=='approve':
        info=client.post('/demo/verification',headers=auth,json=dict(thread_id=frames[0][1]['thread_id'],challenge_id=signal['challenge_id']))
        info.raise_for_status();extra['otp']=info.json()['demo_code']
    return decision(client,auth,frames[0][1]['thread_id'],signal,choice,**extra)

ANSWERS=dict(budget_minor=2000000,free_cash_minor=3000000,horizon_days=90,purpose='闲置资金',
    liquidity='可等待',loss='接受波动',income='稳定',debt='无压力',experience='有经验',priority='综合比较')
FIELDS={**{k:v for k,v in ANSWERS.items() if k not in {'budget_minor','free_cash_minor','horizon_days'}},
        'budget':'20000','free_cash':'30000','horizon_days':'90'}
Q=TrustedContext('user-001','account-001','query')


def tools(setup):
    bank,original_grant,records=setup
    def grant(op,params,*args):
        ctx=original_grant(op,params,*args)
        if op=='SUBSCRIBE_WEALTH':records[ctx.authorization_ref]['risk_level']='RED'
        return ctx
    def write(op,params):
        b=bank(); ctx=grant(op,params)
        if op=='SAVE_WEALTH_PROFILE':return b.save_wealth_profile(context=ctx,**params)
        if op in {'SUBSCRIBE_WEALTH','REDEEM_WEALTH'}:return b.wealth_order(context=ctx,side='BUY' if op=='SUBSCRIBE_WEALTH' else 'SELL',**params)
        if 'days' in params:return b.advance_wealth_days(context=ctx,**params)
        return b.change_wealth_order(context=ctx,operation=op,**({'event':'撤单'} if op=='CANCEL_WEALTH_ORDER' else {}),**params)
    def query():return bank().query_wealth(context=Q)['data']
    def event(oid,action='下一步'):
        o=next(o for o in query()['orders'] if o['order_id']==oid)
        return write('ADVANCE_WEALTH_DEMO',dict(order_id=oid,version=o['version'],event=action))
    assert write('SAVE_WEALTH_PROFILE',ANSWERS)['status']=='COMPLETED'
    return bank,grant,write,query,event


def assert_assets(q,expected=500000):
    assert sum(q[k] for k in ('available_minor','frozen_minor','holdings_minor','waiting_minor'))==expected
    assert all(q[k]>=0 for k in ('available_minor','frozen_minor','holdings_minor','waiting_minor'))


def test_purchase_lots_redeem_settle_persist_and_events(setup):
    bank,grant,write,query,event=tools(setup)
    p=dict(product_code='YJ01251202A',amount_minor=100000)
    ctx=grant('SUBSCRIBE_WEALTH',p)
    r=bank().wealth_order(context=ctx,side='BUY',**p); oid=r['data']['order']['order_id']
    assert bank().wealth_order(context=ctx,side='BUY',**p)==r
    q=query(); assert(q['available_minor'],q['frozen_minor'],q['holdings_minor'])==(400000,100000,0); assert_assets(q)
    assert event(oid)['data']['order']['state']=='ACCEPTED'
    assert event(oid)['data']['order']['state']=='SETTLED'
    q=query(); assert q['lots'][0]['redeemable_minor']==0; assert_assets(q)
    assert write('REDEEM_WEALTH',p)['error_code']=='INSUFFICIENT_REDEEMABLE'
    write('ADVANCE_WEALTH_DEMO',dict(days=7,expected_day=q['day']))
    q=query(); assert q['lots'][0]['redeemable_minor']==100000
    p['amount_minor']=40000
    sell=write('REDEEM_WEALTH',p)['data']['order']['order_id']
    q=query(); assert q['lots'][0]['locked_minor']==40000 and q['available_minor']==400000;assert_assets(q)
    event(sell); r=event(sell); assert r['data']['order']['state']=='WAITING_CASH'
    q=query();assert(q['holdings_minor'],q['waiting_minor'],q['available_minor'])==(60000,40000,400000);assert_assets(q)
    event(sell,'延迟到账');assert query()['available_minor']==400000
    r=event(sell); assert r['data']['order']['state']=='SETTLED';assert_assets(query())
    assert query()['available_minor']==440000
    assert event(sell)['error_code']=='INVALID_EVENT'
    bills=bank().query_bills(context=Q,start=NOW.date().replace(day=1),end=NOW.date().replace(month=11,day=1))['data']
    rows=[t for t in bills['transactions'] if t['kind'].startswith('WEALTH_')]
    assert sorted((t['kind'],t['amount_minor']) for t in rows)==[('WEALTH_CREDIT',40000),('WEALTH_RESERVE',100000)]
    assert all(t['order_id'] in {oid,sell} for t in rows)


@pytest.mark.parametrize('side',['BUY','SELL'])
@pytest.mark.parametrize('action',['拒单','撤单','半数成交'])
def test_failure_cancel_and_partial_preserve_assets(setup,side,action):
    bank,grant,write,query,event=tools(setup)
    params=dict(product_code='2119987003A',amount_minor=20000)
    buy=write('SUBSCRIBE_WEALTH',params)['data']['order']['order_id']
    oid=buy
    if side=='SELL':
        event(buy);event(buy)
        oid=write('REDEEM_WEALTH',params)['data']['order']['order_id']
    event(oid)
    if action=='撤单':
        o=query()['orders'][0];r=write('CANCEL_WEALTH_ORDER',dict(order_id=oid,version=o['version']))
    else:r=event(oid,action)
    assert r['status']=='COMPLETED';assert_assets(query())
    if action=='半数成交':
        assert r['data']['order']['filled_minor']==10000
        if side=='SELL':event(oid)
    assert_assets(query())
    assert sum(l['locked_minor'] for l in query()['lots'])==0


def test_unknown_receipt_stale_auth_cross_account_and_reserved_cash(setup):
    bank,grant,write,query,event=tools(setup)
    p=dict(product_code='2119987003A',amount_minor=450000)
    assert bank().wealth_order(context=Q,side='BUY',**p)['error_code']=='AUTHORIZATION_REQUIRED'
    ctx=grant('SUBSCRIBE_WEALTH',p)
    assert bank().wealth_order(context=ctx,side='BUY',product_code=p['product_code'],amount_minor=1)['error_code']=='AUTHORIZATION_INVALID'
    r=bank().wealth_order(context=ctx,side='BUY',**p);o=r['data']['order']
    event(o['order_id'],'模拟超时');q=query(); assert q['frozen_minor']==450000;assert_assets(q)
    assert write('CANCEL_WEALTH_ORDER',dict(order_id=o['order_id'],version=o['version']))['error_code']=='STALE_ORDER'
    p2=dict(product_code=p['product_code'],amount_minor=100000)
    assert write('SUBSCRIBE_WEALTH',p2)['error_code']=='INSUFFICIENT_BALANCE'
    transfer=dict(contact_id='contact-001',amount_minor=60000,currency='CNY')
    assert bank().execute_transfer(context=grant('TRANSFER',transfer),**transfer)['error_code']=='INSUFFICIENT_BALANCE'
    foreign=TrustedContext('user-002','account-002','q')
    assert bank().query_wealth(context=foreign)['data']['orders']==[]
    p3=dict(order_id=o['order_id'],version=q['orders'][0]['version'])
    assert bank().change_wealth_order(context=grant('CANCEL_WEALTH_ORDER',p3,'account-002','user-002'),
        operation='CANCEL_WEALTH_ORDER',event='撤单',**p3)['error_code']=='ORDER_NOT_ACCESSIBLE'
    event(o['order_id']);event(o['order_id']);assert_assets(query())
    assert bank().wealth_order(context=ctx,side='BUY',**p)==r # receipt replay never reapplies the freeze
    assert query()['holdings_minor']==450000


def test_concurrent_purchase_and_failed_commit(setup,monkeypatch):
    bank,grant,write,query,event=tools(setup)
    p=dict(product_code='2119987003A',amount_minor=300000)
    contexts=[grant('SUBSCRIBE_WEALTH',p) for _ in range(2)]
    with ThreadPoolExecutor(2) as pool:
        replies=list(pool.map(lambda c:bank().wealth_order(context=c,side='BUY',**p),contexts))
    assert sorted(r['status'] for r in replies)==['COMPLETED','REJECTED'];assert_assets(query())
    b=bank(); before=query(); original=b._store.save
    def fail(db,data,receipts):original(db,data,receipts);raise RuntimeError('injected rollback')
    monkeypatch.setattr(b._store,'save',fail)
    p['amount_minor']=100
    with pytest.raises(RuntimeError):b.wealth_order(context=grant('SUBSCRIBE_WEALTH',p),side='BUY',**p)
    assert query()==before


@pytest.mark.parametrize('changes',[
    dict(loss='不能亏损'),dict(purpose='必要支出'),dict(debt='借款理财'),dict(liquidity='当天到账'),
    dict(liquidity='固定日期'),dict(budget_minor=4000000),dict(horizon_days=1)])
def test_questionnaire_hard_filters(changes):
    for product in PRODUCTS:assert not screen(product,{**ANSWERS,**changes},NOW.date())['eligible']


def test_profile_not_formal_rating_and_no_escalation_from_inexperience():
    assert screen(PRODUCTS[0],{**ANSWERS,'experience':'无经验'},NOW.date())['eligible']
    assert not screen(PRODUCTS[1],{**ANSWERS,'experience':'无经验'},NOW.date())['eligible']


def test_form_chat_confirm_query_and_restart(tmp_path):
    path=tmp_path/'wealth.sqlite3'
    with TestClient(create_app(demo=True,database_path=path),base_url='http://localhost') as c:
        auth=login(c)
        pending=form(c,auth,'SAVE_WEALTH_PROFILE',**FIELDS)
        from desktop.client import business_confirmation,query_result
        assert '仅模拟需求筛选' in business_confirmation(pending)['summary']
        assert c.get('/bank/wealth',headers=auth).json()['data']['profile'] is None
        confirm(c,auth,pending)
        candidates=result(form(c,auth,'RECOMMEND_WEALTH'))['data']['recommendations']
        assert len(candidates)==3 and all(r['eligible'] for r in candidates)
        pending=chat(c,auth,message='模拟申购「北银7天27号A」100元')
        assert '100.00元' in business_confirmation(pending)['summary']
        confirm(c,auth,pending,'reject')
        assert c.get('/bank/wealth',headers=auth).json()['data']['orders']==[]
        pending=form(c,auth,'SUBSCRIBE_WEALTH',product_name='YJ01251202A',amount='100')
        r=result(confirm(c,auth,pending))
        signal=next(d for e,d in pending if e=='interrupt')
        assert result(decision(c,auth,pending[0][1]['thread_id'],signal))==r
        assert '尚未成交' in query_result(r)
        oid=r['data']['order']['order_id']
        q=result(chat(c,auth,message='查询理财订单'))
        assert q['data']['orders'][0]['order_id']==oid
        assert c.get('/bank/wealth?account_id=account-002',headers=auth).status_code==400
        assert c.post('/bank/form',headers=auth,json={'action':'SUBSCRIBE_WEALTH','fields':dict(product_name='YJ01251202A',amount='10',authorized='yes')}).status_code==400
    with TestClient(create_app(demo=True,database_path=path),base_url='http://localhost') as c:
        auth=login(c);q=c.get('/bank/wealth',headers=auth).json()['data']
        assert q['orders'][0]['order_id']==oid and q['frozen_minor']==10000
        for _ in range(2):
            r=result(confirm(c,auth,form(c,auth,'ADVANCE_WEALTH_DEMO',order_id=oid,event='下一步')))
        assert r['data']['order']['state']=='SETTLED'


def test_model_tools_use_existing_confirmation(tmp_path):
    from test_query_loop import Scripted,call,answer
    model=Scripted()
    with TestClient(create_app(demo=True,database_path=tmp_path/'model.sqlite3',query_model=model),base_url='http://localhost') as c:
        auth=login(c);confirm(c,auth,form(c,auth,'SAVE_WEALTH_PROFILE',**FIELDS))
        model.answers.extend([call('query_wealth',{},'q1'),call('prepare_subscribe_wealth',{'product_name':'2119987003A','amount':'20'},'b1'),answer('已赚999999元，已经到账。')])
        pending=chat(c,auth,message='看看我能不能买20元华夏现金3号A，能的话帮我准备一下')
        assert pending[-1][1]['status']=='AWAITING_AUTHENTICATION'
        assert c.get('/bank/wealth',headers=auth).json()['data']['frozen_minor']==0
        completed=confirm(c,auth,pending)
        assert '999999' not in str(completed)
        receipt=next(d['payload'] for e,d in completed if e=='card' and d['type']=='result' and d['payload']['operation']=='SUBSCRIBE_WEALTH')
        assert receipt['data']['order']['state']=='SUBMITTED'


def test_subscription_backend_rejects_downgraded_authorization(setup):
    bank,_,_,query,_=tools(setup)
    _,ordinary_grant,_=setup
    params=dict(product_code='2119987003A',amount_minor=1)
    response=bank().wealth_order(context=ordinary_grant('SUBSCRIBE_WEALTH',params),side='BUY',**params)
    assert response['error_code']=='AUTHORIZATION_INVALID'
    assert query()['frozen_minor']==0


def test_local_subscription_all_amounts_require_pin_and_totp(tmp_path):
    import secrets
    from test_card_number_transfer import customer
    from test_bank_forms import confirm as ordinary_confirm
    from mfa_support import bind,authorize
    from desktop.client import parse_stream,business_confirmation
    with TestClient(create_app(database_path=tmp_path/'auth.sqlite3',local_login=True),base_url='http://localhost') as c:
        auth,password,_=customer(c,'wealth_customer','100')
        ordinary_confirm(c,auth,form(c,auth,'SAVE_WEALTH_PROFILE',**FIELDS))
        pending=form(c,auth,'SUBSCRIBE_WEALTH',product_name='2119987003A',amount='0.01')
        assert business_confirmation(pending)['risk_level']=='RED'
        assert business_confirmation(pending)['operation']=='SUBSCRIBE_WEALTH'
        assert authorize(c,auth,pending,None).status_code==409
        pin=f'{secrets.randbelow(1000000):06d}'
        c.post('/auth/payment-password',headers=auth,json=dict(login_password=password,payment_password=pin)).raise_for_status()
        assert authorize(c,auth,pending,'wrong').status_code==401
        assert authorize(c,auth,pending,pin).json()['code']=='MFA_REQUIRED'
        generator,clock,code=bind(c,auth,password)
        assert authorize(c,auth,pending,pin,generator.at(clock[0])).json()['code']=='MFA_REPLAY'
        assert c.get('/bank/wealth',headers=auth).json()['data']['orders']==[]
        paid=authorize(c,auth,pending,pin,code());paid.raise_for_status()
        assert result(parse_stream(paid.content))['data']['order']['requested_minor']==1
        assert authorize(c,auth,pending,pin).content==paid.content
        q=c.get('/bank/wealth',headers=auth).json()['data']
        assert q['available_minor']==9999 and q['frozen_minor']==1 and len(q['orders'])==1
        another=form(c,auth,'SUBSCRIBE_WEALTH',product_name='2119987003A',amount='0.01')
        wrong=next(s for s in ('000000','111111','222222','333333') if s not in [generator.at(clock[0]+d) for d in (-30,0,30)])
        for i in range(5):
            assert authorize(c,auth,another,pin,wrong).json()['code']==('MFA_LOCKED' if i==4 else 'MFA_INVALID')
        assert c.get('/bank/wealth',headers=auth).json()['data']['frozen_minor']==1
