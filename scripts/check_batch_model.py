"""Live model batch acceptance. Explicitly isolated ledger; no user bank database."""
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / 'src')]
from check_task_model import frames
from desktop.app import desktop_environment
from bankagent.agent.model_providers import build_model_from_env
from bankagent.api.server import create_app
from fastapi.testclient import TestClient


def main():
    for key, value in desktop_environment().items():
        if key.startswith('BANKAGENT_MODEL_'):
            os.environ[key] = value
    model = build_model_from_env()
    if model is None:
        print('SKIP: model not configured')
        return 2
    try:
        with TemporaryDirectory() as tmp:
            with TestClient(create_app(demo=True, query_model=model, database_path=Path(tmp)/'batch.sqlite3'), base_url='http://localhost') as c:
                auth = {'Authorization': 'Bearer ' + c.post('/demo/session').json()['token']}
                def chat(text, thread=None):
                    return frames(c.post('/agent/chat', headers=auth, json={'message': text, 'thread_id': thread}))
                def card(out, amounts):
                    assert out[-1]['status'] == 'AWAITING_CONFIRMATION', out[-1]['status']
                    row = next(f['payload'] for f in out if f.get('type') == 'confirm')
                    assert row['operation'] == 'BATCH_TRANSFER' and row['atomic'] is True
                    assert [(r['recipient'], r['amount_minor']) for r in row['items']] == list(zip(['张伟', '李娜'], amounts))
                    assert row['total_minor'] == sum(amounts)
                    return row
                for text, amounts in [('给张伟40元、李娜25元，一次确认整批办理，办完查批量回执。', [4000, 2500]),
                                      ('请把十块钱汇给张伟，二十块钱汇给李娜，作为一批确认，完成后核对回执。', [1000, 2000])]:
                    out = chat(text)
                    row = card(out, amounts)
                    print('prepared atomic list:', amounts, 'total', row['total_minor'], flush=True)
                    result = frames(c.post('/agent/chat', headers=auth, json={'thread_id': out[0]['thread_id'],
                        'resume': {'challenge_id': row['challenge_id'], 'decision': 'approve'}}))
                    receipts = [f['payload'] for f in result if f.get('type') == 'result']
                    print('observed:', result[-1]['status'], [(r['operation'], r['status']) for r in receipts], [f.get('code') for f in result if f.get('code')], flush=True)
                    assert result[-1]['status'] == 'COMPLETED'
                    assert any(r['operation'] == 'BATCH_TRANSFER' and r['status'] == 'COMPLETED' for r in receipts)
                    posted = next(r for r in receipts if r['operation'] == 'BATCH_TRANSFER')
                    batch_id = posted['data']['batch_id']
                    assert any((r['operation'] == 'QUERY_TRANSFER_BATCHES' and any(
                        x['data']['batch_id'] == batch_id for x in r['data']['receipts'])) or
                        (r['operation'] == 'QUERY_BILLS' and len([x for x in r['data']['transactions']
                            if x.get('batch_id') == batch_id]) == 2) for r in receipts)
                    print('execute/recheck:', [(r['operation'], r['status']) for r in receipts], flush=True)
                out = chat('给张伟40元，另外一位25元，作为一批转账')
                assert out[-1]['status'] == 'NEEDS_CLARIFICATION'
                print('missing recipient: clarification', flush=True)
                thread = out[0]['thread_id']
                out = chat('另外一位是李娜', thread)
                old = card(out, [4000, 2500])
                out = chat('张伟改成30元，李娜保持25元', thread)
                card(out, [3000, 2500])
                out = chat('这批不转了', thread)
                assert out[-1]['status'] == 'REJECTED'
                assert c.post('/agent/chat', headers=auth, json={'thread_id': thread,
                    'resume': {'challenge_id': old['challenge_id'], 'decision': 'approve'}}).status_code == 409
                accounts = c.get('/bank/accounts', headers=auth).json()
                balance = next(r['balance_minor'] for r in accounts['accounts'] if r['account_ref'] == accounts['current_account_ref'])
                assert balance == 490500
                print('PASS: two batches committed; changed/cancelled batch not paid; balance 500000 ->', balance, flush=True)
        return 0
    except Exception as exc:
        print('FAIL:', type(exc).__name__, '(provider response and credentials omitted)', flush=True)
        return 1
    finally:
        model.close()


if __name__ == '__main__':
    raise SystemExit(main())
