"""Read conversational responses; deliberately offers no resume/approval API."""
import json
from urllib.request import Request, ProxyHandler, build_opener


class QueryClient:
    def __init__(self, url):
        self.url = url
        self.token = None
        self.opener = build_opener(ProxyHandler({}))

    def post(self, path, payload):
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        return self.opener.open(Request(self.url + path,
            data=json.dumps(payload).encode(), headers=headers), timeout=90)

    def connect(self):
        with self.post('/demo/session', {}) as response:
            session = json.load(response)
        if (not isinstance(session, dict) or not isinstance(session.get('token'), str)
                or not session['token'].strip() or session.get('mode') not in {'model', 'offline'}):
            raise ValueError('invalid session')
        self.token = session['token']
        return session['mode']

    def query(self, message, thread=None):
        with self.post('/agent/chat', {'message': message, 'thread_id': thread}) as response:
            if response.headers.get_content_type() != 'text/event-stream':
                raise ValueError('invalid response')
            raw = response.read(2 * 1024 * 1024 + 1)
        return parse_stream(raw, thread)


def parse_stream(raw, thread=None):
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('response too large')
    text = raw.decode('utf-8').replace('\r\n', '\n')
    if not text.endswith('\n\n'):
        raise ValueError('incomplete stream')
    frames = []
    for frame in text.split('\n\n'):
        if not frame.strip():
            continue
        fields = frame.splitlines()
        event = next((line[7:] for line in fields if line.startswith('event: ')), None)
        data = json.loads('\n'.join(line[6:] for line in fields if line.startswith('data: ')))
        if not isinstance(data, dict):
            raise ValueError('invalid envelope')
        if event not in {'status', 'message', 'card', 'interrupt', 'error', 'done'}:
            raise ValueError('unknown event')
        identity = tuple(data.get(k) for k in ('thread_id', 'request_id', 'mode'))
        if not all(isinstance(v, str) and v for v in identity) or identity[2] not in {'model', 'offline'}:
            raise ValueError('invalid envelope')
        if (thread and identity[0] != thread) or (frames and identity != frames[0][2]):
            raise ValueError('envelope mismatch')
        if frames and frames[-1][0] == 'done':
            raise ValueError('data after done')
        if event in {'message', 'error'}:
            value = data.get('text' if event == 'message' else 'message')
            if not isinstance(value, str) or not value.strip():
                raise ValueError('invalid message')
        if event == 'card' and (data.get('type') not in {'confirm', 'evidence', 'result'}
                                or not isinstance(data.get('payload'), dict)):
            raise ValueError('invalid card')
        frames.append((event, data, identity))
    if not frames or frames[0][0] != 'status' or frames[-1][0] != 'done':
        raise ValueError('incomplete stream')
    if frames[-1][1]['status'] not in {'COMPLETED', 'FAILED', 'REJECTED', 'PENDING',
            'NEEDS_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_AUTHENTICATION'}:
        raise ValueError('invalid final status')
    return [(event, data) for event, data, _ in frames]


def money(minor):
    if type(minor) is not int or minor < 0:
        raise ValueError('invalid amount')
    return f'{minor // 100:,}.{minor % 100:02d}'


def query_result(payload):
    if payload.get('status') != 'COMPLETED':
        return ''
    data = payload['data']
    if payload['operation'] == 'GET_BALANCE':
        if data['currency'] != 'CNY':
            raise ValueError('invalid currency')
        return '账户余额：¥ ' + money(data['balance_minor'])
    if payload['operation'] == 'QUERY_BILLS':
        if data['currency'] != 'CNY':
            raise ValueError('invalid currency')
        lines = [f"消费合计：¥ {money(data['total_minor'])}",
                 f"查询期间：{data['start']} 至 {data['end']}（不含结束日）"]
        lines += [f"{row['occurred_at']}  {row.get('merchant') or row['category']}  ¥ {money(row['amount_minor'])}"
                  for row in data['transactions']]
        return '\n'.join(lines)
    return ''
