"""固定样例与一致性门禁；不冒充后端接口或异常检测已实现。"""

from datetime import date, datetime

import pytest

from bankagent.banking.data.generator import build_demo_data
from bankagent.banking.data.validate import validate_demo_data


def test_fixture_matches_contract_and_returns_fresh_nested_objects():
    first, second = build_demo_data(), build_demo_data()
    assert first == second
    first["accounts"]["account-001"]["balance_minor"] = 0
    first["contacts"]["contact-001"]["display_name"] = "已修改"
    first["transactions"][0]["amount_minor"] = 1
    assert second["accounts"]["account-001"]["balance_minor"] == 500000
    assert second["contacts"]["contact-001"]["display_name"] == "张伟"
    assert second["transactions"][0]["amount_minor"] == 600000


def test_ledger_expenses_and_duplicate_evidence_match_contract():
    data = build_demo_data()
    rows = [t for t in data["transactions"] if t["account_id"] == "account-001"]
    categories = {}
    for row in rows:
        if row["kind"] == "EXPENSE":
            category = row["category"]
            categories[category] = categories.get(category, 0) + row["amount_minor"]
    assert categories == {"居住": 77000, "餐饮": 12000, "交通": 6000, "订阅": 5000}
    assert sum(categories.values()) == 100000
    assert data["reference_date"] == date(2026, 10, 18)
    evidence = [t for t in rows if t["transaction_id"] in {"txn-005", "txn-006"}]
    assert len(evidence) == 2
    assert evidence[0]["merchant"] == evidence[1]["merchant"] == "演示影音会员"
    # 归属靠显式外键，不能只凭同名商户推断。
    assert evidence[0]["subscription_id"] == evidence[1]["subscription_id"] == "sub-001"
    assert evidence[0]["amount_minor"] == evidence[1]["amount_minor"] == 2500
    elapsed = datetime.fromisoformat(evidence[1]["occurred_at"]) - datetime.fromisoformat(
        evidence[0]["occurred_at"])
    assert elapsed.total_seconds() == 30
    assert all(set(t) == {"transaction_id", "account_id", "occurred_at", "kind",
                          "amount_minor", "category", "merchant",
                          "subscription_id"} for t in rows)
    other = [t for t in data["transactions"] if t["account_id"] == "account-002"]
    assert len(other) == 1 and other[0]["amount_minor"] == 40000
    assert data["accounts"]["account-002"]["user_id"] == "user-002"


@pytest.mark.parametrize("value", [True, 2500.0, "2500", -1])
def test_rejects_invalid_money(value):
    data = build_demo_data()
    data["transactions"][4]["amount_minor"] = value
    with pytest.raises(ValueError, match="invalid amount_minor"):
        validate_demo_data(data)


@pytest.mark.parametrize("field,value,reason", [
    ("account_id", "missing", "unknown transaction account"),
    ("transaction_id", "txn-001", "duplicate or invalid transaction id"),
    ("kind", "UNKNOWN", "invalid transaction kind"),
    ("occurred_at", "2026-10-19T00:00:00+08:00", "future transaction"),
    ("occurred_at", "2026-10-12T10:00:00", "timestamp must use"),
    ("occurred_at", "2026-10-12T02:00:00+00:00", "timestamp must use"),
    ("occurred_at", "not-a-date", "invalid transaction timestamp"),
])
def test_rejects_corrupted_transactions(field, value, reason):
    data = build_demo_data()
    data["transactions"][4][field] = value
    with pytest.raises(ValueError, match=reason):
        validate_demo_data(data)


def test_rejects_balance_drift_and_contact_with_unknown_owner():
    data = build_demo_data()
    data["accounts"]["account-001"]["balance_minor"] += 1
    with pytest.raises(ValueError, match="ledger balance mismatch"):
        validate_demo_data(data)
    data = build_demo_data()
    data["contacts"]["contact-001"]["user_id"] = "missing"
    with pytest.raises(ValueError, match="unknown contact owner"):
        validate_demo_data(data)


def test_rejects_hidden_test_labels():
    data = build_demo_data()
    data["transactions"][4]["is_anomaly"] = True
    with pytest.raises(ValueError, match="unexpected transaction fields"):
        validate_demo_data(data)


def test_checks_historical_balance_not_only_final_sum():
    data = build_demo_data()
    data["transactions"][0]["occurred_at"] = "2026-10-17T09:00:00+08:00"
    with pytest.raises(ValueError, match="historical overdraft"):
        validate_demo_data(data)


def test_validator_accepts_order_independent_ledger_and_consistent_transfer():
    data = build_demo_data()
    data["transactions"].reverse()
    data["transactions"].append({
        "transaction_id": "txn-test-transfer", "account_id": "account-001",
        "occurred_at": "2026-10-18T09:00:00+08:00", "kind": "TRANSFER_OUT",
        "amount_minor": 30000, "category": "转账", "merchant": None,
        "subscription_id": None,
    })
    data["accounts"]["account-001"]["balance_minor"] = 470000
    validate_demo_data(data)
    data["accounts"]["account-001"]["balance_minor"] += 1
    with pytest.raises(ValueError, match="ledger balance mismatch"):
        validate_demo_data(data)


def test_card_samples_cover_both_states_account_isolation_and_fresh_copies():
    first, second = build_demo_data(), build_demo_data()
    own = [c for c in first["cards"].values() if c["account_id"] == "account-001"]
    foreign = [c for c in first["cards"].values() if c["account_id"] == "account-002"]
    assert {c["status"] for c in own} == {"ACTIVE", "FROZEN"}
    assert len(foreign) == 1
    # 同名跨账户，后续解析不能按全局名称选择第一条。
    assert foreign[0]["display_name"] == first["cards"]["card-001"]["display_name"]
    first["cards"]["card-001"]["status"] = "FROZEN"
    first["cards"]["card-002"]["display_name"] = "已修改"
    assert second["cards"]["card-001"]["status"] == "ACTIVE"
    assert second["cards"]["card-002"]["display_name"] == "备用卡"


@pytest.mark.parametrize("field,value,reason", [
    ("account_id", "missing", "unknown card account"),
    ("display_name", " ", "card display name required"),
    ("status", "LOST", "invalid card status"),
])
def test_rejects_invalid_card_data(field, value, reason):
    data = build_demo_data()
    data["cards"]["card-001"][field] = value
    with pytest.raises(ValueError, match=reason):
        validate_demo_data(data)


def test_card_data_allows_empty_and_same_name_but_rejects_extra_fields():
    data = build_demo_data()
    data["cards"]["card-002"]["display_name"] = "日常消费卡"
    validate_demo_data(data)  # 名称可重名，后续解析必须处理歧义。
    data["cards"] = {}
    validate_demo_data(data)
    data = build_demo_data()
    data["cards"]["card-001"]["authorized"] = True
    with pytest.raises(ValueError, match="unexpected card fields"):
        validate_demo_data(data)
