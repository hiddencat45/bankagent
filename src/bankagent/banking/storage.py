"""Versioned SQLite snapshots; ledger and idempotency receipts commit together."""
from contextlib import contextmanager
from datetime import date, datetime, timezone, timedelta
import json
from pathlib import Path
import sqlite3


class SQLiteStore:
    def __init__(self, path, initial_data):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        with self.connection() as db:
            tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if not tables:
                if existed:
                    raise ValueError('Existing database is missing its schema')
                db.execute('CREATE TABLE bank_state (id INTEGER PRIMARY KEY CHECK(id=1), '
                           'version INTEGER NOT NULL, data TEXT NOT NULL, receipts TEXT NOT NULL, '
                           'created_at TEXT NOT NULL)')
                data, receipts = self.encode(initial_data, {})
                db.execute('INSERT INTO bank_state VALUES (1, 2, ?, ?, ?)',
                           (data, receipts, datetime.now(timezone.utc).isoformat()))
            saved, _ = self.load(db)  # Unknown/corrupted stores fail closed, never silently reseed.
            self.created_at = datetime.fromisoformat(db.execute(
                'SELECT created_at FROM bank_state WHERE id=1').fetchone()[0])
            if self.created_at.utcoffset() is None:
                raise ValueError('Invalid database clock')
            self.reference = saved.get('reference_date')

    def business_now(self):
        origin = datetime.combine(self.reference, datetime.min.time(),
                                  tzinfo=timezone(timedelta(hours=8))).replace(hour=12)
        return origin + (datetime.now(timezone.utc) - self.created_at)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        try:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def encode(data, completed):
        data = dict(data)
        if 'reference_date' in data:
            data['reference_date'] = data['reference_date'].isoformat()
        receipts = [[list(key), list(fingerprint), result]
                    for key, (fingerprint, result) in completed.items()]
        return (json.dumps(data, ensure_ascii=False, allow_nan=False),
                json.dumps(receipts, ensure_ascii=False, allow_nan=False))

    @staticmethod
    def load(db):
        rows = db.execute('SELECT version, data, receipts FROM bank_state WHERE id=1').fetchall()
        if len(rows) != 1 or rows[0][0] not in {1, 2, 3}:
            raise ValueError('Unsupported bank database version or missing state')
        data = json.loads(rows[0][1])
        if not isinstance(data, dict) or not isinstance(data.get('accounts'), dict) \
                or not isinstance(data.get('transactions'), list):
            raise ValueError('Invalid bank database state')
        if 'reference_date' in data:
            data['reference_date'] = date.fromisoformat(data['reference_date'])
        completed = {}
        for key, fingerprint, result in json.loads(rows[0][2]):
            key = tuple(key)
            if len(key) != 3 or key in completed or not isinstance(result, dict):
                raise ValueError('Invalid stored receipt')
            completed[key] = (tuple(fingerprint), result)
        if rows[0][0] == 1:
            # Only map the two known seed contacts. Never infer destinations for
            # custom contacts or retroactively credit historical outgoing transfers.
            for cid, name, target, owner in (
                    ('contact-001', '张伟', 'account-002', 'user-002'),
                    ('contact-002', '李娜', 'account-003', 'user-003')):
                contact = data.get('contacts', {}).get(cid)
                if contact == {'user_id': 'user-001', 'display_name': name}:
                    if target == 'account-003' and target not in data['accounts']:
                        data['accounts'][target] = {'user_id': owner, 'balance_minor': 0, 'currency': 'CNY'}
                    if data['accounts'].get(target, {}).get('user_id') == owner:
                        contact['recipient_account_id'] = target
            encoded, receipts = SQLiteStore.encode(data, completed)
            db.execute('UPDATE bank_state SET version=2, data=?, receipts=? WHERE id=1', (encoded, receipts))
        if rows[0][0] < 3:
            # Keep the first card and original money; never rewrite past ledger entries.
            seen, moves = set(), []
            for cid, card in data.get('cards', {}).items():
                old = card['account_id']
                if old not in seen:
                    seen.add(old)
                    continue
                new = 'account-card-' + cid
                if new in data['accounts']:
                    raise ValueError('Card account migration collision')
                data['accounts'][new] = {'user_id': data['accounts'][old]['user_id'],
                    'display_name': card['display_name'] + '独立账户', 'balance_minor': 0, 'currency': 'CNY'}
                card['account_id'] = new
                moves.append({'card_id': cid, 'card_name': card['display_name'],
                              'previous_account_id': old, 'account_id': new, 'opening_balance_minor': 0})
            if moves:
                data['card_account_migration'] = moves
            encoded, receipts = SQLiteStore.encode(data, completed)
            db.execute('UPDATE bank_state SET version=3, data=?, receipts=? WHERE id=1', (encoded, receipts))
        from bankagent.banking.card_numbers import fill_missing
        if fill_missing(data.get('cards', {})):
            encoded, receipts = SQLiteStore.encode(data, completed)
            db.execute('UPDATE bank_state SET data=?, receipts=? WHERE id=1', (encoded, receipts))
        return data, completed

    def save(self, db, data, completed):
        encoded = self.encode(data, completed)
        db.execute('UPDATE bank_state SET data=?, receipts=? WHERE id=1', encoded)
