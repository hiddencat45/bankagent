"""Ordinary regression must never inherit a user's live ledger or model credentials."""
import os
import pytest


@pytest.fixture(autouse=True)
def isolate_application_environment(monkeypatch):
    for name in tuple(os.environ):
        if name.startswith('BANKAGENT_MODEL_') or name in {
                'BANKAGENT_DB_PATH', 'BANKAGENT_LOCAL_LOGIN', 'BANKAGENT_DEMO_ALLOW_LAN'}:
            monkeypatch.delenv(name, raising=False)
