"""只验证工作台静态入口与真实 API 共存；不替代浏览器点击或视觉验收。"""
import json

from fastapi.testclient import TestClient

from frontend.dev_app import create_app


def test_static_workbench_does_not_expose_repository_or_shadow_api(monkeypatch):
    from scenarios import bills
    monkeypatch.setattr(bills, '_clock', bills._clock)
    with TestClient(create_app(), base_url='http://localhost') as client:
        page = client.get('/')
        assert page.status_code == 200
        assert 'text/html' in page.headers['content-type']
        assert 'src="app.mjs"' in page.text
        assert client.get('/app.mjs').status_code == 200
        assert client.get('/agent-client.mjs').status_code == 200
        assert client.get('/workbench.css').status_code == 200
        assert client.get('/AGENTS.md').status_code == 404
        assert client.get('/.env').status_code == 404
        assert client.get('/health').json()['backend'] == 'ok'


def test_workbench_session_and_query_use_actual_backend(monkeypatch):
    from scenarios import bills
    monkeypatch.setattr(bills, '_clock', bills._clock)
    with TestClient(create_app(), base_url='http://localhost') as client:
        session = client.post('/demo/session').json()
        response = client.post('/agent/chat',
            headers={'Authorization': 'Bearer ' + session['token']},
            json={'message': '查询余额'})
        assert response.status_code == 200
        frames = [json.loads(frame.split('\ndata: ', 1)[1])
                  for frame in response.text.strip().split('\n\n')]
        result = next(frame['payload'] for frame in frames
                      if frame.get('type') == 'result')
        assert result['status'] == 'COMPLETED'
        assert result['data'] == {'balance_minor': 500000, 'currency': 'CNY'}
        assert 'daily_transfer_total_minor' not in response.text
