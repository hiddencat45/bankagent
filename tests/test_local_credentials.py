import secrets
import sqlite3
import pytest
from bankagent.api.credentials import CredentialStore
from bankagent.api.contracts import ApiError


def test_registration_is_new_identity_and_does_not_create_bank_accounts(tmp_path):
    path = tmp_path / 'ledger.sqlite3'
    store = CredentialStore(path)
    password = secrets.token_urlsafe(24)
    identity = store.register(' Test_User ', '张伟', password)
    assert identity['user_id'].startswith('registered-')
    assert store.login('TEST_USER', password) == identity
    with pytest.raises(ApiError):
        store.register('test_user', '不同显示名', password)
    with sqlite3.connect(path) as db:
        assert [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")] == ['local_credentials']
    assert password.encode() not in path.read_bytes()


def test_locks_persist_and_payment_setup_cannot_overwrite(tmp_path):
    path = tmp_path / 'ledger.sqlite3'
    now = [1000.0]
    store = CredentialStore(path, lambda: now[0])
    password = secrets.token_urlsafe(24)
    user = store.register('alice', '甲', password)['user_id']
    pin = f'{secrets.randbelow(1000000):06d}'
    store.set_payment_password(user, password, pin)
    with pytest.raises(ApiError):
        store.set_payment_password(user, password, pin)
    wrong = '000000' if pin != '000000' else '111111'
    for _ in range(5):
        with pytest.raises(ApiError):
            store.verify_payment(user, wrong)
    store = CredentialStore(path, lambda: now[0])
    with pytest.raises(ApiError):
        store.verify_payment(user, pin)
    now[0] += 901
    store.verify_payment(user, pin)
    assert store.login('alice', password)['user_id'] == user
