"""Explicit real-provider acceptance: read-only, isolated demo data, no credentials printed."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from fastapi.testclient import TestClient
from bankagent.agent.model_providers import build_model_from_env, ProviderConfigError
from bankagent.api.server import create_app
import json


def main():
    try:
        model = build_model_from_env()
    except ProviderConfigError:
        print('模型配置不完整，请核对 BANKAGENT_MODEL_* 环境变量。')
        return 2
    if model is None:
        print('未配置 BANKAGENT_MODEL_API_KEY；未进行真实模型验收。')
        return 2
    cases = [
        ('最近钱花在哪里了', 100000, None, None),
        ('只看餐饮', 12000, '餐饮', None),
        ('列出超过一百的', 12000, '餐饮', 10000),
    ]
    try:
        with TestClient(create_app(demo=True, candidate_model=model, query_model=model),
                        base_url='http://localhost') as client:
            token = client.post('/demo/session').json()['token']
            auth = {'Authorization': 'Bearer ' + token}
            thread = None
            for text, total, category, threshold in cases:
                started = time.monotonic()
                payload = {'message': text}
                if thread:
                    payload['thread_id'] = thread
                response = client.post('/agent/chat', headers=auth, json=payload)
                response.raise_for_status()
                frames = [json.loads(frame.split('\n')[1][6:])
                          for frame in response.text.strip().split('\n\n')]
                thread = frames[0]['thread_id']
                assert frames[-1]['status'] == 'COMPLETED'
                receipt = [f['payload'] for f in frames if f.get('type') == 'result'][-1]
                assert receipt['operation'] == 'QUERY_BILLS'
                data = receipt['data']
                assert data['total_minor'] == total
                assert data['filters']['category'] == category
                assert data['filters']['amount_gt_minor'] == threshold
                print(f'{text}: PASS / {total} 分 / {len(data["transactions"])} 笔 / {time.monotonic()-started:.2f}s')
            print('真实模型连续查询验收通过；未执行资金操作。')
        return 0
    except Exception:
        print('真实模型验收未通过；请检查配置、网络或模型工具调用能力。未自动重试资金操作。')
        return 1
    finally:
        model.close()


if __name__ == '__main__':
    raise SystemExit(main())