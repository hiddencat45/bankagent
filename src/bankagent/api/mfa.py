"""Customer TOTP enrollment and one-use authorization; never part of model state."""
import ctypes
from ctypes import wintypes
import hmac
import os
import re
import secrets

import pyotp

from bankagent.api.contracts import ApiError


def protect(value, *, decrypt=False):
    """Windows current-user DPAPI, without a plaintext or machine-wide fallback."""
    if os.name != 'nt':
        raise ApiError('MFA_UNAVAILABLE', '此版本的验证器密钥保护需要Windows。', 409)
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buffer = ctypes.create_string_buffer(value)
    source = Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise ApiError('MFA_UNAVAILABLE', '验证器密钥无法读取或保护，请使用原Windows用户及电脑；不会降级认证。', 409)
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        kernel.LocalFree(output.data)


class MfaStore:
    def __init__(self, credentials):
        self.credentials = credentials
        with credentials.transaction() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS local_mfa (
                user_id TEXT PRIMARY KEY, secret BLOB, pending_secret BLOB,
                enrollment_id TEXT, pending_until REAL NOT NULL DEFAULT 0,
                last_step INTEGER NOT NULL DEFAULT -1, failures INTEGER NOT NULL DEFAULT 0,
                locked_until REAL NOT NULL DEFAULT 0)''')
            db.execute('''CREATE TABLE IF NOT EXISTS local_mfa_grants (
                challenge_id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                operation_hash TEXT NOT NULL, expires_at REAL NOT NULL)''')

    def configured(self, user):
        with self.credentials.transaction() as db:
            row = db.execute('SELECT secret FROM local_mfa WHERE user_id=?', (user,)).fetchone()
            return bool(row and row['secret'] is not None)

    def begin(self, user, login_password):
        uri = None
        with self.credentials.transaction() as db:
            account = db.execute('SELECT * FROM local_credentials WHERE user_id=?', (user,)).fetchone()
            error = self.credentials._verify(db, account, login_password, 'login')
            if not error:
                db.execute('INSERT OR IGNORE INTO local_mfa (user_id) VALUES (?)', (user,))
                row = db.execute('SELECT * FROM local_mfa WHERE user_id=?', (user,)).fetchone()
                if row['secret'] is not None:
                    raise ApiError('MFA_ALREADY_CONFIGURED', '已绑定验证器，不能通过首次绑定入口覆盖。', 409)
                if row['locked_until'] > self.credentials.clock():
                    self.reject('MFA_LOCKED')
                secret = pyotp.random_base32()
                enrollment = secrets.token_urlsafe(24)
                db.execute('UPDATE local_mfa SET pending_secret=?,enrollment_id=?,pending_until=? WHERE user_id=?',
                           (protect(secret.encode('ascii')), enrollment, self.credentials.clock()+300, user))
                uri = pyotp.TOTP(secret).provisioning_uri(account['username'], issuer_name='有度')
        self.credentials.reject(error)
        return {'enrollment_id': enrollment, 'uri': uri, 'expires_in': 300}

    @staticmethod
    def reject(error):
        if error:
            messages = {
                'MFA_REQUIRED': '本次为高风险转账，请先绑定手机验证器，再重新核对原交易。',
                'MFA_INVALID': '动态码错误或已过期，请检查手机时间并重试。',
                'MFA_REPLAY': '该时段动态码已经使用，请等待手机显示下一组动态码。',
                'MFA_LOCKED': '动态码连续错误5次，已锁定15分钟；重开应用不会解除。',
                'MFA_ENROLLMENT_EXPIRED': '绑定已失效，请重新验证登录密码并扫描新二维码。',
            }
            raise ApiError(error, messages[error], 409)

    def _check(self, db, row, code, *, enrollment=False):
        now = self.credentials.clock()
        if row['locked_until'] > now:
            return 'MFA_LOCKED', None
        blob = row['pending_secret'] if enrollment else row['secret']
        secret = protect(blob, decrypt=True).decode('ascii')
        step = int(now // 30)
        matched = None
        if isinstance(code, str) and re.fullmatch(r'[0-9]{6}', code):
            totp = pyotp.TOTP(secret)
            matched = next((s for s in (step, step-1, step+1)
                            if hmac.compare_digest(totp.at(s*30), code)), None)
        error = 'MFA_INVALID' if matched is None else ('MFA_REPLAY' if matched <= row['last_step'] else None)
        failures = 0 if not error else (0 if row['locked_until'] else row['failures']) + 1
        locked = now+900 if failures >= 5 else 0
        db.execute('UPDATE local_mfa SET failures=?,locked_until=? WHERE user_id=?', (failures, locked, row['user_id']))
        return ('MFA_LOCKED' if locked else error), matched

    def finish(self, user, enrollment, code):
        with self.credentials.transaction() as db:
            row = db.execute('SELECT * FROM local_mfa WHERE user_id=?', (user,)).fetchone()
            if (not row or row['secret'] is not None or not row['pending_secret']
                    or row['enrollment_id'] != enrollment or row['pending_until'] <= self.credentials.clock()):
                self.reject('MFA_ENROLLMENT_EXPIRED')
            error, step = self._check(db, row, code, enrollment=True)
            if not error:
                db.execute('''UPDATE local_mfa SET secret=pending_secret,pending_secret=NULL,
                    enrollment_id=NULL,pending_until=0,last_step=? WHERE user_id=?''', (step, user))
        self.reject(error)

    def verify(self, user, code, challenge, operation_hash, ttl):
        if ttl <= 0:
            raise ApiError('CHALLENGE_INVALID', '确认已过期，请重新核对交易。', 409)
        with self.credentials.transaction() as db:
            now = self.credentials.clock()
            db.execute('DELETE FROM local_mfa_grants WHERE expires_at<=?', (now,))
            grant = db.execute('SELECT * FROM local_mfa_grants WHERE challenge_id=?', (challenge,)).fetchone()
            if grant and grant['user_id'] == user and grant['operation_hash'] == operation_hash:
                return  # Retry of this same authorized operation, never a different payment.
            row = db.execute('SELECT * FROM local_mfa WHERE user_id=?', (user,)).fetchone()
            if not row or row['secret'] is None:
                self.reject('MFA_REQUIRED')
            error, step = self._check(db, row, code)
            if not error:
                db.execute('UPDATE local_mfa SET last_step=? WHERE user_id=?', (step, user))
                db.execute('INSERT INTO local_mfa_grants VALUES (?,?,?,?)',
                           (challenge, user, operation_hash, now+min(ttl, 300)))
        self.reject(error)
