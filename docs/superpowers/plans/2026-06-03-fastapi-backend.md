# FastAPI Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI backend in `backend/` that wraps all existing Python business logic behind 6 JSON endpoints, ready for the Next.js frontend to consume.

**Architecture:** All existing Python modules (`diagnosis.py`, `methodologies.py`, `phase1.py`, `prose.py`, `scoping_doc.py`, `snowflake_lookup.py`) are copied into `backend/` unchanged. `backend/main.py` is a thin FastAPI wrapper — no logic lives there. Two Cloud Run services will exist: this backend (internal) and the future Next.js frontend (public). The Streamlit service remains live and untouched until the frontend is ready.

**Tech Stack:** Python 3.11, FastAPI 0.115+, uvicorn, pydantic v2, pytest + httpx TestClient, unittest.mock for Snowflake/Anthropic.

---

## File Map

| File | Change |
|------|--------|
| `backend/main.py` | **Create** — FastAPI app, CORS, all 6 endpoints |
| `backend/requirements.txt` | **Create** — FastAPI, uvicorn, snowflake, anthropic (no Streamlit) |
| `backend/Dockerfile` | **Create** — Python 3.11-slim, uvicorn entrypoint |
| `backend/diagnosis.py` | **Copy** from root |
| `backend/methodologies.py` | **Copy** from root |
| `backend/phase1.py` | **Copy** from root |
| `backend/prose.py` | **Copy** from root |
| `backend/scoping_doc.py` | **Copy** from root |
| `backend/snowflake_lookup.py` | **Copy** from root |
| `backend/tests/__init__.py` | **Create** — empty |
| `backend/tests/test_api.py` | **Create** — TestClient tests for all endpoints |
| `shared/api-types.ts` | **Create** — TypeScript request/response shapes for the frontend |

**Note on module drift:** Copying root modules into `backend/` creates drift risk — any change to the root must be manually mirrored. Once the frontend path is proven and Streamlit is retired, extract shared domain logic into a proper Python package. Until then, treat root and backend copies as temporarily duplicated, not independent.

---

## Task 1: Scaffold `backend/` directory

**Files:**
- Create: `backend/requirements.txt`
- Copy: all Python modules from root

- [ ] **Step 1.1: Create `backend/requirements.txt`**

```
fastapi>=0.115
uvicorn[standard]>=0.30
pydantic>=2.0
snowflake-connector-python>=3.12
cryptography>=42
anthropic>=0.42
httpx>=0.27
pytest>=8
pytest-asyncio>=0.23
```

- [ ] **Step 1.2: Copy Python modules into `backend/`**

```bash
cp diagnosis.py methodologies.py phase1.py prose.py scoping_doc.py snowflake_lookup.py backend/
```

- [ ] **Step 1.3: Create `backend/tests/__init__.py`**

```bash
mkdir -p backend/tests && touch backend/tests/__init__.py
```

- [ ] **Step 1.4: Install backend dependencies**

```bash
cd backend && pip install -r requirements.txt
```

- [ ] **Step 1.5: Verify imports work**

```bash
cd backend && python -c "
from diagnosis import diagnose
from methodologies import recommend
from phase1 import MOTIONS, fast_estimate
from prose import generate
print('all imports OK')
"
```
Expected: `all imports OK`

- [ ] **Step 1.6: Commit**

```bash
cd ..  # back to repo root
git add backend/
git commit -m "feat: scaffold backend/ directory with copied Python modules"
```

---

## Task 2: Health check endpoint

**Files:**
- Create: `backend/main.py`
- Create: `backend/tests/test_api.py`

- [ ] **Step 2.1: Write failing test** — create `backend/tests/test_api.py`:

```python
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
```

- [ ] **Step 2.2: Run to confirm failure:**

```bash
cd backend && python -m pytest tests/test_api.py::test_health -v
```
Expected: `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 2.3: Create `backend/main.py`:**

```python
"""IS Scoping — FastAPI backend.

Thin wrapper around existing Python business logic. No logic lives here.
All routes delegate immediately to domain modules.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import snowflake_lookup as sf
from diagnosis import diagnose, to_service_motion
from methodologies import recommend, build_flags, build_next_steps
from phase1 import MOTIONS, fast_estimate
from prose import generate as generate_prose

app = FastAPI(title="IS Scoping Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # local dev only — in prod, backend is internal Cloud Run
    allow_credentials=False,      # no cookies between frontend and backend; IAM handles auth
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── Request models ────────────────────────────────────────────────

class DiagnoseRequest(BaseModel):
    answers: dict


class ProseRequest(BaseModel):
    diagnosis: dict
    answers: dict


class EstimateRequest(BaseModel):
    motion: str
    answers: dict


class SelectAccountRequest(BaseModel):
    account: dict  # full account row from /search results (ACCOUNT_ID + all fields)


# ── Endpoints ─────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 2.4: Run test:**

```bash
cd backend && python -m pytest tests/test_api.py::test_health -v
```
Expected: PASS

- [ ] **Step 2.5: Commit:**

```bash
git add backend/main.py backend/tests/test_api.py
git commit -m "feat: FastAPI app scaffold with health endpoint"
```

---

## Task 3: `/search` and `/lookup` endpoints

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 3.1: Write failing tests** — append to `backend/tests/test_api.py`:

```python
from unittest.mock import patch


# ── /search ───────────────────────────────────────────────────────

def test_search_returns_account_list():
    mock_accounts = [
        {"accountId": "001abc", "accountName": "Acme Corp", "salesSegment": "Enterprise"},
    ]
    with patch("main.sf.search_accounts", return_value=mock_accounts):
        r = client.get("/search?q=acme")
    assert r.status_code == 200
    assert r.json() == mock_accounts


def test_search_requires_q():
    r = client.get("/search")
    assert r.status_code == 422


def test_search_opp_id_calls_lookup(monkeypatch):
    opp = {"opportunityId": "006abc1234567890", "accountId": "001abc", "accountName": "Acme"}
    full = {"opportunityId": "006abc1234567890", "accountId": "001abc", "accountName": "Acme",
            "ddProducts": [], "accountFamilyMRR": None}
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
    opp = {"opportunityId": "006abc1234567890", "accountId": "001abc"}
    full = {"opportunityId": "006abc1234567890", "accountId": "001abc",
            "ddProducts": [], "accountFamilyMRR": None}
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
```

- [ ] **Step 3.2: Run to confirm failures:**

```bash
cd backend && python -m pytest tests/test_api.py -k "search or lookup" -v
```
Expected: all fail with `404` or attribute errors — `/search` and `/lookup` don't exist yet.

- [ ] **Step 3.3: Add endpoints to `backend/main.py`** — append after the health endpoint:

```python
@app.get("/search")
def search(q: str = Query(..., min_length=1)) -> list[dict]:
    """Search by account name or opp ID.

    If q looks like an opp ID (006...), fetches the full SF data object
    directly and returns it as a single-element list so the client can
    handle both shapes uniformly.
    """
    if sf.is_opp_id(q):
        opp = sf.lookup_opp_by_id(q)
        if opp is None:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        full = sf.fetch_full(opp)
        return [sf.to_sf_data(full)]
    return sf.search_accounts(q)


@app.get("/lookup")
def lookup(opp_id: str = Query(...)) -> dict:
    """Full SF data fetch for a known opp ID. Returns the sf_data dict
    (accountName, prefill answers, MRR, contracted products)."""
    opp = sf.lookup_opp_by_id(opp_id)
    if opp is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    full = sf.fetch_full(opp)
    return sf.to_sf_data(full)
```

- [ ] **Step 3.4: Run tests:**

```bash
cd backend && python -m pytest tests/test_api.py -k "search or lookup" -v
```
Expected: all 5 tests pass.

- [ ] **Step 3.5: Add failing tests for `/accounts/select`** — append to `backend/tests/test_api.py`:

```python
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
```

- [ ] **Step 3.6: Add `/accounts/select` endpoint to `backend/main.py`** — append:

```python
@app.post("/accounts/select")
def accounts_select(req: SelectAccountRequest) -> dict:
    """Given an account row from /search, fetch the open opportunity and
    contracted DD products, then return the full sf_data dict with prefill.

    The client sends back the account dict it received from /search so we
    avoid a redundant Snowflake account query.
    """
    full = sf.fetch_full(req.account)
    return sf.to_sf_data(full)
```

- [ ] **Step 3.7: Run tests:**

```bash
cd backend && python -m pytest tests/test_api.py -k "search or lookup or select" -v
```
Expected: all 7 tests pass.

- [ ] **Step 3.8: Commit:**

```bash
git add backend/main.py backend/tests/test_api.py
git commit -m "feat: /search, /lookup, and /accounts/select endpoints"
```

---

## Task 4: `/diagnose` endpoint

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/tests/test_api.py`

The `/diagnose` endpoint is pure Python — no external calls. Tests run without mocking.

- [ ] **Step 4.1: Write failing tests** — append to `backend/tests/test_api.py`:

```python
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
```

- [ ] **Step 4.2: Run to confirm failures:**

```bash
cd backend && python -m pytest tests/test_api.py -k "diagnose" -v
```
Expected: all fail — `/diagnose` doesn't exist yet.

- [ ] **Step 4.3: Add endpoint to `backend/main.py`** — append:

```python
@app.post("/diagnose")
def diagnose_endpoint(req: DiagnoseRequest) -> dict:
    """Run the full diagnostic engine on a completed answer set.

    Returns the structured diagnosis, v1 session recommendation, risk flags,
    next steps, and the AE-facing service motion label.
    """
    diag = diagnose(req.answers)
    rec = recommend(req.answers)
    flags = build_flags(req.answers, rec["key"], rec.get("sMax"))
    next_steps = build_next_steps(req.answers, rec["key"])
    service_motion = to_service_motion(
        diag["shape"]["value"], diag["motion"]["value"]
    )
    return {
        "diagnosis": diag,
        "recommendation": rec,
        "flags": flags,
        "next_steps": next_steps,
        "service_motion": service_motion,
    }
```

- [ ] **Step 4.4: Run tests:**

```bash
cd backend && python -m pytest tests/test_api.py -k "diagnose" -v
```
Expected: all 4 tests pass.

- [ ] **Step 4.5: Commit:**

```bash
git add backend/main.py backend/tests/test_api.py
git commit -m "feat: /diagnose endpoint"
```

---

## Task 5: `/prose` endpoint

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 5.1: Write failing tests** — append to `backend/tests/test_api.py`:

```python
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


def test_prose_requires_both_fields():
    r = client.post("/prose", json={"diagnosis": _MOCK_DIAGNOSIS})
    assert r.status_code == 422


def test_prose_returns_nulls_on_exception():
    with patch("main.generate_prose", side_effect=RuntimeError("unexpected")):
        r = client.post("/prose", json={
            "diagnosis": _MOCK_DIAGNOSIS,
            "answers": _FOUNDATION_ANSWERS,
        })
    assert r.status_code == 200
    assert r.json()["diagnosis_paragraph"] is None
```

- [ ] **Step 5.2: Run to confirm failures:**

```bash
cd backend && python -m pytest tests/test_api.py -k "prose" -v
```
Expected: all fail — `/prose` doesn't exist yet.

- [ ] **Step 5.3: Add endpoint to `backend/main.py`** — append:

```python
@app.post("/prose")
def prose_endpoint(req: ProseRequest) -> dict:
    """Generate consulting-voice diagnosis and consequence paragraphs.

    Returns null paragraphs on any failure (missing key, API error, parse
    error, or any unexpected exception). Callers must handle null gracefully.
    prose.generate() catches most Anthropic failures internally, but the
    broad except here guards against any uncaught runtime error.
    """
    try:
        result = generate_prose(req.diagnosis, req.answers)
    except Exception:
        result = None
    if result is None:
        return {"diagnosis_paragraph": None, "consequence_paragraph": None}
    return result
```

- [ ] **Step 5.4: Run tests:**

```bash
cd backend && python -m pytest tests/test_api.py -k "prose" -v
```
Expected: all 3 tests pass.

- [ ] **Step 5.5: Commit:**

```bash
git add backend/main.py backend/tests/test_api.py
git commit -m "feat: /prose endpoint"
```

---

## Task 6: Phase 1 endpoints

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 6.1: Write failing tests** — append to `backend/tests/test_api.py`:

```python
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
```

- [ ] **Step 6.2: Run to confirm failures:**

```bash
cd backend && python -m pytest tests/test_api.py -k "phase1" -v
```
Expected: all fail — `/phase1/*` endpoints don't exist yet.

- [ ] **Step 6.3: Add endpoints to `backend/main.py`** — append:

```python
@app.get("/phase1/motions")
def phase1_motions() -> dict:
    """Return the 6 named service motions for the Phase 1 selector UI."""
    return MOTIONS


@app.post("/phase1/estimate")
def phase1_estimate(req: EstimateRequest) -> dict:
    """Rough day-range estimate from Phase 1 motion + minimal inputs.

    Returns days_min/days_max (int or null), pm_required (bool), and
    optionally a 'label' string when no numeric range applies (Resident
    Architect).
    """
    return fast_estimate(req.motion, req.answers)
```

- [ ] **Step 6.4: Run tests:**

```bash
cd backend && python -m pytest tests/test_api.py -k "phase1" -v
```
Expected: all 5 tests pass.

- [ ] **Step 6.5: Run full test suite:**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: all tests pass.

- [ ] **Step 6.6: Commit:**

```bash
git add backend/main.py backend/tests/test_api.py
git commit -m "feat: Phase 1 endpoints (/phase1/motions, /phase1/estimate)"
```

---

## Task 7: Dockerfile

**Files:**
- Create: `backend/Dockerfile`

No test needed — verified at deploy time.

- [ ] **Step 7.1: Create `backend/Dockerfile`:**

```dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
# Cache-bust marker (bump when deps change):
# 2026-06-03 fastapi-backend-initial
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 7.2: Verify it builds locally:**

```bash
cd backend && docker build -t is-scoping-backend:local . 2>&1 | tail -5
```
Expected: `Successfully built ...`

- [ ] **Step 7.3: Commit:**

```bash
git add backend/Dockerfile
git commit -m "feat: backend Dockerfile"
```

---

## Task 8: TypeScript API types for the frontend

**Files:**
- Create: `shared/api-types.ts`

- [ ] **Step 8.1: Create `shared/api-types.ts`:**

```typescript
// Shared request/response types between is-scoping-backend and the Next.js frontend.
// Generated from FastAPI endpoint contracts — keep in sync with backend/main.py.

// ── /search ──────────────────────────────────────────────────────
// Note: search_accounts() returns Snowflake column names in UPPER_CASE.

export interface AccountResult {
  ACCOUNT_ID: string;
  ACCOUNT_NAME: string;
  INDUSTRY?: string;
  SALES_SEGMENT?: string;
  EMPLOYEE_COUNT?: number;
  ACCOUNT_FAMILY_MRR?: number;
  CUSTOMER_TIER?: string;
}

// ── /accounts/select ─────────────────────────────────────────────

export interface SelectAccountRequest {
  account: AccountResult;  // full row from /search — sent back to avoid re-query
}

// ── /lookup ──────────────────────────────────────────────────────

export interface SfData {
  accountName: string;
  accountId?: string;
  opportunityId?: string;
  accountFamilyMRR?: number;
  ddProducts?: string[];
  prefill: Record<string, string | string[]>;
}

// ── /diagnose ────────────────────────────────────────────────────

export interface DiagnoseRequest {
  answers: Record<string, string | string[]>;
}

export interface DiagnosisField {
  value: string;
  triggers: Array<[string, string]>;
}

export interface Diagnosis {
  shape: DiagnosisField;
  motion: DiagnosisField;
  binding_constraints: DiagnosisField[];
  triggers: Array<{ signal: string; value: string; contributed_to: string[] }>;
  customer_ownership: string[];
}

export interface Flag {
  t: "blk" | "wrn" | "inf" | "ok";
  m: string;
}

export interface DiagnoseResponse {
  diagnosis: Diagnosis;
  recommendation: {
    key: string;
    sMin: number | null;
    sMax: number | null;
  };
  flags: Flag[];
  next_steps: string[];
  service_motion: string;
}

// ── /prose ───────────────────────────────────────────────────────

export interface ProseRequest {
  diagnosis: Diagnosis;
  answers: Record<string, string | string[]>;
}

export interface ProseResponse {
  diagnosis_paragraph: string | null;
  consequence_paragraph: string | null;
}

// ── /phase1/motions ──────────────────────────────────────────────

export interface Motion {
  label: string;
  ask: string;
  desc: string;
  icon: string;
}

export type MotionsResponse = Record<string, Motion>;

// ── /phase1/estimate ─────────────────────────────────────────────

export interface EstimateRequest {
  motion: string;
  answers: Record<string, string | string[]>;
}

export interface EstimateResponse {
  days_min: number | null;
  days_max: number | null;
  pm_required: boolean;
  label?: string;
}
```

- [ ] **Step 8.2: Commit:**

```bash
git add shared/api-types.ts
git commit -m "feat: shared TypeScript API types for frontend"
```

---

## Self-Review

### Spec coverage
- [x] `GET /search?q=` → search_accounts or opp ID lookup — Task 3
- [x] `GET /lookup?opp_id=` → full SF data fetch — Task 3
- [x] `POST /diagnose` → diagnose + recommend + flags + next_steps + service_motion — Task 4
- [x] `POST /prose` → generate_prose, graceful null on failure — Task 5
- [x] Phase 1 endpoints (motions, estimate) — Task 6
- [x] Dockerfile — Task 7
- [x] TypeScript shared types — Task 8
- [x] CORS middleware — Task 2 (main.py scaffold)
- [x] All existing Python modules copied unchanged — Task 1
- [x] Tests for all endpoints — Tasks 2-6
- [x] Snowflake calls mocked in tests — Tasks 3, 5
- [x] Anthropic call mocked in prose test — Task 5

### Gaps
- Deploy command is in the spec but not in this plan — it's a one-liner once built:
  ```bash
  gcloud run deploy is-scoping-backend \
    --source backend/ --project=datadog-tam-sandbox --region=us-central1 \
    --no-allow-unauthenticated \
    --vpc-connector=is-scoping-tool-vpc --vpc-egress=all-traffic \
    --set-secrets="SNOWFLAKE_PAT=is-scoping-pat:latest,SNOWFLAKE_USER=is-scoping-user:latest,ANTHROPIC_API_KEY=is-scoping-anthropic-key:latest" \
    --set-env-vars="SNOWFLAKE_ACCOUNT=sza96462.us-east-1,SNOWFLAKE_DATABASE=REPORTING,SNOWFLAKE_WAREHOUSE=AD_HOC_DEVELOPMENT_XSMALL_WAREHOUSE"
  ```
  Run this after all tasks complete and pass.
