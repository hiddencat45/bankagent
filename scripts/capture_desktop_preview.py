"""Capture the actual two-view Qt application using a disposable real HTTP ledger."""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--visible', action='store_true')
    parser.add_argument('--hold-seconds', type=int, default=0)
    args = parser.parse_args()
    if not args.visible:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    from PySide6.QtWidgets import QApplication
    from desktop.app import LocalService
    from desktop.preview import PreviewWindow
    app = QApplication([])
    if not args.visible:
        from PySide6.QtGui import QFontDatabase
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith('BANKAGENT_MODEL_') and k != 'BANKAGENT_DB_PATH'}
    with TemporaryDirectory(prefix='bankagent-preview-') as tmp:
        env['BANKAGENT_DB_PATH'] = str(Path(tmp) / 'preview.sqlite3')
        service = LocalService(env=env)
        window = None
        def wait(predicate):
            until = time.monotonic() + 25
            while time.monotonic() < until:
                app.processEvents()
                if predicate():
                    return
                time.sleep(.01)
            raise RuntimeError('Preview did not reach expected state')
        def capture(name):
            for _ in range(12):
                app.processEvents()
                time.sleep(.02)
            image = window.grab()
            assert image.save(str(output / name))
            return {'width_px': image.width(), 'height_px': image.height()}
        try:
            window = PreviewWindow(service.start())
            screen = window.screen()
            area = screen.availableGeometry()
            if args.visible:
                window.resize(min(1280, area.width() - 60), min(850, area.height() - 80))
            window.statusBar().showMessage('隔离演示账本 · 本次预览不会修改日常账本')
            window.show()
            wait(lambda: not window.busy and window.snapshot is not None)
            window.card_list.setCurrentRow(0)
            shots = {'overview': capture('overview.png')}
            window.go_transfer.click()
            window.recipient.setCurrentIndex(window.recipient.findData('张伟'))
            window.amount.setText('40')
            window.overview_nav.click()
            window.transfer_nav.click()
            assert window.amount.text() == '40'
            shots['form'] = capture('transfer-form.png')
            window.prepare_transfer.click()
            wait(lambda: not window.busy and window.pending is not None)
            window.edit.click()
            wait(lambda: not window.busy and window.pending is None and window.amount.isEnabled())
            window.amount.setText('30')
            window.prepare_transfer.click()
            wait(lambda: not window.busy and window.pending is not None)
            shots['confirmation'] = capture('transfer-confirm.png')
            window.approve.click()
            wait(lambda: not window.busy and window.pending is None and window.balance_value.text() == '¥ 4,970.00')
            window.send('查询余额')
            wait(lambda: not window.busy and '4,970.00' in window.conversation.toPlainText())
            shots['result'] = capture('transfer-result.png')
            metadata = {'platform': app.platformName(), 'visible': args.visible,
                        'window_logical': [window.width(), window.height()], 'device_pixel_ratio': window.devicePixelRatioF(),
                        'logical_dpi': screen.logicalDotsPerInch(), 'screen_logical': [screen.size().width(), screen.size().height()],
                        'screenshots': shots, 'model': 'offline deterministic for UI acceptance',
                        'operation': ['select 张伟, enter 40', 'back to overview and return: input retained',
                                      'prepare 40, return to edit: old confirmation cancelled',
                                      'prepare 30, approve once', 'query balance through assistant'],
                        'balance_minor_before': 500000, 'balance_minor_after': 497000,
                        'ledger_rows': window.snapshot['ledger']['transactions']}
            (output / 'record.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({k: v for k, v in metadata.items() if k != 'ledger_rows'}, ensure_ascii=False), flush=True)
            if args.visible and args.hold_seconds:
                until = time.monotonic() + args.hold_seconds
                while time.monotonic() < until and not window.closed.is_set():
                    app.processEvents()
                    time.sleep(.02)
        finally:
            if window:
                window.close()
                window.deleteLater()
                app.processEvents()
            service.close()


if __name__ == '__main__':
    main()
