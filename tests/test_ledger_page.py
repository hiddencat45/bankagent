import time
import pytest
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from test_api_http import login
from desktop.app import LocalService
from test_desktop import offline_env


def test_ledger_dates_and_session_scope():
    with TestClient(create_app(demo=True),base_url='http://localhost') as c:
        h=login(c)
        default=c.get('/bank/bills',headers=h).json()
        data=default['data']
        assert c.get('/bank/bills',headers=h,params={'start':data['start'],'end':data['end']}).json()==default
        for params in [{'start':'bad','end':data['end']},{'start':data['start']},{'user_id':'user-002'},{'account_id':'account-002'}]:
            assert c.get('/bank/bills',headers=h,params=params).status_code==400
        assert c.get('/bank/bills',headers=h,params={'start':'2025-01-01','end':'2026-10-01'}).json()['error_code']=='INVALID_DATE_RANGE'
        empty=c.get('/bank/bills',headers=h,params={'start':'2020-01-01','end':'2020-02-01'}).json()['data']
        assert empty['transactions']==[] and empty['total_minor']==0
        assert c.get('/bank/bills').status_code==401


def test_ledger_filters_orb_transfer_refresh_identity_and_failure(tmp_path,monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM','offscreen')
    from PySide6.QtWidgets import QApplication
    from desktop.preview import PreviewWindow
    qt=QApplication.instance() or QApplication([])
    env={**offline_env(),'BANKAGENT_DB_PATH':str(tmp_path/'ledger.sqlite3')}
    service=LocalService(env=env); window=None
    def wait(predicate):
        end=time.monotonic()+20
        while time.monotonic()<end:
            qt.processEvents()
            if predicate():return
            time.sleep(.01)
        assert predicate(),window.status.text()
    try:
        window=PreviewWindow(service.start()); window.show()
        wait(lambda:not window.busy and window.snapshot is not None)
        window.show_page(2); bills=window.bills_page
        assert not window.assistant_box.isVisible()
        window.orb.click(); assert window.assistant_box.isVisible()
        assert '默认演示账户' in window.ai_context.text()
        window.ai_close.click(); assert not window.assistant_box.isVisible()
        original=list(bills.rows)
        bills.details(0)
        assert bills.rows[0]['transaction_id'] in bills.refs.toPlainText()
        bills.refs_toggle.click(); assert bills.refs.isVisible()
        bills.expense_tab.click(); assert bills.rows and all(r['kind']=='EXPENSE' for r in bills.rows)
        assert not bills.refs.toPlainText() and not bills.refs_toggle.isChecked()
        expense=sum(r['amount_minor'] for r in bills.rows)
        assert expense==window.snapshot['ledger']['total_minor']
        bills.search.setText('不存在的商户'); assert bills.rows==[] and '没有交易' in bills.note.text()
        bills.search.clear(); bills.all_tab.click()
        bills.month.setCurrentIndex(1); wait(lambda:not window.busy)
        assert not bills.rows and bills.detail_amount.text()=='—'
        bills.reset.click(); wait(lambda:not window.busy)
        assert len(bills.rows)==len(original) and bills.month.currentIndex()==0
        bills.table.setCurrentCell(0,0)
        assert bills.rows[0]['transaction_id'] in bills.refs.toPlainText()
        assert '0.00' in bills.totals[1].text()
        assert format(expense/100,',.2f') in bills.totals[2].text()
        window.business_form('转账'); window.recipient.setCurrentIndex(window.recipient.findData('张伟')); window.amount.setText('40')
        window.prepare_transfer.click(); wait(lambda:not window.busy and window.pending is not None)
        window.approve.click(); wait(lambda:not window.busy and window.pending is None and any(r['kind']=='TRANSFER_OUT' for r in bills.rows))
        bills.search.setText('张伟'); assert len(bills.rows)==1 and bills.rows[0]['amount_minor']==4000
        bills.focus_receipt({'transaction_id':bills.rows[0]['transaction_id']})
        assert '40.00' in bills.detail_amount.text() and '张伟' in bills.detail_values['对方 / 商户'].text()
        assert '40.00' in bills.totals[1].text() and '0.00' in bills.totals[2].text()
        bills.search.clear(); assert len(bills.rows)==len(original)+1
        window.send('本月账单'); wait(lambda:not window.busy)
        assert str(expense//100) in window.conversation.toPlainText().replace(',','')
        with monkeypatch.context() as failing:
            failing.setattr(window.client,'ledger',lambda *args:(_ for _ in ()).throw(TimeoutError()))
            window.load_ledger(); wait(lambda:not window.busy)
            assert bills.table.rowCount()==0 and '异常' in bills.note.text()
            assert all(label.text()=='—' for label in bills.totals)
            assert not bills.refs.toPlainText() and '选择一笔' in bills.detail_body.text()
        window.load_ledger(); wait(lambda:not window.busy and bills.data is not None)
        from PySide6.QtCore import QDate
        bills.start.setDate(QDate(2020,1,1)); bills.end.setDate(QDate(2020,1,31))
        bills.query.click(); wait(lambda:not window.busy)
        assert bills.rows==[] and bills.data['end']=='2020-02-01'
        bills.end.setDate(QDate(2026,10,31))
        window.load_accounts(); wait(lambda:not window.busy)
        assert '366' in bills.note.text() and bills.data is None
        assert window.balance_value.text()=='¥ 4,960.00'
        bills.reset.click(); wait(lambda:not window.busy)
        assert len(bills.rows)==len(original)+1
        bills.expense_tab.click()
        window.customers.setCurrentIndex(window.customers.findData('zhang-wei')); window.switch_customer.click()
        wait(lambda:not window.busy and window.snapshot and window.snapshot['current_customer_ref']=='zhang-wei')
        assert '张伟' in window.ai_context.text()
        assert bills.all_tab.isChecked() and bills.kind.isEnabled()
        assert any(r['kind']=='TRANSFER_IN' and r['amount_minor']==4000 for r in bills.rows)
        assert not any(r['kind']=='TRANSFER_OUT' for r in bills.rows)
    finally:
        if window:window.close();window.deleteLater();qt.processEvents()
        service.close()
