"""Reproduce the approved ledger/orb UI on a disposable real HTTP ledger."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
from tempfile import TemporaryDirectory
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    parser.add_argument('--visible',action='store_true')
    args=parser.parse_args()
    if not args.visible:os.environ['QT_QPA_PLATFORM']='offscreen'
    from PySide6.QtWidgets import QApplication
    from desktop.preview import PreviewWindow
    from desktop.app import LocalService
    app=QApplication.instance() or QApplication([])
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    env={k:v for k,v in os.environ.items() if not k.startswith('BANKAGENT_MODEL_') and k!='BANKAGENT_DB_PATH'}
    with TemporaryDirectory() as tmp:
        service=LocalService(env={**env,'BANKAGENT_DB_PATH':str(Path(tmp)/'bank.sqlite3')})
        window=None
        def wait(predicate):
            until=time.monotonic()+20
            while time.monotonic()<until:
                app.processEvents()
                if predicate():return
                time.sleep(.01)
            raise AssertionError(window.status.text())
        def capture(name):
            # Allow queued account refresh and native layout/scroll ranges to settle.
            for _ in range(12):
                app.processEvents();time.sleep(.02)
            wait(lambda:not window.busy)
            app.processEvents();window.grab().save(str(output/name))
        try:
            window=PreviewWindow(service.start());window.show()
            wait(lambda:not window.busy and window.snapshot is not None)
            window.show_page(2); capture('ledger.png')
            window.orb.click()
            window.send('查询余额');wait(lambda:not window.busy and '5,000.00' in window.conversation.toPlainText())
            capture('assistant.png')
            window.input.setText('本月账单');window.submit.click();wait(lambda:not window.busy)
            window.ai_close.click()
            window.business_form('转账')
            window.recipient.setCurrentIndex(window.recipient.findData('张伟'));window.amount.setText('40')
            window.prepare_transfer.click();wait(lambda:not window.busy and window.pending is not None)
            window.approve.click();wait(lambda:not window.busy and window.pending is None and window.balance_value.text()=='¥ 4,960.00')
            window.show_page(2);window.bills_page.search.setText('张伟');capture('filtered-transfer.png')
            assert len(window.bills_page.rows)==1 and window.bills_page.rows[0]['amount_minor']==4000
            window.orb.click();window.ai_expand.click();capture('assistant-expanded.png')
            report={'platform':app.platformName(),'visible':args.visible,'logical_size':[window.width(),window.height()],
                'scale':window.devicePixelRatioF(),'model':'offline rules','service':'real HTTP / isolated SQLite',
                'balance_after_minor':496000,'filtered_transfer':window.bills_page.rows,
                'steps':['open ledger','toggle translucent orb','assistant queries balance: bubble and receipt card', 'assistant queries current-month bills',
                    'form transfer 40, approve','ledger refresh, search 张伟, exactly one outgoing 4000 minor']}
            (output/'record.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({k:v for k,v in report.items() if k!='filtered_transfer'},ensure_ascii=False))
        finally:
            if window:window.close();window.deleteLater();app.processEvents()
            service.close()

if __name__=='__main__':main()
