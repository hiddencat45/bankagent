from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from desktop.client import parse_stream
from test_account_lifecycle import setup
from test_api_http import login, result, chat
from test_bank_forms import form, confirm
from test_demo_verification import pending, approve, balance


def test_frozen_card_blocks_form_and_agent_before_confirmation_then_unfreeze():
    with TestClient(create_app(demo=True), base_url='http://localhost') as c:
        h = login(c)
        assert result(confirm(c,h,form(c,h,'FREEZE_CARD',card_name='日常消费卡')))['status'] == 'COMPLETED'
        for out in [form(c,h,'TRANSFER',recipient_name='张伟',amount='1200'), chat(c,h,message='给张伟转40元')]:
            assert result(out)['error_code'] == 'SOURCE_CARD_FROZEN'
            assert not any(e == 'interrupt' for e,d in out)
            assert '冻结' in ' '.join(d.get('text','') for e,d in out)
        assert balance(c,h) == 500000
        confirm(c,h,form(c,h,'UNFREEZE_CARD',card_name='日常消费卡'))
        out = form(c,h,'TRANSFER',recipient_name='张伟',amount='40')
        assert result(confirm(c,h,out))['data']['remaining_balance_minor'] == 496000


def test_frozen_after_prepare_cannot_bypass_with_already_issued_code(tmp_path):
    path = tmp_path/'bank.sqlite3'
    with TestClient(create_app(demo=True,database_path=path),base_url='http://localhost') as c:
        h = login(c)
        ref = pending(c,h)
        code = c.post('/demo/verification',headers=h,json=ref).json()['demo_code']
        other = login(c)
        confirm(c,other,form(c,other,'FREEZE_CARD',card_name='日常消费卡'))
        assert c.post('/demo/verification',headers=h,json=ref).json()['code'] == 'SOURCE_CARD_FROZEN'
        done = parse_stream(approve(c,h,ref,code).content)
        assert result(done)['error_code'] == 'SOURCE_CARD_FROZEN'
        assert balance(c,h) == 500000
        assert result(parse_stream(approve(c,h,ref).content))['error_code'] == 'SOURCE_CARD_FROZEN'
    with TestClient(create_app(demo=True,database_path=path),base_url='http://localhost') as c:
        h=login(c)
        assert balance(c,h) == 500000
        assert not [r for r in c.get('/bank/bills',headers=h).json()['data']['transactions'] if r['kind']=='TRANSFER_OUT']


@pytest.mark.parametrize('batch', [False, True])
def test_authorized_transfer_rechecks_frozen_state_and_keeps_all_money(setup,batch):
    bank,grant,_=setup
    b=bank()
    row={'contact_id':'contact-001','amount_minor':4000,'currency':'CNY'}
    params={'items':[row,{**row,'contact_id':'contact-002'}]} if batch else row
    ctx=grant('BATCH_TRANSFER' if batch else 'TRANSFER',params)
    b.freeze_card(context=grant('FREEZE_CARD',{'card_id':'card-001'}),card_id='card-001')
    before=deepcopy(b._data)
    done=b.execute_transfer_batch(context=ctx,**params) if batch else b.execute_transfer(context=ctx,**params)
    assert done['status']=='REJECTED'
    if batch:
        assert done['data']['committed'] is False
        assert done['data']['items'][0]['error_code']=='SOURCE_CARD_FROZEN'
    else:
        assert done['error_code']=='SOURCE_CARD_FROZEN'
    after=bank()._data
    assert after['accounts']==before['accounts'] and after['transactions']==before['transactions']
