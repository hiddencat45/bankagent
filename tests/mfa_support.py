"""Test-only authenticator; generated secrets and deterministic wall clock."""
import time
import pyotp


def bind(c, auth, password):
    clock = [int(time.time() // 30) * 30]
    c.app.state.service.credentials.clock = lambda: clock[0]
    response = c.post('/auth/mfa/enroll', headers=auth, json={'login_password': password})
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    payload = response.json()
    authenticator = pyotp.parse_uri(payload['uri'])
    response = c.post('/auth/mfa/confirm', headers=auth,
                      json={'enrollment_id':payload['enrollment_id'], 'code':authenticator.at(clock[0])})
    assert response.status_code == 200
    def next_code():
        clock[0] += 30
        return authenticator.at(clock[0])
    return authenticator, clock, next_code


def authorize(c, auth, pending, pin, code=None):
    signal = next(d for e,d in pending if e == 'interrupt')
    payload = {'challenge_id':signal['challenge_id'], 'decision':'approve', 'otp':pin}
    if code is not None:
        payload['totp'] = code
    return c.post('/agent/chat', headers=auth,
                  json={'thread_id':pending[0][1]['thread_id'], 'resume':payload})
