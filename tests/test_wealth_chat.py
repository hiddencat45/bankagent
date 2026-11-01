"""Wealth cards preserve receipt facts without authorizing transactions."""
from copy import deepcopy
import pytest
from bankagent.banking.wealth import PRODUCTS

NOTICE = ('已读取模拟业务结果，具体金额、筛选理由和订单状态见下方服务端回执。'
          '理财申请已提交不等于成交或到账；未核实真实渠道的在售和到账信息。')


@pytest.fixture
def chat(monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication
    from desktop.chat import ChatView
    app = QApplication.instance() or QApplication([])
    view = ChatView(); view.resize(800, 700); view.show()
    yield view, app
    view.close(); view.deleteLater(); app.processEvents()


def snapshot(valid=False):
    from test_wealth import ANSWERS
    return dict(operation='RECOMMEND_WEALTH', status='COMPLETED', data=dict(
        products=deepcopy(PRODUCTS), profile={'answers':ANSWERS} if valid else None, profile_valid=valid, recommendations=[],
        orders=[], lots=[], day='2026-11-01', available_minor=370001, frozen_minor=0,
        holdings_minor=0, waiting_minor=0))


def shown(view):
    from PySide6.QtWidgets import QLabel
    return '\n'.join(w.text() for w in view.findChildren(QLabel) if w.isVisible())


def test_missing_and_expired_profile_guide_without_recommending_or_writing(chat):
    from PySide6.QtWidgets import QPushButton
    from desktop.preview import PreviewWindow
    view, app = chat; receipt = snapshot(); original = deepcopy(receipt); actions = []
    view.wealth_opened.connect(lambda *args: actions.append(args))
    view.add_turn([('message', {'text': NOTICE}), ('card', {'type': 'result', 'payload': receipt})], PreviewWindow.summarize)
    app.processEvents()
    assert len(view.rows) == 1 and NOTICE not in shown(view)
    assert all(p['code'] not in shown(view) for p in PRODUCTS)
    view.findChild(QPushButton, 'wealthChatPrimary').click()
    assert actions == [('profile', {})] and receipt == original
    view.clear()
    view.add_turn([('message', {'text':PreviewWindow.summarize(receipt)}),
                   ('card', {'type':'result', 'payload':receipt})], PreviewWindow.summarize)
    app.processEvents(); assert len(view.rows) == 1  # Offline text is also a duplicate.
    view.clear(); receipt['data']['profile'] = {'expires_on': '2026-10-31'}
    view.add_receipt(receipt, PreviewWindow.summarize(receipt)); app.processEvents()
    assert '问卷已过期' in shown(view)
    assert next(b for b in view.findChildren(QPushButton, 'wealthChatPrimary') if b.isVisible()).text() == '更新我的需求'


def test_screening_reasons_and_amounts_are_receipt_facts(chat):
    from desktop.preview import PreviewWindow
    from PySide6.QtWidgets import QPushButton
    view, app = chat; receipt = snapshot(True)
    receipt['data']['recommendations'] = [dict(product_code=p['code'], eligible=i == 0,
        reasons=['预算与期限通过' if i == 0 else '不符合风险范围']) for i, p in enumerate(PRODUCTS)]
    view.add_receipt(receipt, PreviewWindow.summarize(receipt)); app.processEvents()
    assert '1 款产品' in shown(view) and shown(view).count('不符合风险范围') == 2
    actions=[];view.wealth_opened.connect(lambda *args:actions.append(args))
    next(b for b in view.findChildren(QPushButton) if b.text() == '查看产品详情 →').click()
    assert actions == [('product', {'code': PRODUCTS[0]['code']})]
    view.clear(); receipt['operation'] = 'QUERY_WEALTH'
    view.add_receipt(receipt, PreviewWindow.summarize(receipt)); app.processEvents()
    assert '3,700.01' in shown(view) and '0.00' in shown(view)


def test_waiting_cash_and_partial_fill_are_not_presented_as_full_settlement(chat):
    from desktop.preview import PreviewWindow
    view, app = chat
    receipt = dict(operation='ADVANCE_WEALTH_DEMO',status='COMPLETED',data=dict(order=dict(
        order_id='test-order', product_snapshot=PRODUCTS[1], side='SELL', state='WAITING_CASH',
        requested_minor=40000, filled_minor=20000, events=[dict(message='已确认200份，款项待到账。')])) )
    view.add_receipt(receipt, PreviewWindow.summarize(receipt)); app.processEvents()
    assert '部分成交' in shown(view) and '待到账' in shown(view)
    assert '申请赎回 400.00 份' in shown(view) and '已确认 200.00 份' in shown(view)
    assert '已完成' not in shown(view)


def test_clarification_and_failure_are_never_removed(chat):
    from desktop.preview import PreviewWindow
    view, app = chat; receipt = snapshot()
    view.add_turn([('card', {'type':'result', 'payload':receipt}),
                   ('message', {'text':'请问这笔钱多久不用？'}),
                   ('error', {'message':'查询失败，请重试'})], PreviewWindow.summarize)
    app.processEvents()
    assert '请问这笔钱多久不用？' in shown(view) and '查询失败，请重试' in shown(view)
    view.clear(); view.add_turn([('message', {'text':NOTICE})], PreviewWindow.summarize)
    app.processEvents(); assert NOTICE in shown(view)


def test_saved_profile_button_requests_fresh_recommendation(chat):
    from desktop.preview import PreviewWindow
    from PySide6.QtWidgets import QPushButton
    view,app=chat;actions=[]
    view.wealth_opened.connect(lambda *args:actions.append(args))
    receipt=dict(operation='SAVE_WEALTH_PROFILE',status='COMPLETED',
        data=dict(profile=dict(expires_on='2027-11-01')))
    view.add_receipt(receipt,PreviewWindow.summarize(receipt));app.processEvents()
    view.findChild(QPushButton,'wealthChatPrimary').click()
    assert actions==[('recommend',{})]
