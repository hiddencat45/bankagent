"""Native shortlist rehearsal via real HTTP and a temporary ledger; no real model needed."""
import argparse,json,os,sys,time
from pathlib import Path
from tempfile import TemporaryDirectory
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from desktop.app import LocalService
from desktop.preview import PreviewWindow
from PySide6.QtWidgets import QApplication,QPushButton,QFrame


def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if (output/'record.json').exists():raise ValueError('Choose a new output directory')
    app=QApplication.instance() or QApplication([])
    env={k:v for k,v in os.environ.items() if not k.startswith('BANKAGENT_') and k!='QT_QPA_PLATFORM'}
    report=dict(transport='real TCP HTTP',ledger='temporary SQLite',model='offline rules; ranking from trusted backend',cases=[])
    with TemporaryDirectory(dir=ROOT/'.desktop-tmp') as temp:
        service=LocalService(env={**env,'BANKAGENT_DB_PATH':str(Path(temp)/'ledger.sqlite3')});window=None
        def wait(predicate):
            end=time.monotonic()+30
            while time.monotonic()<end:
                app.processEvents()
                if predicate():
                    for _ in range(6):app.processEvents();time.sleep(.03)
                    return
                time.sleep(.02)
            raise AssertionError('Native operation timed out')
        try:
            window=PreviewWindow(service.start());window.resize(1280,850);window.show()
            wait(lambda:not window.busy and window.wealth_page.data is not None)
            for priority,label,expected in [('风险优先','risk',['2119987003A','5811323020']),
                                             ('综合比较','balanced',['2119987003A','5811223114'])]:
                fields=dict(budget='20000',free_cash='30000',horizon_days='1095',purpose='闲置资金',liquidity='可等待',
                    loss='接受波动',income='稳定',debt='无压力',experience='无经验',priority=priority)
                window.prepare_wealth_form('SAVE_WEALTH_PROFILE',fields)
                wait(lambda:not window.busy and window.pending is not None)
                window.approve.click();wait(lambda:not window.busy and window.pending is None)
                window.conversation.clear();window.prepare_wealth_form('RECOMMEND_WEALTH',{})
                wait(lambda:not window.busy)
                data=window.client.wealth();selected=[r for r in data['recommendations'] if r['recommendation_rank']]
                assert [r['product_code'] for r in selected]==expected
                assert sum(r['eligible'] for r in data['recommendations'])==10
                assert data['orders']==[] and data['available_minor']==500000 and data['frozen_minor']==0
                cards=window.conversation.findChildren(QFrame,'wealthChatProduct')
                assert sum(c.isVisible() for c in cards)==2
                bubbles=[b for _,b in window.conversation.rows if b.objectName()=='wealthChat']
                bubbles[-1].grab().save(str(output/(label+'-recommendations.png')))
                window.assistant_box.grab().save(str(output/(label+'-chat.png')))
                toggle=next(b for b in window.conversation.findChildren(QPushButton) if b.isVisible() and b.text()=='查看 8 款其他备选')
                toggle.click();app.processEvents();assert sum(c.isVisible() for c in cards)==10
                toggle.click();app.processEvents();assert sum(c.isVisible() for c in cards)==2
                report['cases'].append(dict(priority=priority,eligible=10,recommended=selected,visible_cards=2,other_cards=8))
            window.resize(1040,720);wait(lambda:True)
            window.assistant_box.grab().save(str(output/'compact-chat.png'))
            assert window.conversation.horizontalScrollBar().maximum()==0
            report.update(status='PASSED',platform=app.platformName(),scale=window.devicePixelRatioF())
            (output/'record.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print('Native recommendations passed: 10 eligible -> 2 ranked, preference changes results, no orders or money changes')
        finally:
            if window:window.close();window.deleteLater();app.processEvents()
            service.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    run(parser.parse_args().output)
