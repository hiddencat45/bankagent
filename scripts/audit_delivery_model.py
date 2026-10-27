"""Explicit live-provider audit on disposable ledgers. Record failures without retries.

Only public business receipts are saved, never model reasoning or credentials.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from desktop.app import desktop_environment
from bankagent.agent.model_providers import build_model_from_env
from bankagent.api.server import create_app
from fastapi.testclient import TestClient
from check_task_model import frames


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise SystemExit('Choose a new output: prior failures must be retained.')
    output.parent.mkdir(parents=True, exist_ok=True)
    for k, v in desktop_environment().items():
        if k.startswith('BANKAGENT_MODEL_'):
            os.environ[k] = v
    model = build_model_from_env()
    report = {'mode': 'live provider / TestClient ASGI / isolated SQLite', 'cases': []}
    def save():
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if model is None:
        report['not_run'] = 'No model configuration'
        save()
        return 2
    def safe(value):
        if isinstance(value, dict):
            return {k: safe(v) for k, v in value.items() if k not in {'challenge_id', 'operation_hash', 'token'}}
        if isinstance(value, list):
            return [safe(v) for v in value]
        return value
    try:
        with TemporaryDirectory(prefix='delivery-audit-') as tmp:
            for name in ['账单追问', '客户创建', '卡生命周期', '双边多步骤', '修改取消最新请求', '批量', '对象解析', '理财推荐']:
                case = {'name': name, 'steps': [], 'result': 'RUNNING'}
                report['cases'].append(case)
                path = Path(tmp) / (name + '.sqlite3')
                try:
                    with TestClient(create_app(demo=True, query_model=model, database_path=path), base_url='http://localhost') as c:
                        auth = {'Authorization': 'Bearer ' + c.post('/demo/session').json()['token']}
                        thread = None
                        def chat(message, continuation=True):
                            nonlocal thread
                            started = time.monotonic()
                            out = frames(c.post('/agent/chat', headers=auth, json={'message': message,
                                'thread_id': thread if continuation else None}))
                            thread = out[0]['thread_id']
                            case['steps'].append({'input': message, 'seconds': round(time.monotonic()-started, 2), 'events': safe(out)})
                            save()
                            print(name, message, out[-1]['status'], flush=True)
                            return out
                        def approve(out, operation, expected=None):
                            card = next((f['payload'] for f in out if f.get('type') == 'confirm'), None)
                            assert card and card['operation'] == operation, 'missing or unexpected confirmation'
                            if expected:
                                assert all(card.get(k) == v for k, v in expected.items()), 'confirmation differs from request'
                            assert card['risk_level'] == 'YELLOW', 'independent authentication required'
                            done = frames(c.post('/agent/chat', headers=auth, json={'thread_id': thread,
                                'resume': {'challenge_id': card['challenge_id'], 'decision': 'approve'}}))
                            case['steps'].append({'input': '批准所列确认', 'events': safe(done)})
                            save()
                            return done
                        def receipt(out, operation):
                            rows = [f['payload'] for f in out if f.get('type') == 'result' and f['payload']['operation'] == operation]
                            assert rows, 'no actual ' + operation + ' receipt'
                            return rows[-1]
                        def balance():
                            rows = c.get('/bank/accounts', headers=auth).json()
                            return next(r['balance_minor'] for r in rows['accounts'] if r['account_ref'] == rows['current_account_ref'])
                        if name == '账单追问':
                            for message, category, threshold in [('这个月的钱主要用在哪些地方？', None, None),
                                    ('吃饭这一类单独给我看看', '餐饮', None), ('其中一笔超过一百块的留下', '餐饮', 10000),
                                    ('金额条件撤掉，换成出行那一类', '交通', None)]:
                                r = receipt(chat(message), 'QUERY_BILLS')
                                assert r['data']['filters']['category'] == category
                                assert r['data']['filters']['amount_gt_minor'] == threshold
                        elif name == '客户创建':
                            out = chat('新增一个虚构客户叫小禾，首个账户取名日用账户。')
                            r = receipt(approve(out, 'CREATE_DEMO_CUSTOMER'), 'CREATE_DEMO_CUSTOMER')
                            assert r['status'] == 'COMPLETED'
                            response = c.post('/demo/customer-session', headers=auth, json={'customer_ref': r['data']['customer_ref']})
                            auth = {'Authorization': 'Bearer ' + response.json()['token']}
                            thread = None
                            assert balance() == 100000
                            r = receipt(approve(chat('申请一张借记卡，叫小禾日常卡'), 'ISSUE_DEBIT_CARD'), 'ISSUE_DEBIT_CARD')
                            assert r['data']['status'] == 'PENDING_ACTIVATION'
                            r = receipt(approve(chat('把刚才的小禾日常卡激活'), 'ACTIVATE_DEBIT_CARD'), 'ACTIVATE_DEBIT_CARD')
                            assert r['data']['status'] == 'ACTIVE'
                        elif name == '卡生命周期':
                            receipt(approve(chat('帮我办一张叫旅行卡的借记卡'), 'ISSUE_DEBIT_CARD'), 'ISSUE_DEBIT_CARD')
                            r = receipt(approve(chat('用旅行卡在演示书店花12元，归到购物'), 'PAY_BY_CARD'), 'PAY_BY_CARD')
                            assert r['error_code'] == 'CARD_NOT_ACTIVE'
                            assert receipt(approve(chat('现在开通旅行卡，让它可以使用', False), 'ACTIVATE_DEBIT_CARD'), 'ACTIVATE_DEBIT_CARD')['status'] == 'COMPLETED'
                            assert receipt(approve(chat('把旅行卡临时冻结', False), 'FREEZE_CARD'), 'FREEZE_CARD')['status'] == 'COMPLETED'
                            r = receipt(approve(chat('旅行卡在演示书店支付12元，算购物', False), 'PAY_BY_CARD'), 'PAY_BY_CARD')
                            assert r['status'] == 'REJECTED'
                            receipt(approve(chat('恢复旅行卡使用', False), 'UNFREEZE_CARD'), 'UNFREEZE_CARD')
                            r = receipt(approve(chat('用旅行卡给演示书店付十二块，分类购物', False), 'PAY_BY_CARD'), 'PAY_BY_CARD')
                            assert r['status'] == 'COMPLETED' and balance() == 498800
                        elif name == '双边多步骤':
                            out = chat('看看我还有多少钱，如果够，就给张伟汇三十七块五毛，最后列出这笔流水。')
                            receipt(out, 'GET_BALANCE')
                            done = approve(out, 'TRANSFER', {'recipient': '张伟', 'amount_minor': 3750})
                            receipt(done, 'QUERY_BILLS')
                            assert balance() == 496250
                            sender = c.get('/bank/bills', headers=auth).json()['data']['transactions']
                            response = c.post('/demo/customer-session', headers=auth, json={'customer_ref': 'zhang-wei'})
                            auth = {'Authorization': 'Bearer ' + response.json()['token']}
                            assert balance() == 43750
                            incoming = c.get('/bank/bills', headers=auth).json()['data']['transactions']
                            transfer = next(x for x in sender if x['kind'] == 'TRANSFER_OUT')
                            assert any(x.get('transfer_id') == transfer['transfer_id'] for x in incoming)
                            case['both_sides_minor'] = [496250, 43750]
                        elif name == '修改取消最新请求':
                            out = chat('向张伟汇四十六元')
                            old = next(f['payload'] for f in out if f.get('type') == 'confirm')
                            revised = chat('数额换成二十九块，收款人不变')
                            assert next(f['payload'] for f in revised if f.get('type') == 'confirm')['amount_minor'] == 2900
                            receipt(chat('先别付，我要知道现在余额'), 'GET_BALANCE')
                            assert balance() == 500000
                            cancelled = chat('这一笔彻底作罢')
                            assert cancelled[-1]['status'] == 'REJECTED'
                            stale = c.post('/agent/chat', headers=auth, json={'thread_id': thread,
                                'resume': {'challenge_id': old['challenge_id'], 'decision': 'approve'}})
                            assert stale.status_code == 409 and balance() == 500000
                        elif name == '批量':
                            out = chat('张伟收十八块，李娜收二十三块五，请合成一批让我核对，完成后查回执。')
                            card = next(f['payload'] for f in out if f.get('type') == 'confirm')
                            assert [(x['recipient'], x['amount_minor']) for x in card['items']] == [('张伟', 1800), ('李娜', 2350)]
                            done = approve(out, 'BATCH_TRANSFER', {'total_minor': 4150, 'atomic': True})
                            assert receipt(done, 'BATCH_TRANSFER')['data']['committed'] is True
                            assert balance() == 495850
                            case['batch_receipts'] = c.get('/bank/transfer-batches', headers=auth).json()
                        elif name == '对象解析':
                            out = chat('把我的借记卡列一下')
                            receipt(out, 'QUERY_CARDS')
                            out = chat('把第一张临时冻结')
                            card = next(f['payload'] for f in out if f.get('type') == 'confirm')
                            assert card['operation'] == 'FREEZE_CARD'
                            case['resolved_confirmation'] = safe(card)
                            # Do not approve an ambiguous reference during this audit.
                            chat('取消刚才的冻结')
                        else:
                            out = chat('我能拿出两千元，三个月后要用，不愿承受本金损失，有什么理财适合我？')
                            case['result'] = 'UNIMPLEMENTED'
                            case['reason'] = 'No investment profile/catalog/recommendation backend or registered tool; text is not a product recommendation receipt.'
                        case['final_balance_minor'] = balance()
                    # Restart same database, read through public customer/accounts/bills endpoints.
                    with TestClient(create_app(demo=True, database_path=path), base_url='http://localhost') as reopened:
                        h = {'Authorization': 'Bearer ' + reopened.post('/demo/session').json()['token']}
                        case['restart_accounts'] = reopened.get('/bank/accounts', headers=h).json()
                        case['restart_batches'] = reopened.get('/bank/transfer-batches', headers=h).json()
                    if case['result'] == 'RUNNING':
                        case['result'] = 'PASS'
                except Exception as exc:
                    case['result'] = 'FAIL'
                    case['error_type'] = type(exc).__name__
                    # Assertion text is ours; provider exceptions may contain secrets.
                    if isinstance(exc, AssertionError):
                        case['reason'] = str(exc)
                save()
                print(name, case['result'], flush=True)
    finally:
        model.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
