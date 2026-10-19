"""加载前检查固定演示数据；不替代运行时授权、归属和事务检查。"""

from datetime import date, datetime, timedelta


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def _minor(value: object) -> bool:
    return type(value) is int and value >= 0


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_demo_data(data: dict) -> None:
    """校验内部数据形状、归属、外键、时间、整数分和余额账本一致性。

    账户均从零余额开始，INCOME 记入、EXPENSE/TRANSFER_OUT 记出。
    失败抛 ValueError，错误消息不回显整笔业务数据。
    """
    _require(isinstance(data, dict), "dataset must be a mapping")
    _require(set(data) == {"reference_date", "accounts", "contacts", "transactions"},
             "unexpected dataset fields")
    reference = data["reference_date"]
    _require(type(reference) is date, "reference_date must be a date")
    accounts, contacts, transactions = (
        data["accounts"], data["contacts"], data["transactions"])
    _require(isinstance(accounts, dict) and bool(accounts), "accounts required")
    _require(isinstance(contacts, dict), "contacts must be a mapping")
    _require(isinstance(transactions, list), "transactions must be a list")
    owners = set()
    for account_id, account in accounts.items():
        _require(_text(account_id) and isinstance(account, dict), "invalid account")
        _require(set(account) == {"user_id", "balance_minor", "currency"},
                 "unexpected account fields")
        _require(_text(account["user_id"]), "account owner required")
        _require(_minor(account["balance_minor"]), "invalid balance_minor")
        _require(account["currency"] == "CNY", "unsupported currency")
        owners.add(account["user_id"])
    for contact_id, contact in contacts.items():
        _require(_text(contact_id) and isinstance(contact, dict), "invalid contact")
        _require(set(contact) == {"user_id", "display_name"},
                 "unexpected contact fields")
        _require(contact["user_id"] in owners, "unknown contact owner")
        _require(_text(contact["display_name"]), "contact display name required")

    fields = {"transaction_id", "account_id", "occurred_at", "kind",
              "amount_minor", "category", "merchant"}
    seen = set()
    balances = dict.fromkeys(accounts, 0)
    ordered = []
    for transaction in transactions:
        _require(isinstance(transaction, dict) and set(transaction) == fields,
                 "unexpected transaction fields")
        tx_id = transaction["transaction_id"]
        _require(_text(tx_id) and tx_id not in seen, "duplicate or invalid transaction id")
        seen.add(tx_id)
        account_id = transaction["account_id"]
        _require(account_id in accounts, "unknown transaction account")
        kind, amount = transaction["kind"], transaction["amount_minor"]
        _require(kind in {"INCOME", "EXPENSE", "TRANSFER_OUT"}, "invalid transaction kind")
        _require(_minor(amount), "invalid amount_minor")
        _require(_text(transaction["category"]), "transaction category required")
        _require(transaction["merchant"] is None or _text(transaction["merchant"]),
                 "invalid merchant")
        try:
            occurred = datetime.fromisoformat(transaction["occurred_at"])
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid transaction timestamp") from exc
        _require(occurred.utcoffset() == timedelta(hours=8), "timestamp must use +08:00")
        _require(occurred.date() <= reference, "future transaction")
        ordered.append((occurred, tx_id, account_id, amount if kind == "INCOME" else -amount))

    for _, _, account_id, delta in sorted(ordered):
        balances[account_id] += delta
        _require(balances[account_id] >= 0, "historical overdraft")
    for account_id, account in accounts.items():
        _require(balances[account_id] == account["balance_minor"], "ledger balance mismatch")
