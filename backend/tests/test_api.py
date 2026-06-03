"""API endpoint tests. Run from the backend/ directory:
    cd backend && python -m pytest tests/ -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # backend/ on path

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ── /search ───────────────────────────────────────────────────────

from unittest.mock import patch


def test_search_returns_account_list():
    mock_accounts = [
        {"ACCOUNT_ID": "001abc", "ACCOUNT_NAME": "Acme Corp", "SALES_SEGMENT": "Enterprise"},
    ]
    with patch("main.sf.search_accounts", return_value=mock_accounts):
        r = client.get("/search?q=acme")
    assert r.status_code == 200
    assert r.json() == mock_accounts


def test_search_requires_q():
    r = client.get("/search")
    assert r.status_code == 422


def test_search_opp_id_calls_lookup():
    opp = {"OPPORTUNITY_ID": "006abc1234567890", "ACCOUNT_ID": "001abc", "ACCOUNT_NAME": "Acme"}
    full = {"account": opp, "opp": opp, "dd_products": []}
    sf_data = {"accountName": "Acme", "prefill": {}}
    with (
        patch("main.sf.is_opp_id", return_value=True),
        patch("main.sf.lookup_opp_by_id", return_value=opp),
        patch("main.sf.fetch_full", return_value=full),
        patch("main.sf.to_sf_data", return_value=sf_data),
    ):
        r = client.get("/search?q=006abc1234567890")
    assert r.status_code == 200
    assert r.json() == [sf_data]


def test_search_opp_id_not_found():
    with (
        patch("main.sf.is_opp_id", return_value=True),
        patch("main.sf.lookup_opp_by_id", return_value=None),
    ):
        r = client.get("/search?q=006abc1234567890")
    assert r.status_code == 404


# ── /lookup ───────────────────────────────────────────────────────

def test_lookup_returns_sf_data():
    opp = {"OPPORTUNITY_ID": "006abc1234567890", "ACCOUNT_ID": "001abc"}
    full = {"account": opp, "opp": opp, "dd_products": []}
    sf_data = {"accountName": "Acme", "prefill": {"ddStatus": "new"}}
    with (
        patch("main.sf.lookup_opp_by_id", return_value=opp),
        patch("main.sf.fetch_full", return_value=full),
        patch("main.sf.to_sf_data", return_value=sf_data),
    ):
        r = client.get("/lookup?opp_id=006abc1234567890")
    assert r.status_code == 200
    assert r.json()["prefill"]["ddStatus"] == "new"


def test_lookup_not_found():
    with patch("main.sf.lookup_opp_by_id", return_value=None):
        r = client.get("/lookup?opp_id=006abc1234567890")
    assert r.status_code == 404


# ── /accounts/select ─────────────────────────────────────────────

_MOCK_ACCOUNT = {
    "ACCOUNT_ID": "001abc", "ACCOUNT_NAME": "Acme Corp",
    "INDUSTRY": "Technology", "SALES_SEGMENT": "Enterprise",
    "EMPLOYEE_COUNT": 5000, "ACCOUNT_FAMILY_MRR": 50000.0, "CUSTOMER_TIER": "1",
}


def test_accounts_select_returns_sf_data():
    full = {"account": _MOCK_ACCOUNT, "opp": None, "dd_products": []}
    sf_data = {"accountName": "Acme Corp", "prefill": {"ddStatus": "new"}}
    with (
        patch("main.sf.fetch_full", return_value=full),
        patch("main.sf.to_sf_data", return_value=sf_data),
    ):
        r = client.post("/accounts/select", json={"account": _MOCK_ACCOUNT})
    assert r.status_code == 200
    assert r.json()["accountName"] == "Acme Corp"


def test_accounts_select_requires_account_key():
    r = client.post("/accounts/select", json={"wrong": {}})
    assert r.status_code == 422
