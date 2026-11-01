"""Local credentials, independent of account balances and model state.

This store never claims existing customers: registration always generates a new
customer identity. Counters commit even when authentication fails.
"""
import hashlib
import json
import hmac
import re
import secrets
import sqlite3
import time
import unicodedata
from contextlib import contextmanager

from bankagent.api.contracts import ApiError


def username_key(value):
    if not isinstance(value, str):
        raise ApiError('INVALID_USERNAME', '用户名须为4至32位字母、数字或下划线。', 400)
    value = unicodedata.normalize('NFKC', value).strip().casefold()
    if not re.fullmatch(r'[a-z0-9_]{4,32}', value):
        raise ApiError('INVALID_USERNAME', '用户名须为4至32位字母、数字或下划线。', 400)
    return value


def password_hash(value, salt):
    return hashlib.scrypt(value.encode('utf-8'), salt=salt, n=16384, r=8, p=1, dklen=32)


class CredentialStore:
    def __init__(self, path, clock=time.time):
        self.path, self.clock = str(path), clock
        with self.transaction() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS local_credentials (
                username TEXT PRIMARY KEY, user_id TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL, login_salt BLOB NOT NULL,
                login_hash BLOB NOT NULL, payment_salt BLOB, payment_hash BLOB,
                login_failures INTEGER NOT NULL DEFAULT 0,
                login_locked_until REAL NOT NULL DEFAULT 0,
                payment_failures INTEGER NOT NULL DEFAULT 0,
                payment_locked_until REAL NOT NULL DEFAULT 0)''')

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def register(self, username, display_name, password):
        username = username_key(username)
        if not isinstance(display_name, str) or not 1 <= len(display_name.strip()) <= 40:
            raise ApiError('INVALID_NAME', '显示姓名须为1至40个字符。', 400)
        if not isinstance(password, str) or not 10 <= len(password) <= 128:
            raise ApiError('INVALID_PASSWORD', '登录密码须为10至128个字符。', 400)
        salt = secrets.token_bytes(16)
        digest = password_hash(password, salt)
        user = 'registered-' + secrets.token_hex(16)
        with self.transaction() as db:
            if db.execute('SELECT 1 FROM local_credentials WHERE username=?', (username,)).fetchone():
                raise ApiError('USERNAME_EXISTS', '该用户名已注册，请更换。', 409)
            db.execute('INSERT INTO local_credentials (username,user_id,display_name,login_salt,login_hash) VALUES (?,?,?,?,?)',
                       (username, user, display_name.strip(), salt, digest))
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='bank_state'").fetchone():
                data = json.loads(db.execute('SELECT data FROM bank_state WHERE id=1').fetchone()[0])
                data.setdefault('customers', {})[user] = {'display_name': display_name.strip(), 'identity_type': 'LOCAL'}
                db.execute('UPDATE bank_state SET data=? WHERE id=1', (json.dumps(data, ensure_ascii=False),))
        return {'user_id': user, 'display_name': display_name.strip()}

    def _verify(self, db, row, password, kind):
        if row is None:
            # Unknown identities still perform the same expensive hash operation.
            password_hash(password if isinstance(password, str) and len(password) <= 128 else '', b'unknown-identity!')
            return 'INVALID_CREDENTIALS'
        if row[kind + '_locked_until'] > self.clock():
            return 'CREDENTIALS_LOCKED'
        if row[kind + '_hash'] is None:
            return 'PAYMENT_PASSWORD_REQUIRED'
        valid = isinstance(password, str) and len(password) <= 128 and hmac.compare_digest(
            password_hash(password, row[kind + '_salt']), row[kind + '_hash'])
        count = 0 if valid else (0 if row[kind + '_locked_until'] else row[kind + '_failures']) + 1
        locked = self.clock() + 900 if count >= 5 else 0
        # kind is an internal constant, never a client supplied column name.
        db.execute(f'UPDATE local_credentials SET {kind}_failures=?, {kind}_locked_until=? WHERE user_id=?',
                   (count, locked, row['user_id']))
        return None if valid else ('CREDENTIALS_LOCKED' if locked else 'INVALID_CREDENTIALS')

    @staticmethod
    def reject(error):
        if error:
            messages = {'INVALID_CREDENTIALS': '用户名或密码错误。',
                        'CREDENTIALS_LOCKED': '连续错误次数过多，请15分钟后再试。',
                        'PAYMENT_PASSWORD_REQUIRED': '请先设置交易密码。'}
            raise ApiError(error, messages[error], 401 if error == 'INVALID_CREDENTIALS' else 409)

    def login(self, username, password):
        username = username_key(username)
        with self.transaction() as db:
            row = db.execute('SELECT * FROM local_credentials WHERE username=?', (username,)).fetchone()
            error = self._verify(db, row, password, 'login')
        self.reject(error)
        return {'user_id': row['user_id'], 'display_name': row['display_name']}

    def set_payment_password(self, user_id, login_password, payment_password):
        if not isinstance(payment_password, str) or not re.fullmatch(r'[0-9]{6}', payment_password):
            raise ApiError('INVALID_PAYMENT_PASSWORD', '交易密码须为6位数字。', 400)
        if payment_password == login_password:
            raise ApiError('INVALID_PAYMENT_PASSWORD', '交易密码不能与登录密码相同。', 400)
        with self.transaction() as db:
            row = db.execute('SELECT * FROM local_credentials WHERE user_id=?', (user_id,)).fetchone()
            error = self._verify(db, row, login_password, 'login')
            if not error:
                if row['payment_hash'] is not None:
                    error = 'ALREADY_CONFIGURED'
                else:
                    salt = secrets.token_bytes(16)
                    db.execute('UPDATE local_credentials SET payment_salt=?,payment_hash=? WHERE user_id=?',
                               (salt, password_hash(payment_password, salt), user_id))
        if error == 'ALREADY_CONFIGURED':
            raise ApiError(error, '已设置交易密码，不能通过首次设置入口覆盖。', 409)
        self.reject(error)

    def verify_payment(self, user_id, password):
        with self.transaction() as db:
            row = db.execute('SELECT * FROM local_credentials WHERE user_id=?', (user_id,)).fetchone()
            error = self._verify(db, row, password, 'payment')
        self.reject(error)
