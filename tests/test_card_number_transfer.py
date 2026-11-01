import secrets
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from desktop.client import parse_stream
from test_bank_forms import form, confirm
from test_api_http import result, chat


def customer(c, username, funding='1000'):
    password = secrets.token_urlsafe(24)
    assert c.post('/auth/register',json={'username':username,'display_name':'同名客户','password':password}).status_code==200
    token = c.post('/auth/login',json={'username':username,'password':password}).json()['token']
    auth={'Authorization':'Bearer '+token}
    assert c.get('/bank/accounts',headers=auth).json()['accounts']==[]
    account=result(confirm(c,auth,form(c,auth,'OPEN_ACCOUNT',display_name='日常账户')))['data']['account_id']
    assert c.get('/bank/accounts',headers=auth).json()['accounts'][0]['balance_minor']==0
    token=c.post('/bank/account-session',headers=auth,json={'account_ref':account}).json()['token']
    auth={'Authorization':'Bearer '+token}
    for action,fields in [('ISSUE_DEBIT_CARD',{'display_name':'日常卡'}),('ACTIVATE_DEBIT_CARD',{'card_name':'日常卡'})]:
        assert result(confirm(c,auth,form(c,auth,action,**fields)))['status']=='COMPLETED'
    number=c.get('/bank/desktop-objects',headers=auth).json()['data']['cards'][0]['card_number']
    if funding:
        assert result(confirm(c,auth,form(c,auth,'SIMULATE_CARD_DEPOSIT',card_name='日常卡',amount=funding)))['status']=='COMPLETED'
    return auth,password,number


def pay(c,auth,pending,pin):
    signal=next(d for e,d in pending if e=='interrupt')
    return c.post('/agent/chat',headers=auth,json={'thread_id':pending[0][1]['thread_id'],
        'resume':{'challenge_id':signal['challenge_id'],'decision':'approve','otp':pin}})


def test_two_new_customers_card_number_form_ai_restart(tmp_path):
    path=tmp_path/'bank.sqlite3'
    with TestClient(create_app(database_path=path,local_login=True),base_url='http://localhost') as c:
        a,password,own=customer(c,'sender')
        b,other_password,number=customer(c,'receiver')
        assert len(number)==16 and number!=own
        assert c.get('/bank/desktop-objects',headers=a).json()['data']['recipients']==[]
        pin=f'{secrets.randbelow(1000000):06d}'
        assert c.post('/auth/payment-password',headers=a,json={'login_password':password,'payment_password':pin}).status_code==200
        spaced=' '.join(number[i:i+4] for i in range(0,16,4))
        pending=form(c,a,'TRANSFER',recipient_name=spaced,amount='40')
        card=next(d['payload'] for e,d in pending if e=='card' and d['type']=='confirm')
        assert number not in card['recipient'] and number[-4:] in card['recipient'] and '同名客户' in card['recipient']
        assert pay(c,a,pending,'wrong').status_code==401
        paid=result(parse_stream(pay(c,a,pending,pin).content))
        assert paid['status']=='COMPLETED'
        assert result(parse_stream(pay(c,a,pending,pin).content))==paid
        # Same named customers cannot be selected by bare name.
        missing=chat(c,a,message='给同名客户转30元')
        assert missing[-1][1]['status']=='NEEDS_CLARIFICATION'
        pending=chat(c,a,message=number,thread_id=missing[0][1]['thread_id'])
        assert result(parse_stream(pay(c,a,pending,pin).content))['status']=='COMPLETED'
        for target in ('9900999999999999',own,number+'x'):
            invalid=form(c,a,'TRANSFER',recipient_name=target,amount='1')
            assert not any(e=='interrupt' for e,d in invalid)
        for auth,balance in ((a,93000),(b,107000)):
            assert c.get('/bank/accounts',headers=auth).json()['accounts'][0]['balance_minor']==balance
        outgoing=[t for t in c.get('/bank/bills',headers=a).json()['data']['transactions'] if t['kind']=='TRANSFER_OUT']
        incoming=[t for t in c.get('/bank/bills',headers=b).json()['data']['transactions'] if t['kind']=='TRANSFER_IN']
        assert len(outgoing)==len(incoming)==2
        assert {t['related_transaction_id'] for t in outgoing}=={t['transaction_id'] for t in incoming}
    with TestClient(create_app(database_path=path,local_login=True),base_url='http://localhost') as c:
        for username,secret,balance,card in [('sender',password,93000,own),('receiver',other_password,107000,number)]:
            token=c.post('/auth/login',json={'username':username,'password':secret}).json()['token']
            auth={'Authorization':'Bearer '+token}
            assert c.get('/bank/accounts',headers=auth).json()['accounts'][0]['balance_minor']==balance
            assert c.get('/bank/desktop-objects',headers=auth).json()['data']['cards'][0]['card_number']==card


def test_number_upgrade_preserves_old_money_and_history(tmp_path):
    from bankagent.banking.storage import SQLiteStore
    from bankagent.banking.data.generator import build_demo_data
    from copy import deepcopy
    seed=build_demo_data()
    for row in seed['cards'].values(): row.pop('card_number')
    before=deepcopy(seed)
    path=tmp_path/'old.sqlite3'
    store=SQLiteStore(path,seed)
    with store.connection() as db: upgraded,_=store.load(db)
    numbers={key:row.pop('card_number') for key,row in upgraded['cards'].items()}
    assert upgraded==before
    with store.connection() as db: again,_=store.load(db)
    assert {key:row['card_number'] for key,row in again['cards'].items()}==numbers


def test_card_transfer_cancel_change_frozen_insufficient_and_cross_user(tmp_path):
    with TestClient(create_app(database_path=tmp_path/'rules.sqlite3',local_login=True),base_url='http://localhost') as c:
        a,password,own=customer(c,'sender')
        b,_,number=customer(c,'receiver')
        pin=f'{secrets.randbelow(1000000):06d}'
        c.post('/auth/payment-password',headers=a,json={'login_password':password,'payment_password':pin}).raise_for_status()
        old=form(c,a,'TRANSFER',recipient_name=number,amount='40')
        assert pay(c,b,old,pin).status_code in {403,404}
        # Native form edit explicitly rejects the old challenge, then prepares a new draft.
        assert confirm(c,a,old,'reject')[-1][1]['status']=='REJECTED'
        changed=form(c,a,'TRANSFER',recipient_name=number,amount='30')
        assert pay(c,a,old,pin).status_code==409
        card=next(d['payload'] for e,d in changed if e=='card' and d['type']=='confirm')
        assert card['amount_minor']==3000 and card['recipient_input']==number
        assert confirm(c,a,changed,'reject')[-1][1]['status']=='REJECTED'
        confirm(c,a,form(c,a,'FREEZE_CARD',card_name='日常卡'))
        blocked=form(c,a,'TRANSFER',recipient_name=number,amount='40')
        assert result(blocked)['error_code']=='SOURCE_CARD_FROZEN'
        confirm(c,a,form(c,a,'UNFREEZE_CARD',card_name='日常卡'))
        insufficient=form(c,a,'TRANSFER',recipient_name=number,amount='1001')
        assert result(parse_stream(pay(c,a,insufficient,pin).content))['error_code']=='INSUFFICIENT_BALANCE'
        pending=form(c,a,'TRANSFER',recipient_name=number,amount='40')
        # Simulate a destination binding change after confirmation in this isolated store.
        import json
        import sqlite3
        with sqlite3.connect(tmp_path/'rules.sqlite3') as db:
            data=json.loads(db.execute('SELECT data FROM bank_state').fetchone()[0])
            source=next(card['account_id'] for card in data['cards'].values() if card['card_number']==own)
            next(card for card in data['cards'].values() if card['card_number']==number)['account_id']=source
            db.execute('UPDATE bank_state SET data=?',(json.dumps(data),))
        assert result(parse_stream(pay(c,a,pending,pin).content))['error_code']=='CONTACT_NOT_ACCESSIBLE'
        for auth in (a,b):
            assert c.get('/bank/accounts',headers=auth).json()['accounts'][0]['balance_minor']==100000


def test_card_batch_reuses_atomic_backend(tmp_path):
    from test_query_loop import Scripted, call, answer
    from test_batch_transfer import batch_result
    model=Scripted()
    with TestClient(create_app(database_path=tmp_path/'batch.sqlite3',local_login=True,query_model=model),base_url='http://localhost') as c:
        a,password,_=customer(c,'sender')
        b,_,number=customer(c,'receiver')
        # Two items may pay the same concrete card; both still commit as one batch.
        pin=f'{secrets.randbelow(1000000):06d}'
        c.post('/auth/payment-password',headers=a,json={'login_password':password,'payment_password':pin}).raise_for_status()
        for amounts,success,expected in [(('40','25'),True,93500),(('900','50'),False,93500)]:
            model.answers.extend([call('prepare_batch_transfer',{'items':[
                {'recipient_name':number,'amount':amount} for amount in amounts]}),answer('请核对实际回执。')])
            pending=chat(c,a,message='按提供的卡号分两笔转出')
            response=pay(c,a,pending,pin)
            actual=batch_result(parse_stream(response.content))
            assert actual['data']['committed'] is success
            assert parse_stream(pay(c,a,pending,pin).content)==parse_stream(response.content)
            assert c.get('/bank/accounts',headers=a).json()['accounts'][0]['balance_minor']==expected
        assert c.get('/bank/accounts',headers=b).json()['accounts'][0]['balance_minor']==106500
