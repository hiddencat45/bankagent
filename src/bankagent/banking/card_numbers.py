"""Local-only demo numbers; not real bank card numbers or login credentials."""
import secrets
import re


def new_number(cards):
    existing = {row.get('card_number') for row in cards.values()}
    while True:
        number = '9900' + ''.join(str(secrets.randbelow(10)) for _ in range(12))
        if number not in existing:
            return number


def fill_missing(cards):
    changed = False
    for row in cards.values():
        if 'card_number' not in row:
            row['card_number'] = new_number(cards)
            changed = True
    return changed


def normalize(value):
    if not isinstance(value, str): return None
    value = value.replace(' ', '')
    return value if re.fullmatch(r'[0-9]{16}', value) else None
