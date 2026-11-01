"""Live AI + native desktop rehearsal on a temporary ledger; never touches daily accounts."""
import argparse,os,sys,time,json
from pathlib import Path
from tempfile import TemporaryDirectory
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from desktop.app import LocalService,desktop_environment
from desktop.preview import PreviewWindow
from PySide6.QtWidgets import QApplication,QPushButton,QLabel
app=QApplication([])
parser=argparse.ArgumentParser()
parser.add_argument('--output',required=True,help='New evidence directory; calls the configured real model')
args=parser.parse_args()
out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
if (out/'live-native.json').exists():raise RuntimeError('Preserve previous evidence')
configured=desktop_environment()
env={k:v for k,v in os.environ.items() if not k.startswith('BANKAGENT_') and k!='QT_QPA_PLATFORM'}
env.update({k:v for k,v in configured.items() if k.startswith('BANKAGENT_MODEL_')})
assert env.get('BANKAGENT_MODEL_API_KEY')
report={'mode':'live model + Windows native Qt + TCP HTTP','ledger':'temporary SQLite','turns':[]}
def save():(out/'live-native.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
with TemporaryDirectory(dir=ROOT/'.desktop-tmp') as temp:
 service=LocalService(env={**env,'BANKAGENT_DB_PATH':str(Path(temp)/'ledger.sqlite3')})
 w=None
 def wait(predicate,seconds=70):
  end=time.monotonic()+seconds
  while time.monotonic()<end:
   app.processEvents()
   if predicate():
    for _ in range(6):app.processEvents();time.sleep(.03)
    return
   time.sleep(.02)
  raise AssertionError('UI timeout: '+w.status.text())
 def capture(name):
  for _ in range(12):app.processEvents();time.sleep(.04)
  w.grab().save(str(out/(name+'.png')))
  w.assistant_box.grab().save(str(out/(name+'-chat.png')))
 def latest():return w.conversation.toPlainText().split('有度：')[-1]
 def send(text):
  print('Sending next synthetic answer',flush=True)
  w.send(text);wait(lambda:not w.busy)
  report['turns'].append({'user':text,'transcript_tail':latest(),'pending':bool(w.pending)})
  save()
  assert '暂时不可用' not in latest() and '无法使用的查询' not in latest(),latest()
 try:
  w=PreviewWindow(service.start());w.resize(1280,850);w.show()
  wait(lambda:not w.busy and w.wealth_page.data is not None)
  assert w.mode=='真实模型'
  w.input.setText('保留尚未发送的草稿')
  w.wealth_nav.click();wait(lambda:not w.busy and len(w.conversation.rows)>0)
  assert w.assistant_box.isVisible() and not w.wealth_page.questionnaire.isVisible()
  assert w.input.text()=='保留尚未发送的草稿'
  report['turns'].append({'user':'首次进入理财自动开启需求对话','transcript_tail':latest()});save();capture('first-question')
  send('我想拿一万元理财，已经扣除了生活开销、近期还款并留足应急备用金，没有借款也没有还款压力。')
  capture('question')
  send('2027年11月1日要用这笔钱，可以提前赎回并留出到账时间。')
  send('我只想看低风险产品，没有买过非保本理财，亏损或延期不会影响生活和还款，这次风险优先。')
  for _ in range(4):
   if w.pending:break
   q=latest()
   if '接受本金亏损' in q or '亏损态度' in q or '低风险也不保本' in q:send('能接受小幅亏损，但这次只考虑仅低风险的比较范围。')
   elif '生活' in q or '还款' in q:send('这笔钱亏损或者延期到账都不会影响我的生活和还款。')
   elif '经验' in q:send('尚不了解，也没买过非保本理财。')
   elif '更在意' in q:send('这次风险优先。')
   else:raise AssertionError('Unexpected question: '+q)
  assert w.pending and w.pending['operation']=='SAVE_WEALTH_PROFILE'
  assert w.client.wealth()['profile'] is None
  send('先把金额改为五千元，其他答案不变。')
  assert w.pending and '5000.00' in w.confirm_text.text()
  capture('confirm')
  w.approve.click();wait(lambda:not w.busy and w.pending is None)
  wait(lambda:not w.busy and w.wealth_page.data['profile_valid'])
  data=w.client.wealth()
  assert data['profile']['answers']['budget_minor']==500000
  assert data['needs_deadline']=='2027-11-01'
  assert data['orders']==[] and data['available_minor']==500000 and data['frozen_minor']==0
  assert sum(r['eligible'] for r in data['recommendations'])==2
  capture('recommendations')
  for _,bubble in w.conversation.rows:
   if bubble.objectName()=='wealthChat':bubble.grab().save(str(out/'recommendation-card.png'))
  w.toggle_assistant(False);w.wealth_page.edit_profile.click();wait(lambda:w.wealth_page.questionnaire.isVisible())
  assert w.wealth_page.fields['budget'].text()=='5000.00' and w.wealth_page.fields['need_on'].text()=='2027-11-01'
  w.wealth_page.questionnaire.grab().save(str(out/'edit-form.png'));w.wealth_page.questionnaire.reject()
  w.resize(1040,720);w.toggle_assistant(True);capture('compact')
  assert w.main_scroll.horizontalScrollBar().maximum()==0 and w.conversation.horizontalScrollBar().maximum()==0
  report.update(status='PASSED',platform=app.platformName(),scale=w.devicePixelRatioF(),
   saved_answers=data['profile']['answers'],matches=sum(r['eligible'] for r in data['recommendations']),
   orders=0,balance=500000,form_edit='saved values preserved',draft='preserved by first-use entry')
  save();print('LIVE_NATIVE_PASSED',flush=True)
 except Exception as exc:
  report.update(status='FAILED',error=str(exc));save();raise
 finally:
  if w:w.close();w.deleteLater();app.processEvents()
  service.close()
