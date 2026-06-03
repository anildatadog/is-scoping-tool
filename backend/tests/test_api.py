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


# ── /diagnose ─────────────────────────────────────────────────────

_FOUNDATION_ANSWERS = {
    "ddStatus": "new",
    "replacingTool": "no",
    "teamCount": "multi",
    "productScope": ["infra_apm_logs"],
    "infraTopology": ["single-cloud"],
    "sponsor": "exec",
    "authority": "central",
    "capability": "limited",
    "urgency": "flex",
    "compliance": "no",
}


def test_diagnose_returns_shape():
    r = client.post("/diagnose", json={"answers": _FOUNDATION_ANSWERS})
    assert r.status_code == 200
    body = r.json()
    assert "diagnosis" in body
    assert "recommendation" in body
    assert "flags" in body
    assert "next_steps" in body
    assert "service_motion" in body


def test_diagnose_service_motion_is_string():
    r = client.post("/diagnose", json={"answers": _FOUNDATION_ANSWERS})
    assert isinstance(r.json()["service_motion"], str)
    assert len(r.json()["service_motion"]) > 0


def test_diagnose_defer_on_no_sponsor():
    answers = dict(_FOUNDATION_ANSWERS, sponsor="none")
    r = client.post("/diagnose", json={"answers": answers})
    assert r.status_code == 200
    assert r.json()["diagnosis"]["shape"]["value"] == "Defer"
    assert r.json()["service_motion"] == "Discovery / Consultative First"


def test_diagnose_requires_answers_key():
    r = client.post("/diagnose", json={"wrong_key": {}})
    assert r.status_code == 422


# ── /prose ────────────────────────────────────────────────────────

_MOCK_DIAGNOSIS = {
    "shape": {"value": "Foundation", "triggers": []},
    "motion": {"value": "IS-delivered", "triggers": []},
    "binding_constraints": [],
    "triggers": [],
    "customer_ownership": [],
}

_MOCK_PROSE = {
    "diagnosis_paragraph": "Foundation engagement.",
    "consequence_paragraph": "Without IS, governance fails.",
}


def test_prose_returns_paragraphs():
    with patch("main.generate_prose", return_value=_MOCK_PROSE):
        r = client.post("/prose", json={
            "diagnosis": _MOCK_DIAGNOSIS,
            "answers": _FOUNDATION_ANSWERS,
        })
    assert r.status_code == 200
    assert r.json()["diagnosis_paragraph"] == "Foundation engagement."
    assert r.json()["consequence_paragraph"] == "Without IS, governance fails."


def test_prose_returns_nulls_on_failure():
    with patch("main.generate_prose", return_value=None):
        r = client.post("/prose", json={
            "diagnosis": _MOCK_DIAGNOSIS,
            "answers": _FOUNDATION_ANSWERS,
        })
    assert r.status_code == 200
    assert r.json()["diagnosis_paragraph"] is None
    assert r.json()["consequence_paragraph"] is None


def test_prose_returns_nulls_on_exception():
    with patch("main.generate_prose", side_effect=RuntimeError("unexpected")):
        r = client.post("/prose", json={
            "diagnosis": _MOCK_DIAGNOSIS,
            "answers": _FOUNDATION_ANSWERS,
        })
    assert r.status_code == 200
    assert r.json()["diagnosis_paragraph"] is None


def test_prose_requires_both_fields():
    r = client.post("/prose", json={"diagnosis": _MOCK_DIAGNOSIS})
    assert r.status_code == 422


# ── /phase1/motions ───────────────────────────────────────────────

def test_phase1_motions_returns_six():
    r = client.get("/phase1/motions")
    assert r.status_code == 200
    assert len(r.json()) == 6


def test_phase1_motions_keys():
    r = client.get("/phase1/motions")
    assert set(r.json().keys()) == {
        "consultative", "onboarding", "hok",
        "migration", "resident_architect", "discovery",
    }


# ── /phase1/estimate ─────────────────────────────────────────────

def test_phase1_estimate_hok_single_team():
    r = client.post("/phase1/estimate", json={
        "motion": "hok",
        "answers": {"p1_teamCount": "single"},
    })
    assert r.status_code == 200
    body = r.json()
    assert body["days_min"] is not None
    assert body["days_max"] is not None
    assert isinstance(body["pm_required"], bool)


def test_phase1_estimate_discovery_fixed_range():
    r = client.post("/phase1/estimate", json={"motion": "discovery", "answers": {}})
    assert r.status_code == 200
    assert r.json()["days_min"] == 5
    assert r.json()["days_max"] == 10


def test_phase1_estimate_resident_architect_no_range():
    r = client.post("/phase1/estimate", json={"motion": "resident_architect", "answers": {}})
    assert r.status_code == 200
    assert r.json()["days_min"] is None
    assert r.json()["days_max"] is None
    assert r.json()["pm_required"] is True
