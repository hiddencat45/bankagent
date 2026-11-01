"""Exercise the actual Qt/HTTP workflow on an isolated ledger and capture evidence."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]


def run(output, visible=False, scale=None, width=1280, height=850):
    if not visible:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    if scale:
        os.environ['QT_SCREEN_SCALE_FACTORS'] = str(scale)
    from PySide6.QtWidgets import QApplication, QPushButton
    from PySide6.QtCore import Qt, QPoint
    from PySide6.QtTest import QTest
    from desktop.app import LocalService
    from desktop.preview import PreviewWindow
    app = QApplication.instance() or QApplication([])
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith('BANKAGENT_MODEL_') and k != 'BANKAGENT_DB_PATH'}
    with TemporaryDirectory() as tmp:
        service = LocalService(env={**env, 'BANKAGENT_DB_PATH': str(Path(tmp) / 'bank.sqlite3')})
        window = None

        def settle():
            for _ in range(15):
                app.processEvents(); time.sleep(.01)

        def wait(predicate):
            until = time.monotonic() + 25
            while time.monotonic() < until:
                app.processEvents()
                if predicate():
                    settle()
                    if predicate():
                        return
                time.sleep(.01)
            raise AssertionError(window.status.text())

        def capture(name):
            settle()
            assert window.grab().save(str(output / (name + '.png')))

        try:
            window = PreviewWindow(service.start(), startup_customer='zhang-wei')
            window.resize(width, height); window.show()
            wait(lambda: not window.busy and window.snapshot is not None)
            root = window.centralWidget()
            assert root.rect().contains(window.orb.geometry())
            assert root.childAt(window.orb.geometry().center()) is window.orb
            capture('overview')
            QTest.mouseClick(window.orb, Qt.MouseButton.LeftButton); settle()
            assert window.assistant_box.welcome.isVisible() and not window.orb.isVisible()
            window.assistant_box.shortcut_buttons[1].click()
            assert window.input.text() == '我想转账' and not window.busy and not window.pending
            window.input.setText('先留一份\n未发送的草稿')
            window.ai_close.click(); window.orb.click()
            assert window.input.text() == '先留一份\n未发送的草稿'
            window.input.clear(); capture('welcome')
            # Historical demo sender has the predefined payees; do not modify Zhang Wei's data.
            window.ai_close.click(); window.choose_context('customer', 'primary')
            wait(lambda: not window.busy and window.snapshot and window.snapshot['current_customer_ref'] == 'primary')
            window.orb.click(); window.input.setText('本月账单')
            QTest.keyClick(window.input, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
            wait(lambda: not window.busy and '消费合计' in window.conversation.toPlainText())
            assert not window.assistant_box.welcome.isVisible()
            capture('conversation')
            link = next(b for b in window.conversation.findChildren(QPushButton) if b.text().startswith('查看相关交易'))
            transcript = window.conversation.toPlainText()
            link.click(); settle()
            assert window.pages.currentIndex() == 2 and window.bills_page.rows
            assert not window.assistant_box.isVisible()
            capture('bills')
            window.orb.click(); assert window.conversation.toPlainText() == transcript
            window.input.setText('给张伟转40元'); window.submit.click()
            wait(lambda: not window.busy and window.pending is not None)
            old = dict(window.pending)
            assert window.assistant_box.isVisible() and window.confirmation.isVisible()
            assert '40.00' in window.confirm_text.text() and '默认演示账户' in window.confirm_text.text()
            capture('confirmation')
            viewport = window.assistant_box.confirm_scroll.viewport()
            bounds = window.confirm_text.rect().translated(window.confirm_text.mapTo(viewport, QPoint(0, 0)))
            assert viewport.rect().contains(bounds), 'Confirmation content is clipped'
            panel = window.assistant_box
            scroll_bounds = panel.confirm_scroll.rect().translated(panel.confirm_scroll.mapTo(panel, QPoint(0, 0)))
            for control in (window.approve, window.edit, window.reject):
                bounds = control.rect().translated(control.mapTo(panel, QPoint(0, 0)))
                assert panel.rect().contains(bounds), 'Confirmation action is clipped'
                assert not scroll_bounds.intersects(bounds), f'Fixed actions overlap scrolling explanation: {scroll_bounds}, {bounds}'
            window.ai_close.click(); window.orb.click()
            assert window.pending == old
            assert window.balance_value.text() == '¥ 5,000.00'
            window.edit.click()
            wait(lambda: not window.busy and window.pending is None and window.amount.text() == '40.00')
            assert not window.assistant_box.isVisible()
            from urllib.error import HTTPError
            try:
                window.client.resume(old, 'approve')
                raise AssertionError('old confirmation remained valid')
            except HTTPError as exc:
                assert exc.code == 409
            window.amount.setText('30'); window.prepare_transfer.click()
            wait(lambda: not window.busy and window.pending is not None)
            window.orb.click(); window.approve.click()
            wait(lambda: not window.busy and window.pending is None and window.balance_value.text() == '¥ 4,970.00')
            capture('receipt')
            links = [b for b in window.conversation.findChildren(QPushButton) if b.text().startswith('查看相关交易')]
            links[-1].click(); settle()
            assert window.bills_page.table.currentRow() >= 0
            assert window.bills_page.rows[window.bills_page.page*20 + window.bills_page.table.currentRow()]['amount_minor'] == 3000
            window.orb.click(); window.send('给张伟转20元')
            wait(lambda: not window.busy and window.pending is not None)
            window.reject.click(); wait(lambda: not window.busy and window.pending is None)
            assert window.balance_value.text() == '¥ 4,970.00'
            # A long message remains readable; incoming messages do not jump a history reader.
            window.conversation.add_message('assistant', '这是一段用于验证换行的长中文说明。' * 140)
            settle(); bar = window.conversation.verticalScrollBar(); bar.setValue(0)
            window.conversation.add_message('assistant', '新消息到达，保留正在阅读的位置。'); settle()
            assert bar.value() == 0
            assert window.submit.isVisible() and window.input.isVisible()
            assert window.assistant_box.rect().contains(window.submit.mapTo(window.assistant_box, window.submit.rect().bottomRight()))
            window.new.click(); settle()
            assert not window.conversation.rows and window.assistant_box.welcome.isVisible()
            report = {'platform': app.platformName(), 'visible': visible, 'scale': window.devicePixelRatioF(),
                      'size': [window.width(), window.height()], 'model': 'offline rules',
                      'service': 'real HTTP, isolated SQLite', 'startup_customer': 'zhang-wei',
                      'transfer_sender': 'primary (explicit controlled switch)',
                      'before_minor': 500000, 'after_minor': 497000,
                      'steps': ['welcome', 'prefill only', 'draft retained', 'bills query -> exact result view',
                                '40 pending -> close/reopen -> modify invalidates old confirmation',
                                '30 confirmed -> selected transaction', '20 cancelled, no debit',
                                'long text and historical scroll preserved', 'new conversation clears draft/history']}
            (output / 'record.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(report, ensure_ascii=False), flush=True)
            return report
        finally:
            if window:
                window.close(); window.deleteLater(); app.processEvents()
            service.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--visible', action='store_true')
    parser.add_argument('--scale', type=float)
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=850)
    args = parser.parse_args()
    run(args.output, args.visible, args.scale, args.width, args.height)
