"""Exercise the real child server without a GUI or live model credentials."""
import json
import os
import socket
import subprocess
from urllib.request import ProxyHandler, Request, build_opener
from urllib.error import HTTPError
from urllib.parse import urlsplit

import pytest

from desktop.app import LocalService
from desktop.client import QueryClient, parse_stream, query_result


def offline_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith('BANKAGENT_MODEL_')}
    env.pop('BANKAGENT_DB_PATH', None)
    env['BANKAGENT_DEMO_ALLOW_LAN'] = '1'  # desktop must override even this
    return env


def test_real_service_lifecycle():
    service = LocalService(env=offline_env())
    opener = build_opener(ProxyHandler({}))
    try:
        url = service.start()
        process = service.process
        with opener.open(url) as response:
            assert 'app.mjs' in response.read().decode()
        with opener.open(url + '/health') as response:
            assert json.load(response)['model'] == 'not_configured'
        with pytest.raises(HTTPError) as rejected:
            opener.open(Request(url + '/health', headers={'Host': 'outside.example'}))
        assert rejected.value.code == 403
        client = QueryClient(url)
        assert client.connect() == 'offline'
        frames = client.query('查询余额')
        receipt = next(data['payload'] for event, data in frames if event == 'card' and data['type'] == 'result')
        before = receipt['data']['balance_minor']
        assert query_result(receipt).startswith('账户余额：¥ ')
        pending = client.query('给张伟转300元')
        assert pending[-1][1]['status'] == 'AWAITING_CONFIRMATION'
        after = client.query('查询余额')
        balance = next(data['payload']['data']['balance_minor'] for event, data in after
                       if event == 'card' and data['type'] == 'result')
        assert balance == before
        port = urlsplit(url).port
    finally:
        service.close()
    assert process.poll() is not None
    with socket.socket() as sock:
        assert sock.connect_ex(('127.0.0.1', port)) != 0
    service.close()  # shutdown is idempotent


def test_parent_pipe_loss_stops_child():
    service = LocalService(env=offline_env())
    try:
        service.start()
        service.process.stdin.close()
        assert service.process.wait(timeout=5) == 0
    finally:
        service.close()


def test_startup_timeout_cleans_up():
    service = LocalService(env=offline_env(), timeout=0)
    with pytest.raises(RuntimeError, match='超时'):
        service.start()
    assert service.process is None
    assert service.temp is None


def test_stream_rejects_missing_done_and_mixed_identity():
    data = {'thread_id': 't1', 'request_id': 'r1', 'mode': 'offline', 'status': 'PROCESSING'}
    first = 'event: status\ndata: ' + json.dumps(data) + '\n\n'
    with pytest.raises(ValueError, match='incomplete'):
        parse_stream(first.encode())
    data.update(thread_id='t2', status='COMPLETED')
    end = 'event: done\ndata: ' + json.dumps(data) + '\n\n'
    with pytest.raises(ValueError, match='mismatch'):
        parse_stream((first + end).encode())


@pytest.mark.parametrize('invalid', [[], {'token': '', 'mode': 'offline'},
                                    {'token': 'test-token', 'mode': 'unknown'}])
def test_invalid_session_does_not_replace_token(monkeypatch, invalid):
    from io import BytesIO
    client = QueryClient('http://127.0.0.1')
    client.token = 'previous-token'
    monkeypatch.setattr(client, 'post', lambda *args: BytesIO(json.dumps(invalid).encode()))
    with pytest.raises(ValueError, match='invalid session'):
        client.connect()
    assert client.token == 'previous-token'


def test_stream_rejects_unterminated_final_frame():
    data = {'thread_id': 't', 'request_id': 'r', 'mode': 'offline', 'status': 'COMPLETED'}
    raw = ('event: status\ndata: ' + json.dumps(data) + '\n\n'
           + 'event: done\ndata: ' + json.dumps(data)).encode()
    with pytest.raises(ValueError, match='incomplete'):
        parse_stream(raw)


def test_launch_failure_cleans_up(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError('cannot spawn')
    monkeypatch.setattr(subprocess, 'Popen', fail)
    service = LocalService(env=offline_env())
    with pytest.raises(OSError):
        service.start()
    assert service.temp is None


def test_bad_model_configuration_cleans_up():
    env = offline_env()
    env['BANKAGENT_MODEL_API_KEY'] = 'test-only-placeholder'
    env['BANKAGENT_MODEL_TIMEOUT'] = 'not-a-number'
    service = LocalService(env=env)
    with pytest.raises(RuntimeError, match='启动失败'):
        service.start()
    assert service.process is None
    assert service.temp is None


def test_persistent_service_restart_keeps_confirmed_transfer(tmp_path):
    env = offline_env()
    env['BANKAGENT_DB_PATH'] = str(tmp_path / 'bank.sqlite3')
    first = LocalService(env=env)
    try:
        client = QueryClient(first.start())
        client.connect()
        pending = client.query('给张伟转40元')
        interrupt = next(data for event, data in pending if event == 'interrupt')
        with client.post('/agent/chat', {'thread_id': interrupt['thread_id'],
                'resume': {'challenge_id': interrupt['challenge_id'], 'decision': 'approve'}}) as response:
            frames = parse_stream(response.read())
        assert frames[-1][1]['status'] == 'COMPLETED'
        with pytest.raises(HTTPError) as denied:
            client.post('/demo/reset', {})
        assert denied.value.code == 409
    finally:
        first.close()
    reopened = LocalService(env=env)
    try:
        client = QueryClient(reopened.start())
        client.connect()
        frames = client.query('查询余额')
        receipt = next(data['payload'] for event, data in frames if event == 'card' and data['type'] == 'result')
        assert receipt['data']['balance_minor'] == 496000
    finally:
        reopened.close()
