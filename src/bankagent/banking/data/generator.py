"""按阶段 0 契约构造固定样例，不随机编造业务事实或异常标签。

返回新的内部数据集供后续模拟后端加载，不写文件、不修改教学图。
它不是对用户/模型公开的数据接口，不能直接作为 API 响应。
"""

from datetime import date

from .validate import validate_demo_data


REFERENCE_DATE = date(2026, 10, 18)


def build_demo_data() -> dict:
    """返回已校验、彼此独立的固定账户/联系人/卡片/账本，金额单位为分。"""
    accounts = {
        "account-001": {"user_id": "user-001", "balance_minor": 500000,
                        "currency": "CNY"},
        "account-002": {"user_id": "user-002", "balance_minor": 40000,
                        "currency": "CNY"},
        "account-003": {"user_id": "user-003", "balance_minor": 0,
                        "currency": "CNY"},
        "account-card-card-002": {"user_id": "user-001", "balance_minor": 0,
                        "currency": "CNY", "display_name": "备用卡独立账户"},
    }
    contacts = {
        "contact-001": {"user_id": "user-001", "display_name": "张伟", "recipient_account_id": "account-002"},
        "contact-002": {"user_id": "user-001", "display_name": "李娜", "recipient_account_id": "account-003"},
    }
    # 只准备内部状态；不含卡号，也不表示冻结/解冻接口已经启用。
    cards = {
        "card-001": {"account_id": "account-001", "display_name": "日常消费卡",
                     "status": "ACTIVE"},
        "card-002": {"account_id": "account-card-card-002", "display_name": "备用卡",
                     "status": "FROZEN"},
        "card-003": {"account_id": "account-002", "display_name": "日常消费卡",
                     "status": "ACTIVE"},
    }
    # 月度代扣协议。merchant 与 display_name 一致，账单流水才能归到某条协议上：
    # txn-005/006 就是 sub-001 在同一分钟内被扣了两次，账单里表现为疑似重复。
    subscriptions = {
        "sub-001": {"account_id": "account-001", "display_name": "演示影音会员",
                    "status": "ACTIVE", "amount_minor": 2500, "currency": "CNY",
                    "next_payment_date": "2026-11-12"},
        "sub-002": {"account_id": "account-001", "display_name": "演示云存储",
                    "status": "PAUSED", "amount_minor": 1200, "currency": "CNY",
                    "next_payment_date": None},
        "sub-003": {"account_id": "account-002", "display_name": "演示健身",
                    "status": "ACTIVE", "amount_minor": 9900, "currency": "CNY",
                    "next_payment_date": "2026-11-01"},
    }
    rows = (
        ("txn-001", "account-001", "2026-10-01T09:00:00+08:00",
         "INCOME", 600000, "工资", "演示雇主", None),
        ("txn-002", "account-001", "2026-10-02T09:00:00+08:00",
         "EXPENSE", 77000, "居住", "演示租赁", None),
        ("txn-003", "account-001", "2026-10-10T12:00:00+08:00",
         "EXPENSE", 12000, "餐饮", "演示餐厅", None),
        ("txn-004", "account-001", "2026-10-11T08:00:00+08:00",
         "EXPENSE", 6000, "交通", "演示交通", None),
        ("txn-005", "account-001", "2026-10-12T10:00:00+08:00",
         "EXPENSE", 2500, "订阅", "演示影音会员", "sub-001"),
        ("txn-006", "account-001", "2026-10-12T10:00:30+08:00",
         "EXPENSE", 2500, "订阅", "演示影音会员", "sub-001"),
        ("txn-007", "account-002", "2026-10-01T09:00:00+08:00",
         "INCOME", 40000, "工资", "演示雇主", None),
    )
    fields = ("transaction_id", "account_id", "occurred_at", "kind",
              "amount_minor", "category", "merchant", "subscription_id")
    data = {
        "reference_date": REFERENCE_DATE,
        "accounts": accounts,
        "contacts": contacts,
        "cards": cards,
        "subscriptions": subscriptions,
        "transactions": [dict(zip(fields, row)) for row in rows],
    }
    validate_demo_data(data)
    return data
