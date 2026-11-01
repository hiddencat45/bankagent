import secrets
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from desktop.client import parse_stream
from test_api_http import result
from test_bank_forms import form, confirm
from test_card_number_transfer import customer, pay
from test_account_lifecycle import setup


def test_zero_opening_explicit_funding_card_transfer_and_restart(tmp_path,monkeypatch):
    path=tmp_path/'bank.sqlite3'
    with TestClient(create_app(database_path=path,local_login=True),base_url='http://localhost') as c:
        a,password,own=customer(c,'payer',funding=None)
        b,other_password,target=customer(c,'receiver',funding=None)
        def balance(auth): return c.get('/bank/accounts',headers=auth).json()['accounts'][0]['balance_minor']
        assert balance(a)==balance(b)==0
        assert c.get('/bank/bills',headers=a).json()['data']['transactions']==[]
        pending=form(c,a,'SIMULATE_CARD_DEPOSIT',card_name='日常卡',amount='1000')
        assert balance(a)==0
        confirm(c,a,pending,'reject')
        assert balance(a)==0
        pending=form(c,a,'SIMULATE_CARD_DEPOSIT',card_name='日常卡',amount='1000')
        from bankagent.agent.scenarios import REGISTRY
        spec=REGISTRY.get('card_deposit')
        original=spec.execute
        calls=[]
        def lose_response(*args,**kwargs):
            value=original(*args,**kwargs)
            calls.append(True)
            if len(calls)==1: raise OSError('injected response failure after commit')
            return value
        with monkeypatch.context() as injected:
            injected.setattr(spec,'execute',lose_response)
            assert confirm(c,a,pending)[-1][1]['status']=='FAILED'
            assert balance(a)==100000
        funded=result(confirm(c,a,pending))
        assert funded['status']=='COMPLETED' and balance(a)==100000
        assert result(confirm(c,a,pending))==funded and balance(a)==100000
        pin=f'{secrets.randbelow(1000000):06d}'
        c.post('/auth/payment-password',headers=a,json={'login_password':password,'payment_password':pin}).raise_for_status()
        pending=form(c,a,'TRANSFER',recipient_name=target,amount='40')
        card=next(d['payload'] for e,d in pending if e=='card' and d['type']=='confirm')
        assert own[-4:] in card['payer_card'] and target[-4:] in card['recipient']
        paid=result(parse_stream(pay(c,a,pending,pin).content))
        assert paid['status']=='COMPLETED' and balance(a)==96000 and balance(b)==4000
        assert result(parse_stream(pay(c,a,pending,pin).content))==paid
        rows=c.get('/bank/bills',headers=a).json()['data']['transactions']
        assert [(t['kind'],t['amount_minor']) for t in rows]==[('INCOME',100000),('TRANSFER_OUT',4000)]
        assert rows[0]['category']=='模拟入金'
        # Additional account has no card or money, and cannot be used for outgoing payments.
        opened=result(confirm(c,a,form(c,a,'OPEN_ACCOUNT',display_name='未办卡账户')))
        from test_funds_chain import select
        a=select(c,a,opened['data']['account_id'])
        assert result(form(c,a,'TRANSFER',recipient_name=target,amount='1'))['error_code']=='SOURCE_CARD_REQUIRED'
        confirm(c,a,form(c,a,'ISSUE_DEBIT_CARD',display_name='待激活卡'))
        assert result(form(c,a,'TRANSFER',recipient_name=target,amount='1'))['error_code']=='SOURCE_CARD_NOT_ACTIVE'
        blocked=result(confirm(c,a,form(c,a,'SIMULATE_CARD_DEPOSIT',card_name='待激活卡',amount='10')))
        assert blocked['error_code']=='CARD_NOT_ACTIVE'
    with TestClient(create_app(database_path=path,local_login=True),base_url='http://localhost') as c:
        for username,password,expected in [('payer',password,[96000,0]),('receiver',other_password,[4000])]:
            token=c.post('/auth/login',json={'username':username,'password':password}).json()['token']
            auth={'Authorization':'Bearer '+token}
            assert [a['balance_minor'] for a in c.get('/bank/accounts',headers=auth).json()['accounts']]==expected


def test_funding_transaction_rules_and_failed_commit(setup,monkeypatch):
    import sqlite3
    bank,grant,_=setup
    b=bank()
    params=dict(card_id='card-001',amount_minor=1000)
    ctx=grant('SIMULATE_CARD_DEPOSIT',params)
    before=b._data
    original=b._store.save
    def fail(db,data,receipts):
        original(db,data,receipts)
        raise sqlite3.OperationalError('injected commit failure')
    monkeypatch.setattr(b._store,'save',fail)
    import pytest
    with pytest.raises(sqlite3.OperationalError): b.simulate_card_deposit(context=ctx,**params)
    assert bank()._data==before
    b=bank()
    funded=b.simulate_card_deposit(context=ctx,**params)
    assert funded['data']['remaining_balance_minor']==501000
    assert bank().simulate_card_deposit(context=ctx,**params)==funded
    for amount in (True,0,-1,1000001):
        assert b.simulate_card_deposit(context=ctx,card_id='card-001',amount_minor=amount)['error_code']=='INVALID_DEPOSIT'
    foreign=dict(card_id='card-003',amount_minor=1000)
    assert b.simulate_card_deposit(context=grant('SIMULATE_CARD_DEPOSIT',foreign),**foreign)['error_code']=='CARD_NOT_ACCESSIBLE'
    next_ctx=grant('SIMULATE_CARD_DEPOSIT',params)
    b.freeze_card(context=grant('FREEZE_CARD',{'card_id':'card-001'}),card_id='card-001')
    assert b.simulate_card_deposit(context=next_ctx,**params)['error_code']=='CARD_NOT_ACTIVE'
    from bankagent.agent.scenarios.card_deposit import render
    assert '尚未确认' in render({'status':'FAILED'})


def test_model_tool_deposit_uses_same_confirmation_and_ledger(tmp_path):
    from test_query_loop import Scripted, call, answer
    from test_api_http import chat
    model=Scripted()
    with TestClient(create_app(database_path=tmp_path/'model.sqlite3',local_login=True,query_model=model),base_url='http://localhost') as c:
        auth,_,_=customer(c,'payer',funding=None)
        model.answers.extend([call('prepare_simulate_card_deposit',{'card_name':'日常卡','amount':'25'}),answer('入金结果以回执为准。')])
        pending=chat(c,auth,message='我想手动加25元模拟资金到日常卡里')
        assert c.get('/bank/accounts',headers=auth).json()['accounts'][0]['balance_minor']==0
        assert result(confirm(c,auth,pending))['status']=='COMPLETED'
        assert c.get('/bank/accounts',headers=auth).json()['accounts'][0]['balance_minor']==2500
