"""Reproducible competition demo: isolated ledger, native controls, optional live AI.

Never opens the user's daily ledger or saves credentials. Screens show simulated money.
"""
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


def run(output,visible=False,live_model=False):
    if not visible:os.environ['QT_QPA_PLATFORM']='offscreen'
    import pyotp
    from PySide6.QtWidgets import QApplication,QLineEdit,QDialog
    from PySide6.QtCore import QTimer
    from desktop.app import LocalService,desktop_environment
    from desktop.login import LoginWindow
    from desktop.client import business_confirmation
    app=QApplication.instance() or QApplication([])
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if (output/'record.json').exists():raise ValueError('Choose a new output directory to preserve earlier evidence')
    env={k:v for k,v in os.environ.items() if not k.startswith('BANKAGENT_')}
    if live_model:
        env.update({k:v for k,v in desktop_environment().items() if k.startswith('BANKAGENT_MODEL_')})
        if not env.get('BANKAGENT_MODEL_API_KEY'):raise ValueError('No live model configuration')
    report=dict(transport='real TCP HTTP',ledger='temporary SQLite',mode='live model' if live_model else 'offline rules',cases=[])
    def save():(output/'record.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'.desktop-tmp').mkdir(exist_ok=True)
    with TemporaryDirectory(prefix='wealth-audit-',dir=ROOT/'.desktop-tmp') as temp:
        service=LocalService(env={**env,'BANKAGENT_DB_PATH':str(Path(temp)/'ledger.sqlite3'),'BANKAGENT_LOCAL_LOGIN':'1'})
        w=None;shell=None
        def wait(predicate):
            until=time.monotonic()+90
            while time.monotonic()<until:
                app.processEvents()
                if predicate():return
                time.sleep(.01)
            raise AssertionError('UI operation timeout')
        def idle():
            for _ in range(4):app.processEvents();time.sleep(.03)
            wait(lambda:not w.busy)
        def capture(name):
            idle()
            if 'confirm' not in name:
                w.main_scroll.verticalScrollBar().setValue(0);idle()
            assert w.grab().save(str(output/(name+'.png')))
        def write(client,op,**fields):
            frames=client.resume(business_confirmation(client.form(op,fields)),'approve')
            r=next(d['payload'] for e,d in frames if e=='card' and d['type']=='result' and d['payload']['operation']==op)
            assert r['status']=='COMPLETED';return r
        def approve():
            wait(lambda:not w.busy and w.pending is not None)
            assert w.approve.isVisible() and w.approve.isEnabled()
            if w.pending['risk_level']=='RED':
                timer=QTimer();timer.setInterval(50)
                def fill():
                    dialog=next((d for d in app.topLevelWidgets() if isinstance(d,QDialog) and d.isVisible() and d.windowTitle()=='模拟申购 · 追加认证'),None)
                    if dialog is None:return
                    timer.stop()
                    assert dialog.grab().save(str(output/'buy-auth-dialog.png'))
                    entries=dialog.findChildren(QLineEdit)
                    assert len(entries)==2
                    entries[0].setText(pin);entries[1].setText(authenticator.at(time.time()+30));dialog.accept()
                timer.timeout.connect(fill);timer.start()
            w.approve.click();wait(lambda:not w.busy and w.pending is None);idle()
        try:
            shell=LoginWindow(service.start());client=shell.client;password=secrets.token_urlsafe(24)
            client.request('/auth/register',dict(username='wealth_audit',display_name='理财演示客户',password=password))
            client.token=client.request('/auth/login',dict(username='wealth_audit',password=password))['token']
            account=write(client,'OPEN_ACCOUNT',display_name='理财演示账户')['data']['account_id'];client.switch_account(account)
            write(client,'ISSUE_DEBIT_CARD',display_name='演示卡');write(client,'ACTIVATE_DEBIT_CARD',card_name='演示卡')
            write(client,'SIMULATE_CARD_DEPOSIT',card_name='演示卡',amount='10000')
            pin=f'{secrets.randbelow(1000000):06d}'
            client.request('/auth/payment-password',dict(login_password=password,payment_password=pin))
            enrollment=client.request('/auth/mfa/enroll',dict(login_password=password))
            authenticator=pyotp.parse_uri(enrollment['uri'])
            client.request('/auth/mfa/confirm',dict(enrollment_id=enrollment['enrollment_id'],code=authenticator.now()))
            shell.show_bank();w=shell.bank;w.resize(1440,900)
            wait(lambda:not w.busy and w.snapshot is not None and w.wealth_page.data is not None);idle()
            w.wealth_nav.click();page=w.wealth_page;page.tabs.setCurrentIndex(1)
            fields=dict(budget='2000',free_cash='6000',horizon_days='90',purpose='闲置资金',liquidity='可等待',loss='接受波动',
                income='稳定',debt='无压力',experience='有经验',priority='综合比较')
            for key,value in fields.items():
                f=page.fields[key]
                if isinstance(f,QLineEdit):f.setText(value)
                else:f.setCurrentIndex(f.findData(value))
            capture('questionnaire');page.save.click();approve()
            page.tabs.setCurrentIndex(0);capture('products')
            if live_model:
                w.toggle_assistant(True)
                for prompt in ['我刚填好了问卷，请比较这三款产品，告诉我哪些符合需求。',
                               '请帮我准备申购1000元北银7天27号A，先让我确认。']:
                    w.send(prompt);wait(lambda:not w.busy);idle()
                    report['cases'].append(dict(input=prompt,pending=bool(w.pending),reply=w.conversation.toPlainText()[-7000:]))
                    save();print('Recorded live AI case',len(report['cases']),flush=True)
                assert w.pending
                capture('assistant-confirm');approve();w.toggle_assistant(False)
            else:
                page.products.selectRow(1);page.buy_amount.setText('1000');page.buy.click()
                wait(lambda:not w.busy and w.pending is not None);capture('buy-confirm');approve()
            q=client.wealth();assert q['frozen_minor']==100000 and q['available_minor']==900000
            assert q['orders'][0]['product_code']=='YJ01251202A'
            page.tabs.setCurrentIndex(3);page.orders.selectRow(0);capture('submitted')
            for _ in range(2):page.step.click();approve()
            q=client.wealth();assert q['holdings_minor']==100000 and q['lots'][0]['redeemable_minor']==0
            page.tabs.setCurrentIndex(2);capture('locked-holding')
            page.sell_units.setText('400');page.sell.click();approve()
            assert client.wealth()['holdings_minor']==100000 and len(client.wealth()['orders'])==1
            report['cases'].append(dict(name='reject redemption before minimum holding period',status='PASSED'))
            page.tabs.setCurrentIndex(3);page.days.setCurrentText('7');page.advance.click();approve()
            if live_model:
                w.toggle_assistant(True)
                prompt='请查一下我的持仓，准备赎回400份北银7天27号A，先让我确认，不要推进演示时间。'
                w.send(prompt);wait(lambda:not w.busy);idle()
                report['cases'].append(dict(input=prompt,pending=bool(w.pending),reply=w.conversation.toPlainText()[-7000:]))
                save();print('Recorded live AI redemption case',flush=True)
                assert w.pending and w.pending.get('operation')=='REDEEM_WEALTH'
                capture('assistant-redeem-confirm');approve();w.toggle_assistant(False)
            else:
                page.tabs.setCurrentIndex(2);page.sell_units.setText('400');page.sell.click();approve()
            page.tabs.setCurrentIndex(3);page.orders.selectRow(0)
            for _ in range(2):page.step.click();approve()
            q=client.wealth();assert q['waiting_minor']==40000 and q['available_minor']==900000;capture('waiting-cash')
            page.step.click();approve();q=client.wealth()
            assert(q['available_minor'],q['holdings_minor'],q['waiting_minor'])==(940000,60000,0)
            capture('settled');w.show_page(2);capture('ledger')
            w.show_page(3);w.resize(1040,720);page.tabs.setCurrentIndex(0);capture('compact-products')
            assert w.main_scroll.horizontalScrollBar().maximum()==0
            report.update(status='COMPLETED',platform=app.platformName(),scale=w.devicePixelRatioF(),
                authentication='local login + transaction PIN + TOTP; native dialog; generated authenticator, not physical phone',
                final_available_minor=q['available_minor'],final_holdings_minor=q['holdings_minor'],orders=q['orders'])
            report['cases'].append(dict(name='1000 CNY subscribe / 400 units redeem / cash and holdings conservation',status='PASSED'))
            save()
        except Exception as exc:
            report.update(status='FAILED',error_type=type(exc).__name__);save();raise
        finally:
            if w:w.hide();w.deleteLater();app.processEvents()
            if shell:shell.hide();shell.deleteLater();app.processEvents()
            service.close()
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    parser.add_argument('--visible',action='store_true');parser.add_argument('--live-model',action='store_true')
    a=parser.parse_args();r=run(a.output,a.visible,a.live_model)
    print(json.dumps({k:v for k,v in r.items() if k not in {'orders','cases'}},ensure_ascii=False))
