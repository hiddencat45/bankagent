"""Explicit live-model task acceptance, disposable ledger only. Never prints secrets."""
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / 'src')]
from desktop.app import desktop_environment
from bankagent.agent.model_providers import build_model_from_env
from bankagent.api.server import create_app
from bankagent.banking import bank_backend
from bankagent.banking.bank_types import TrustedContext
from fastapi.testclient import TestClient


def frames(response):
    response.raise_for_status()
    return [json.loads(f.split('\n')[1][6:]) for f in response.text.strip().split('\n\n')]


def main():
    for k, v in desktop_environment().items():
        if k.startswith('BANKAGENT_MODEL_'):
            os.environ[k] = v
    model = build_model_from_env()
    if model is None:
        print('SKIP: model not configured')
        return 2
    try:
        with TemporaryDirectory() as tmp:
            with TestClient(create_app(demo=True, query_model=model, database_path=Path(tmp)/'live.sqlite3'), base_url='http://localhost') as c:
                auth = {'Authorization': 'Bearer ' + c.post('/demo/session').json()['token']}
                cases = [('先查一下余额，够的话给张伟转40元，转完让我看看记录。', '张伟', 4000),
                         ('确认我的余额能够支付后，向李娜汇出二十五块五毛，办完核对一下流水。', '李娜', 2550)]
                for text, person, amount in cases:
                    out = frames(c.post('/agent/chat', headers=auth, json={'message': text}))
                    print('prepare:', person, out[-1]['status'], flush=True)
                    card = next((f['payload'] for f in out if f.get('type') == 'confirm'), None)
                    if card is None:
                        print('messages:', [f.get('text', f.get('message')) for f in out if 'text' in f or 'message' in f], flush=True)
                    assert card and card['operation'] == 'TRANSFER' and card['recipient'] == person and card['amount_minor'] == amount
                    assert any(f.get('type') == 'result' and f['payload']['operation'] == 'GET_BALANCE' for f in out)
                    done = frames(c.post('/agent/chat', headers=auth, json={'thread_id': out[0]['thread_id'],
                        'resume': {'challenge_id': card['challenge_id'], 'decision': 'approve'}}))
                    results = [f['payload'] for f in done if f.get('type') == 'result']
                    print('execute/recheck:', done[-1]['status'], [(r['operation'], r['status']) for r in results], flush=True)
                    assert done[-1]['status'] == 'COMPLETED'
                    assert any(r['operation'] == 'TRANSFER' and r['status'] == 'COMPLETED' for r in results)
                    assert results[-1]['operation'] == 'QUERY_BILLS'
                out = frames(c.post('/agent/chat', headers=auth, json={'message': '给张伟转40元，之后查记录'}))
                thread = out[0]['thread_id']
                original = next(f['payload'] for f in out if f.get('type') == 'confirm')
                for text, expected in [('改成三十元', 'AWAITING_CONFIRMATION'), ('先看看余额，暂时别转', 'COMPLETED'), ('不转了', 'REJECTED')]:
                    out = frames(c.post('/agent/chat', headers=auth, json={'thread_id': thread, 'message': text}))
                    print('pending update:', text, out[-1]['status'], flush=True)
                    assert out[-1]['status'] == expected
                    if expected == 'AWAITING_CONFIRMATION':
                        revised = next(f['payload'] for f in out if f.get('type') == 'confirm')
                        assert revised['amount_minor'] == 3000
                stale = c.post('/agent/chat', headers=auth, json={'thread_id': thread,
                    'resume': {'challenge_id': original['challenge_id'], 'decision': 'approve'}})
                assert stale.status_code == 409
                actual = bank_backend.get_balance(context=TrustedContext('user-001', 'account-001', 'check'))['data']['balance_minor']
                assert actual == 493450
                print('PASS: balance 500000 ->', actual, flush=True)
        return 0
    except Exception as exc:
        print('FAIL:', type(exc).__name__, '(credentials and provider response omitted)', flush=True)
        return 1
    finally:
        model.close()


if __name__ == '__main__':
    raise SystemExit(main())
