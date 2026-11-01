import secrets
import sqlite3
import os

import pytest
from fastapi.testclient import TestClient

from bankagent.api.server import create_app
from bankagent.api.credentials import CredentialStore
from bankagent.api.mfa import MfaStore, protect
from bankagent.api.contracts import ApiError
from desktop.client import parse_stream, business_confirmation
from test_card_number_transfer import customer
from test_bank_forms import form, confirm
from test_api_http import result, chat
from test_funds_chain import select
from mfa_support import bind, authorize

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Current-user Windows DPAPI integration')


def setup(c, funding='3000'):
    auth, password, own = customer(c, 'sender', funding)
    other, _, target = customer(c, 'receiver', None)
    pin = f'{secrets.randbelow(1000000):06d}'
    c.post('/auth/payment-password', headers=auth,
           json={'login_password':password, 'payment_password':pin}).raise_for_status()
    return auth, password, own, other, target, pin


def balance(c, auth):
    return sum(a['balance_minor'] for a in c.get('/bank/accounts',headers=auth).json()['accounts'])


def test_all_cards_threshold_exact_boundary_mfa_and_restart(tmp_path):
    path = tmp_path/'customer.sqlite3'
    with TestClient(create_app(database_path=path,local_login=True),base_url='http://localhost') as c:
        a,password,own,b,target,pin = setup(c)
        first = form(c,a,'TRANSFER',recipient_name=target,amount='1000')
        assert business_confirmation(first)['risk_level']=='YELLOW'
        assert result(parse_stream(authorize(c,a,first,pin).content))['status']=='COMPLETED'
        # A second account/card has its own balance but shares this customer's daily total.
        second = result(confirm(c,a,form(c,a,'OPEN_ACCOUNT',display_name='第二账户')))['data']['account_id']
        a = select(c,a,second)
        for action,fields in [('ISSUE_DEBIT_CARD',{'display_name':'第二卡'}),('ACTIVATE_DEBIT_CARD',{'card_name':'第二卡'}),
                              ('SIMULATE_CARD_DEPOSIT',{'card_name':'第二卡','amount':'100'})]:
            assert result(confirm(c,a,form(c,a,action,**fields)))['status']=='COMPLETED'
        pending = form(c,a,'TRANSFER',recipient_name=target,amount='1')
        assert business_confirmation(pending)['risk_level']=='RED'
        assert authorize(c,a,pending,pin).json()['code']=='MFA_REQUIRED'
        assert balance(c,a)==210000 and balance(c,b)==100000
        generator, clock, code = bind(c,a,password)
        assert c.get('/auth/me',headers=a).json()['mfa_configured'] is True
        assert authorize(c,a,pending,pin,generator.at(clock[0])).json()['code']=='MFA_REPLAY'
        paid = authorize(c,a,pending,pin,code())
        assert result(parse_stream(paid.content))['status']=='COMPLETED'
        # Lost response / duplicate click uses the original operation, no fresh OTP or debit.
        assert authorize(c,a,pending,pin).content==paid.content
        assert balance(c,a)==209900 and balance(c,b)==100100
        assert authorize(c,b,pending,pin,code()).status_code in {403,404}
        with sqlite3.connect(path) as db:
            before = db.execute('SELECT data FROM bank_state').fetchone()[0]
            credentials = db.execute('SELECT * FROM local_credentials').fetchall()
            blob = db.execute('SELECT secret FROM local_mfa').fetchone()[0]
        assert generator.secret.encode() not in blob
        assert generator.secret not in before
    # Reinitializing auth changes neither ledger nor password hashes, nor used-code state.
    with TestClient(create_app(database_path=path,local_login=True),base_url='http://localhost') as c:
        with sqlite3.connect(path) as db:
            assert db.execute('SELECT data FROM bank_state').fetchone()[0]==before
            assert db.execute('SELECT * FROM local_credentials').fetchall()==credentials
        token = c.post('/auth/login',json={'username':'sender','password':password}).json()['token']
        a = {'Authorization':'Bearer '+token}
        assert balance(c,a)==209900 and c.get('/auth/me',headers=a).json()['mfa_configured']
        tx = c.get('/bank/bills',headers=a).json()['data']['transactions']
        assert any(t['kind']=='TRANSFER_OUT' and t['amount_minor']==100000 for t in tx)


def test_persistent_lock_binding_scope_and_replay(tmp_path):
    path=tmp_path/'security.sqlite3'
    with TestClient(create_app(database_path=path,local_login=True),base_url='http://localhost') as c:
        a,password,_,b,target,pin = setup(c)
        assert c.post('/auth/mfa/enroll',json={'login_password':password}).status_code==401
        assert c.post('/auth/mfa/enroll',headers=a,json={'login_password':password,'user_id':'other'}).status_code==400
        generator,clock,next_code=bind(c,a,password)
        assert c.post('/auth/mfa/enroll',headers=a,json={'login_password':password}).json()['code']=='MFA_ALREADY_CONFIGURED'
        pending=form(c,a,'TRANSFER',recipient_name=target,amount='1001')
        wrong=next(s for s in ('000000','111111','222222','333333') if s not in
                   [generator.at(clock[0]+offset) for offset in (-30,0,30)])
        for i in range(5):
            reply=authorize(c,a,pending,pin,wrong)
            assert reply.json()['code']==('MFA_LOCKED' if i==4 else 'MFA_INVALID')
        assert balance(c,a)==300000 and balance(c,b)==0
        assert confirm(c,a,pending,'reject')[-1][1]['status']=='REJECTED'
    with TestClient(create_app(database_path=path,local_login=True),base_url='http://localhost') as c:
        c.app.state.service.credentials.clock=lambda:clock[0]
        token=c.post('/auth/login',json={'username':'sender','password':password}).json()['token']
        a={'Authorization':'Bearer '+token}
        pending=form(c,a,'TRANSFER',recipient_name=target,amount='1002')
        assert authorize(c,a,pending,pin,next_code()).json()['code']=='MFA_LOCKED'
        clock[0]+=900
        code=next_code()
        assert result(parse_stream(authorize(c,a,pending,pin,code).content))['status']=='COMPLETED'
        another=form(c,a,'TRANSFER',recipient_name=target,amount='1')
        assert authorize(c,a,another,pin,code).json()['code']=='MFA_REPLAY'
        assert confirm(c,a,another,'reject')[-1][1]['status']=='REJECTED'
        modified=form(c,a,'TRANSFER',recipient_name=target,amount='2')
        assert authorize(c,a,another,pin,next_code()).status_code==409
        assert balance(c,a)==199800
        assert result(parse_stream(authorize(c,a,modified,pin,next_code()).content))['status']=='COMPLETED'


def test_ai_batch_mfa_atomic_failure_and_success(tmp_path):
    from test_query_loop import Scripted, call, answer
    from test_batch_transfer import batch_result
    model=Scripted()
    with TestClient(create_app(database_path=tmp_path/'batch.sqlite3',local_login=True,query_model=model),base_url='http://localhost') as c:
        a,password,_,b,target,pin=setup(c,'1500')
        _,_,code=bind(c,a,password)
        for amounts,committed,expected in [(('900','700'),False,150000),(('900','200'),True,40000)]:
            model.answers.clear()
            model.answers.extend([call('prepare_batch_transfer',{'items':[
                {'recipient_name':target,'amount':v} for v in amounts]}),answer('请查看实际结果。')])
            pending=chat(c,a,message='请分两笔付到这张卡，确认总金额后再办理')
            assert business_confirmation(pending) is not None, [(e, d.get('status'),d.get('message'),d.get('code')) for e,d in pending]
            assert business_confirmation(pending)['risk_level']=='RED'
            assert authorize(c,a,pending,pin).json()['code']=='MFA_INVALID'
            reply=authorize(c,a,pending,pin,code())
            actual=batch_result(parse_stream(reply.content))
            assert actual['data']['committed'] is committed
            assert balance(c,a)==expected
            assert authorize(c,a,pending,pin).content==reply.content
        assert balance(c,b)==110000
        receipts=c.get('/bank/transfer-batches',headers=a).json()['data']['receipts']
        assert len(receipts)==2


def test_dpapi_and_same_grant_retry_does_not_authorize_another_operation(tmp_path):
    value=secrets.token_bytes(32)
    encrypted=protect(value)
    assert encrypted!=value and protect(encrypted,decrypt=True)==value
    with TestClient(create_app(database_path=tmp_path/'grant.sqlite3',local_login=True),base_url='http://localhost') as c:
        a,password,_,_,_,_=setup(c)
        generator,clock,code=bind(c,a,password)
        service=c.app.state.service
        user=service.sessions.resolve(a['Authorization']).user_id
        used=code()
        service.mfa.verify(user,used,'challenge-1','hash-1',60)
        # A fresh store can retry exactly the approved operation after an interrupted response.
        store=MfaStore(CredentialStore(tmp_path/'grant.sqlite3',clock=lambda:clock[0]))
        store.verify(user,None,'challenge-1','hash-1',60)
        for cid,digest in [('challenge-2','hash-1'),('challenge-1','hash-2')]:
            with pytest.raises(ApiError) as error:
                store.verify(user,used,cid,digest,60)
            assert error.value.code=='MFA_REPLAY'
        clock[0]+=120
        with pytest.raises(ApiError):
            store.verify(user,used,'challenge-1','hash-1',60)


def test_risk_rechecked_after_other_session_spends_and_freeze(tmp_path):
    with TestClient(create_app(database_path=tmp_path/'race.sqlite3',local_login=True),base_url='http://localhost') as c:
        a,password,_,b,target,pin=setup(c)
        _,_,code=bind(c,a,password)
        old=form(c,a,'TRANSFER',recipient_name=target,amount='600')
        assert business_confirmation(old)['risk_level']=='YELLOW'
        token=c.post('/auth/login',json={'username':'sender','password':password}).json()['token']
        concurrent={'Authorization':'Bearer '+token}
        other=form(c,concurrent,'TRANSFER',recipient_name=target,amount='500')
        assert result(parse_stream(authorize(c,concurrent,other,pin).content))['status']=='COMPLETED'
        # The old low-risk confirmation must not bypass a newly crossed daily boundary.
        reply=result(parse_stream(authorize(c,a,old,pin).content))
        assert reply['error_code']=='REAUTHORIZATION_REQUIRED'
        assert balance(c,a)==250000
        high=form(c,a,'TRANSFER',recipient_name=target,amount='600')
        assert business_confirmation(high)['risk_level']=='RED'
        confirm(c,concurrent,form(c,concurrent,'FREEZE_CARD',card_name='日常卡'))
        reply=result(parse_stream(authorize(c,a,high,pin,code()).content))
        assert reply['error_code']=='SOURCE_CARD_FROZEN'
        assert balance(c,a)==250000 and balance(c,b)==50000


def test_enrollment_requires_both_secrets_and_expiry(tmp_path):
    import pyotp
    with TestClient(create_app(database_path=tmp_path/'binding.sqlite3',local_login=True),base_url='http://localhost') as c:
        a,password,_,b,target,pin=setup(c)
        store=c.app.state.service.credentials
        clock=[store.clock()]; store.clock=lambda:clock[0]
        assert c.post('/auth/mfa/enroll',headers=a,json={'login_password':secrets.token_urlsafe(24)}).status_code==401
        data=c.post('/auth/mfa/enroll',headers=a,json={'login_password':password}).json()
        otp=pyotp.parse_uri(data['uri'])
        payload={'enrollment_id':data['enrollment_id'],'code':otp.at(clock[0])}
        assert c.post('/auth/mfa/confirm',headers=b,json=payload).json()['code']=='MFA_ENROLLMENT_EXPIRED'
        assert c.get('/auth/me',headers=a).json()['mfa_configured'] is False
        clock[0]+=301
        assert c.post('/auth/mfa/confirm',headers=a,json=payload).json()['code']=='MFA_ENROLLMENT_EXPIRED'
        assert c.get('/auth/me',headers=a).json()['mfa_configured'] is False
        pending=form(c,a,'TRANSFER',recipient_name=target,amount='1001')
        assert authorize(c,a,pending,pin,payload['code']).json()['code']=='MFA_REQUIRED'
        assert balance(c,a)==300000
