"""Explanations, evidence and failures remain visible in the conversation space."""
import pytest


def test_chat_explanation_visible_with_supporting_receipt(monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    pytest.importorskip('PySide6.QtWidgets')
    from PySide6.QtWidgets import QApplication, QPushButton, QLabel
    from desktop.chat import ChatView
    from desktop.preview import PreviewWindow
    app = QApplication.instance() or QApplication([])
    chat = ChatView()
    chat.resize(350, 400)
    chat.show()
    balance = {'operation': 'GET_BALANCE', 'status': 'COMPLETED', 'data': {'balance_minor': 296000}}
    reply = '您当前账户余额为 **2,960.00 元**（人民币）。'
    events = [('card', {'type': 'result', 'payload': balance}), ('message', {'text': reply}),
              ('done', {'status': 'COMPLETED'})]
    try:
        chat.add_message('user', '现在余额多少')
        chat.add_turn(events, PreviewWindow.summarize)
        app.processEvents()
        assert reply in chat.toPlainText()
        assert chat.rows[0][1].objectName() == 'userBubble'
        assert chat.rows[1][1].objectName() == 'assistantBubble'
        assert chat.rows[2][1].objectName() == 'receiptCard'
        assert chat.findChild(QPushButton, 'replyDetails') is None
        detail = next(l for l in chat.findChildren(QLabel) if l.text() == reply)
        assert not detail.isHidden()
        # Changing viewport width keeps content within the viewport; plain text is not HTML.
        chat.add_message('user', '<b>不要解释成HTML</b>' + '长消息' * 60)
        chat.resize(290, 400)
        app.processEvents()
        assert all(b.maximumWidth() < chat.viewport().width() for _, b in chat.rows)
        assert all(b.height() >= b.minimumSizeHint().height() for _, b in chat.rows)
        chat.clear()
        assert chat.toPlainText() == '' and chat.rows == []
        # A read result followed by a missing-information question must not hide the question.
        missing = events[:1] + [('message', {'text': '请问转给谁？'}), ('done', {'status': 'NEEDS_INPUT'})]
        chat.add_turn(missing, PreviewWindow.summarize)
        assert '请问转给谁？' in chat.toPlainText()
        chat.clear()
        failure = {'operation': 'TRANSFER', 'status': 'FAILED', 'error_code': 'INSUFFICIENT_BALANCE'}
        chat.add_turn([('card', {'type': 'result', 'payload': failure}),
                       ('error', {'message': '余额不足，未扣款'}), ('done', {'status': 'FAILED'})], PreviewWindow.summarize)
        assert '未扣款' in chat.toPlainText() and '成功' not in chat.toPlainText()
        assert all(b.objectName() == 'errorBubble' for _, b in chat.rows)
    finally:
        chat.close()
        chat.deleteLater()
        app.processEvents()
