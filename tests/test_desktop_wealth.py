"""Native Qt controls against a real local HTTP service and isolated SQLite."""
import time
import os
import pytest
from desktop.app import LocalService
from test_desktop import offline_env
from test_wealth import FIELDS


def test_wealth_controls_purchase_redeem_and_restart_view(tmp_path,monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM','offscreen')
    from PySide6.QtWidgets import QApplication,QLineEdit,QPushButton,QLabel
    from desktop.preview import PreviewWindow
    qt=QApplication.instance() or QApplication([])
    service=LocalService(env={**offline_env(),'BANKAGENT_DB_PATH':str(tmp_path/'wealth.sqlite3')})
    w=None
    def wait(predicate):
        end=time.monotonic()+20
        while time.monotonic()<end:
            qt.processEvents()
            if predicate():return
            time.sleep(.01)
        assert predicate(),w.status.text()+'\n'+w.history.toPlainText()
    def settle(expected):
        wait(lambda:not w.busy and w.pending is not None)
        assert expected in w.confirm_text.text()
        assert not w.wealth_page.buy.isEnabled()
        if w.pending['risk_level']=='RED':
            w.decide('approve',w.client.verification(w.pending)['demo_code'])
        else:w.approve.click()
        wait(lambda:not w.busy and w.pending is None)
        # The account refresh is queued after the decision result.
        qt.processEvents();wait(lambda:not w.busy)
    try:
        w=PreviewWindow(service.start());w.show()
        wait(lambda:not w.busy and w.snapshot is not None and w.wealth_page.data is not None)
        w.wealth_nav.click();page=w.wealth_page
        w.resize(1040,720);qt.processEvents()
        assert w.main_scroll.horizontalScrollBar().maximum()==0
        assert w.pages.currentWidget()==page
        assert page.products.rowCount()==10
        wait(lambda:page.questionnaire.isVisible())
        for key,value in FIELDS.items():
            field=page.fields[key]
            if isinstance(field,QLineEdit):field.setText(value)
            else:field.setCurrentIndex(field.findData(value))
        page.questionnaire.next.click();assert page.save.isVisible()
        page.save.click();settle('仅模拟需求筛选')
        wait(lambda:page.data['profile_valid'])
        # The saved-profile CTA must execute read-only screening in chat, not navigate.
        w.show_page(0);w.toggle_assistant(True)
        link=next(b for b in w.conversation.findChildren(QPushButton) if b.text()=='查看匹配产品 →')
        calls=[];original=w.client.form
        def tracked(action,fields):
            calls.append((action,fields));return original(action,fields)
        monkeypatch.setattr(w.client,'form',tracked)
        w.conversation.verticalScrollBar().setValue(0)
        link.click();link.click()  # A second click while busy must not send another request.
        wait(lambda:not w.busy and any('款产品符合' in l.text() for l in w.conversation.findChildren(QLabel)))
        wait(lambda:w.conversation.verticalScrollBar().value()==w.conversation.verticalScrollBar().maximum())
        assert calls==[('RECOMMEND_WEALTH',{})]
        assert w.assistant_box.isVisible() and w.pages.currentIndex()==0
        assert page.data['orders']==[] and page.data['available_minor']==500000 and w.pending is None
        assert any('通过初筛' in l.text() for l in w.conversation.findChildren(QLabel))
        # A historical CTA cannot overwrite a new pending confirmation.
        wait(lambda:not w.busy)  # Read receipt queues an account refresh after layout.
        w.prepare_wealth_form('SAVE_WEALTH_PROFILE',FIELDS)
        wait(lambda:not w.busy and w.pending is not None)
        pending=dict(w.pending);before=len(calls)
        w.toggle_assistant(True);link.click()
        assert w.pending==pending and len(calls)==before and not w.busy
        w.decide('reject');wait(lambda:not w.busy and w.pending is None)
        w.show_page(3);w.toggle_assistant(False);page.compare.click()
        assert w.assistant_box.isVisible()
        wait(lambda:not w.busy)
        assert calls[-1]==('RECOMMEND_WEALTH',{}) and w.pending is None
        monkeypatch.setattr(w.client,'form',original)
        w.show_page(3);w.toggle_assistant(False)
        page.tabs.setCurrentIndex(0);page.products.selectRow(0);page.buy_amount.setText('100')
        page.buy.click();settle('申购金额：100.00元')
        wait(lambda:page.orders.rowCount()==1)
        assert page.data['available_minor']==490000 and page.data['frozen_minor']==10000
        page.tabs.setCurrentIndex(3);page.demo_toggle.setChecked(True)
        for _ in range(2):page.step.click();settle('下一步')
        wait(lambda:page.data['holdings_minor']==10000)
        page.tabs.setCurrentIndex(2);page.lots.selectRow(0);page.sell_units.setText('40')
        page.sell.click();settle('赎回份额：40.00份')
        wait(lambda:page.orders.rowCount()==2)
        page.tabs.setCurrentIndex(3);page.orders.selectRow(0)
        for _ in range(3):page.step.click();settle('下一步')
        wait(lambda:page.data['available_minor']==494000 and page.data['holdings_minor']==6000)
        assert page.data['waiting_minor']==0
        assert '已到账' in page.order_text.toPlainText()
        w.ledger_nav.click();assert any(w.bills_page.table.item(i,2).text()=='赎回到账' for i in range(w.bills_page.table.rowCount()))
        w.choose_context('customer','zhang-wei')
        wait(lambda:not w.busy and w.snapshot and w.snapshot['current_customer_ref']=='zhang-wei' and page.data is not None)
        assert page.orders.rowCount()==0 and page.fields['budget'].text()==''
    finally:
        if w:
            w.close();w.deleteLater();qt.processEvents()
        service.close()


@pytest.mark.skipif(os.name!='nt',reason='Local DPAPI authenticator')
def test_authenticated_wealth_controls_remain_visible_after_red_approval(tmp_path):
    from scripts.audit_wealth import run
    report=run(tmp_path/'audit')
    assert report['status']=='COMPLETED'
    assert report['final_available_minor']==940000 and report['final_holdings_minor']==60000
