"""启动隔离的真实 HTTP 服务，验证转账闭环后自动停止；不输出会话令牌。"""
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx


def main():
    root = Path(__file__).resolve().parents[1]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen([
        sys.executable, '-m', 'uvicorn', 'api.server:create_demo_app', '--factory',
        '--app-dir', 'preparaion', '--host', '127.0.0.1', '--port', str(port),
        '--no-access-log', '--log-level', 'error',
    ], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=10, trust_env=False) as client:
            deadline = time.monotonic() + 20
            while True:
                try:
                    assert client.get('/health').json()['status'] == 'ok'
                    break
                except httpx.ConnectError:
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError('HTTP server did not start') from None
                    time.sleep(0.1)
            session = client.post('/demo/session').json()
            auth = {'Authorization': 'Bearer ' + session['token']}
            def chat(payload):
                response = client.post('/agent/chat', headers=auth, json=payload)
                assert response.status_code == 200
                return [(frame.split('\n')[0][7:], json.loads(frame.split('\n')[1][6:]))
                        for frame in response.text.strip().split('\n\n')]
            def result(out):
                return next(d['payload'] for n, d in out if n == 'card' and d['type'] == 'result')
            assert result(chat({'message': '本月账单'}))['data']['total_minor'] == 100000
            out = chat({'message': '给张伟转 300 元'})
            intr = next(d for n, d in out if n == 'interrupt')
            assert out[-1][1]['status'] == 'AWAITING_CONFIRMATION'
            payload = {'thread_id': intr['thread_id'], 'resume': {
                'challenge_id': intr['challenge_id'], 'decision': 'approve'}}
            first = result(chat(payload))
            assert first['data']['remaining_balance_minor'] == 470000
            assert result(chat(payload)) == first
            assert result(chat({'message': '余额'}))['data']['balance_minor'] == 470000
            assert client.post('/demo/reset', headers=auth).json()['status'] == 'COMPLETED'
            assert client.post('/agent/chat', headers=auth, json=payload).status_code == 401
        print('HTTP smoke passed: bills, confirmation, transfer, replay, balance, reset')
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == '__main__':
    main()
