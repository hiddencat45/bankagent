"""Reproduce the documented form journey over real HTTP, with a fresh ledger."""
import argparse
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from desktop.app import LocalService
from desktop.client import QueryClient, business_confirmation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise SystemExit('Choose a new output file.')
    record = {'mode': 'real child-process HTTP / deterministic forms / no window or live model', 'steps': []}
    with TemporaryDirectory(prefix='delivery-replay-') as tmp:
        env = {k: v for k, v in os.environ.items() if not k.startswith('BANKAGENT_MODEL_') and k != 'BANKAGENT_DB_PATH'}
        env['BANKAGENT_DB_PATH'] = str(Path(tmp) / 'demo.sqlite3')
        def connect():
            server = LocalService(env=env)
            client = QueryClient(server.start())
            client.connect()
            return server, client
        server, client = connect()
        def write(action, fields):
            pending = business_confirmation(client.form(action, fields))
            assert pending and pending['risk_level'] == 'YELLOW'
            events = client.resume(pending, 'approve')
            result = next(d['payload'] for e, d in events if e == 'card' and d.get('type') == 'result' and d['payload']['operation'] == action)
            record['steps'].append({'action': action, 'fields': fields, 'result': result})
            return result
        def switch(ref):
            with client.post('/demo/customer-session', {'customer_ref': ref}) as response:
                client.token = json.load(response)['token']
        def balance():
            data = client.accounts()
            return next(r['balance_minor'] for r in data['accounts'] if r['account_ref'] == data['current_account_ref'])
        try:
            account = write('OPEN_ACCOUNT', {'display_name': '旅程账户'})['data']['account_id']
            client.switch_account(account)
            write('ISSUE_DEBIT_CARD', {'display_name': '旅程卡'})
            fields = {'card_name': '旅程卡', 'merchant': '演示书店', 'amount': '12', 'category': '购物'}
            assert write('PAY_BY_CARD', fields)['error_code'] == 'CARD_NOT_ACTIVE'
            assert balance() == 100000
            write('ACTIVATE_DEBIT_CARD', {'card_name': '旅程卡'})
            assert write('PAY_BY_CARD', fields)['status'] == 'COMPLETED'
            assert balance() == 98800
            write('TRANSFER', {'recipient_name': '张伟', 'amount': '37.50'})
            assert balance() == 95050
            record['sender_bills'] = client.bills()
            switch('zhang-wei')
            assert balance() == 43750
            record['receiver_bills'] = client.bills()
            switch('primary')
            client.switch_account(account)
            assert balance() == 95050
        finally:
            server.close()
        server, client = connect()
        try:
            client.switch_account(account)
            assert balance() == 95050 and client.bills() == record['sender_bills']
            switch('zhang-wei')
            assert balance() == 43750 and client.bills() == record['receiver_bills']
            record['restart_balances_minor'] = [95050, 43750]
            record['result'] = 'PASS'
        finally:
            server.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS: 100000 -> 98800 -> 95050; receiver 40000 -> 43750; both unchanged after child process restart.')


if __name__ == '__main__':
    main()
