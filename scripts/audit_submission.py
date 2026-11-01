"""Reproducible native UI / optional live-model audit on a disposable ledger."""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
import time
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]


def run(output, visible=False, live_model=False):
    if not visible: os.environ['QT_QPA_PLATFORM']='offscreen'
    import pyotp
    from PySide6.QtWidgets import QApplication
    from desktop.app import LocalService, desktop_environment
    from desktop.login import LoginWindow, LoginClient
    from desktop.client import business_confirmation
    app=QApplication.instance() or QApplication([])
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    if (output/'record.json').exists(): raise ValueError('Use a new output directory; retain previous failures')
    env={k:v for k,v in os.environ.items() if not k.startswith('BANKAGENT_')}
    if live_model:
        env.update({k:v for k,v in desktop_environment().items() if k.startswith('BANKAGENT_MODEL_')})
        if not env.get('BANKAGENT_MODEL_API_KEY'): raise ValueError('Live model configuration unavailable')
    report={'mode':'real model' if live_model else 'offline rules','transport':'real TCP HTTP',
            'ledger':'temporary SQLite','cases':[]}
    def save(): (output/'record.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    with TemporaryDirectory(prefix='submission-',dir=ROOT/'.desktop-tmp') as tmp:
        service=LocalService(env={**env,'BANKAGENT_DB_PATH':str(Path(tmp)/'ledger.sqlite3'),'BANKAGENT_LOCAL_LOGIN':'1'})
        shell=None
        def wait(test):
            deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                app.processEvents()
                if test(): return
                time.sleep(.01)
            raise AssertionError('Window operation timed out')
        def settle():
            for _ in range(5): app.processEvents(); time.sleep(.04)
            wait(lambda:not shell.bank.busy)
        def capture(name):
            settle(); assert shell.bank.grab().save(str(output/(name+'.png')))
        def write(client,action,**fields):
            frames=client.resume(business_confirmation(client.form(action,fields)),'approve')
            receipts=[d['payload'] for e,d in frames if e=='card' and d['type']=='result']
            assert receipts and receipts[-1]['status']=='COMPLETED'
            return receipts[-1]
        def customer(client,username,name,funding):
            password=secrets.token_urlsafe(24)
            client.request('/auth/register',{'username':username,'display_name':name,'password':password})
            client.token=client.request('/auth/login',{'username':username,'password':password})['token']
            account=write(client,'OPEN_ACCOUNT',display_name='日常账户')['data']['account_id']
            client.switch_account(account)
            write(client,'ISSUE_DEBIT_CARD',display_name='日常卡'); write(client,'ACTIVATE_DEBIT_CARD',card_name='日常卡')
            if funding: write(client,'SIMULATE_CARD_DEPOSIT',card_name='日常卡',amount=funding)
            return password,client.get('/bank/desktop-objects')['data']['cards'][0]['card_number']
        try:
            shell=LoginWindow(service.start()); password,_=customer(shell.client,'audit_sender','张伟','10000')
            receiver=LoginClient(shell.client.url); _,target=customer(receiver,'audit_receiver','王芳',None)
            pin=f'{secrets.randbelow(1000000):06d}'
            shell.client.request('/auth/payment-password',{'login_password':password,'payment_password':pin})
            def pay(amount,code=None):
                pending=business_confirmation(shell.client.form('TRANSFER',{'recipient_name':target,'amount':amount}))
                frames=shell.client.resume(pending,'approve',pin,totp=code)
                assert frames[-1][1]['status']=='COMPLETED'
            pay('1000')
            enrollment=shell.client.request('/auth/mfa/enroll',{'login_password':password})
            authenticator=pyotp.parse_uri(enrollment.pop('uri'))
            shell.client.request('/auth/mfa/confirm',{'enrollment_id':enrollment['enrollment_id'],'code':authenticator.now()})
            pay('5000',authenticator.at(time.time()+30))
            shell.show_bank(); bank=shell.bank
            wait(lambda:not bank.busy and bank.snapshot is not None); settle()
            bank.resize(1440,860); bank.show_page(2); settle(); bank.bills_page.details(0)
            capture('ledger-detail')
            report.update(logical_size=[bank.width(),bank.height()],scale=bank.devicePixelRatioF(),
                          platform=app.platformName(),source_balance_minor=400000,
                          recipient_balance_minor=receiver.accounts()['accounts'][0]['balance_minor'])
            assert bank.snapshot['accounts'][0]['balance_minor']==400000
            bills=bank.bills_page
            assert len(bills.rows)==3 and '5,000.00' in bills.detail_amount.text()
            bills.search.setText('无匹配商户'); capture('ledger-empty'); assert not bills.rows and bills.detail_amount.text()=='—'
            bills.search.clear(); bills.month.setCurrentIndex(1); settle(); assert not bills.rows
            bills.reset.click(); settle(); assert len(bills.rows)==3
            report['cases'].append({'name':'ledger filters / month / reset / details','status':'COMPLETED'})
            bank.resize(1040,720); bills.details(0); capture('ledger-compact')
            bank.main_scroll.ensureWidgetVisible(bills.inspector); capture('ledger-compact-detail')
            bank.main_scroll.verticalScrollBar().setValue(0)
            bank.resize(1440,860)
            if live_model:
                bank.toggle_assistant(True)
                for prompt in ['我现在能用的钱还有多少？','看看这月给王芳的转账，一共花了多少？',
                               f'给卡号{target}转40元，先让我核对再付', '先取消这笔，不要扣钱']:
                    bank.send(prompt); wait(lambda:not bank.busy); settle()
                    # Save only public UI content, never tokens, QR, PIN or model reasoning.
                    report['cases'].append({'input':prompt.replace(target,'[本地测试收款卡]'),
                        'status':bank.status.text(),'pending':bool(bank.pending),
                        'reply':bank.conversation.toPlainText().replace(target,'[本地测试收款卡]')[-3500:]})
                    save(); print('Model case recorded:',report['cases'][-1]['pending'],flush=True)
                capture('assistant-live')
            else:
                bank.show_page(1); bank.recipient.setEditText(target); bank.amount.setText('30')
                bank.prepare_transfer.click(); wait(lambda:not bank.busy and bank.pending is not None)
                capture('transfer-confirm'); bank.reject.click(); wait(lambda:not bank.busy and bank.pending is None); settle()
                assert shell.client.accounts()['accounts'][0]['balance_minor']==400000
                report['cases'].append({'name':'ordinary form prepare and cancel','status':'COMPLETED','balance_minor':400000})
            assert receiver.accounts()['accounts'][0]['balance_minor']==600000
            report['final_balance_minor']=shell.client.accounts()['accounts'][0]['balance_minor']
            report['status']='COMPLETED'; save()
        except Exception as exc:
            report['status']='FAILED'; report['error_type']=type(exc).__name__; save(); raise
        finally:
            if shell:
                if shell.bank:
                    shell.bank.hide(); shell.bank.deleteLater()
                shell.hide(); shell.deleteLater(); app.processEvents()
            service.close()
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',required=True)
    parser.add_argument('--visible',action='store_true'); parser.add_argument('--live-model',action='store_true')
    args=parser.parse_args(); result=run(args.output,args.visible,args.live_model)
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False))
