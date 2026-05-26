"""Snowflake lookup + field mapper for the scoping tool.

Query structures mirror the `is-salesforce-lookup` skill in
`dd-governed-onboarding-mcp/.claude/commands/is-salesforce-lookup.md`.
"""
from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from functools import lru_cache
from typing import Any

import snowflake.connector


OPP_ID_RE = re.compile(r"^006[a-zA-Z0-9]{15}$")

_REGULATED_KEYWORDS = (
    "financial", "bank", "insurance", "healthcare", "hospital",
    "government", "defence", "defense", "federal", "pharma",
)

_EXEC_KEYWORDS = ("vp ", "vice president", "cto", "cio", "ceo",
                  "cfo", "chief", "president")
_MANAGER_KEYWORDS = ("director", "head of", "senior manager")
_ENGINEER_KEYWORDS = ("engineer", "architect", "developer", "sre")


# ──────────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────────

def _load_private_key() -> bytes | None:
    """Load an RSA private key in DER format for Snowflake key-pair auth.

    Looks for SNOWFLAKE_PRIVATE_KEY (PEM string, useful in Howler secrets)
    or SNOWFLAKE_PRIVATE_KEY_PATH (path to a PEM file).
    Returns DER-encoded bytes the Snowflake connector accepts, or None if no
    key-pair material is configured.
    """
    pem_str = os.environ.get("SNOWFLAKE_PRIVATE_KEY")
    pem_path = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH")
    if not pem_str and not pem_path:
        return None

    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization

    if pem_str:
        pem_bytes = pem_str.encode("utf-8")
    else:
        with open(pem_path, "rb") as f:
            pem_bytes = f.read()

    passphrase = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
    pk = serialization.load_pem_private_key(
        pem_bytes,
        password=passphrase.encode() if passphrase else None,
        backend=default_backend(),
    )
    return pk.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


@lru_cache(maxsize=1)
def _connect() -> snowflake.connector.SnowflakeConnection:
    common = dict(
        account=os.environ.get("SNOWFLAKE_ACCOUNT", "sza96462.us-east-1"),
        user=os.environ["SNOWFLAKE_USER"],
        database=os.environ.get("SNOWFLAKE_DATABASE", "REPORTING"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "AD_HOC_DEVELOPMENT_XSMALL_WAREHOUSE"),
        client_session_keep_alive=True,
    )
    private_key = _load_private_key()
    if private_key is not None:
        return snowflake.connector.connect(**common, private_key=private_key)
    return snowflake.connector.connect(**common, authenticator="externalbrowser")


def _query(sql: str, params: dict | None = None) -> list[dict]:
    conn = _connect()
    cur = conn.cursor(snowflake.connector.DictCursor)
    try:
        cur.execute(sql, params or {})
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()


# ──────────────────────────────────────────────────────────────────
# Lookups
# ──────────────────────────────────────────────────────────────────

def is_opp_id(query: str) -> bool:
    return bool(OPP_ID_RE.match(query.strip()))


def search_accounts(search_term: str, limit: int = 5) -> list[dict]:
    """Returns up to `limit` matching accounts for disambiguation."""
    sql = """
        SELECT a.ACCOUNT_ID, a.ACCOUNT_NAME, a.INDUSTRY, a.SALES_SEGMENT,
               a.EMPLOYEE_COUNT, a.ACCOUNT_FAMILY_MRR, a.CUSTOMER_TIER
        FROM REPORTING.GTM.DIM_SFDC_ACCOUNT_RESTRICTED a
        WHERE UPPER(a.ACCOUNT_NAME) LIKE %(pattern)s
          AND a.IS_MOST_RECENT_DATE = TRUE
        ORDER BY a.ACCOUNT_FAMILY_MRR DESC NULLS LAST
        LIMIT %(limit)s
    """
    pattern = f"%{search_term.strip().upper()}%"
    return _query(sql, {"pattern": pattern, "limit": limit})


def lookup_opp_by_id(opp_id: str) -> dict | None:
    """Returns the opp row joined to its account, or None."""
    sql = """
        SELECT o.OPPORTUNITY_ID, o.OPPORTUNITY_NAME, o.PRODUCTS_IN_SCOPE,
               o.CURRENT_ENVIRONMENT_TOOLS, o.PRIMARY_COMPETITOR,
               o.PRIMARY_COMPETITOR_INCUMBENT_STATUS,
               o.CHAMPION, o.ECONOMIC_BUYER, o.CLOSE_DATE, o.TYPE, o.STAGE,
               a.ACCOUNT_ID, a.ACCOUNT_NAME, a.INDUSTRY, a.SALES_SEGMENT,
               a.EMPLOYEE_COUNT, a.ACCOUNT_FAMILY_MRR, a.CUSTOMER_TIER
        FROM REPORTING.GTM.DIM_SFDC_OPPORTUNITY_RESTRICTED o
        JOIN REPORTING.GTM.DIM_SFDC_ACCOUNT_RESTRICTED a ON o.ACCOUNT_ID = a.ACCOUNT_ID
        WHERE o.OPPORTUNITY_ID = %(opp_id)s
          AND o.IS_MOST_RECENT_DATE = TRUE
          AND a.IS_MOST_RECENT_DATE = TRUE
        LIMIT 1
    """
    rows = _query(sql, {"opp_id": opp_id.strip()})
    return rows[0] if rows else None


def fetch_open_opp(account_id: str) -> dict | None:
    sql = """
        SELECT o.OPPORTUNITY_ID, o.OPPORTUNITY_NAME, o.PRODUCTS_IN_SCOPE,
               o.CURRENT_ENVIRONMENT_TOOLS, o.PRIMARY_COMPETITOR,
               o.PRIMARY_COMPETITOR_INCUMBENT_STATUS,
               o.CHAMPION, o.ECONOMIC_BUYER, o.CLOSE_DATE, o.TYPE, o.STAGE
        FROM REPORTING.GTM.DIM_SFDC_OPPORTUNITY_RESTRICTED o
        WHERE o.ACCOUNT_ID = %(account_id)s
          AND o.IS_MOST_RECENT_DATE = TRUE
          AND o.STAGE NOT IN ('Closed Lost', 'Closed Won')
        ORDER BY o.CLOSE_DATE ASC NULLS LAST
        LIMIT 1
    """
    rows = _query(sql, {"account_id": account_id})
    return rows[0] if rows else None


def fetch_dd_product_count(account_id: str) -> int:
    sql = """
        SELECT COUNT(*) AS DD_PRODUCT_COUNT
        FROM REPORTING.BILLING.CS_PRODUCT_ATTACH p
        WHERE p.SALESFORCE_ACCOUNT_ID = %(account_id)s
          AND p.IS_WON = 1
    """
    rows = _query(sql, {"account_id": account_id})
    return int(rows[0]["DD_PRODUCT_COUNT"]) if rows else 0


def fetch_full(account: dict) -> dict:
    """Given an account row, fetch open opp + DD product count in parallel."""
    account_id = account["ACCOUNT_ID"]
    with ThreadPoolExecutor(max_workers=2) as ex:
        opp_f = ex.submit(fetch_open_opp, account_id)
        dd_f = ex.submit(fetch_dd_product_count, account_id)
        opp = opp_f.result()
        dd_count = dd_f.result()
    return {"account": account, "opp": opp, "dd_product_count": dd_count}


# ──────────────────────────────────────────────────────────────────
# Field mapping
# ──────────────────────────────────────────────────────────────────

def _map_dd_status(dd_product_count: int) -> str:
    return "live" if dd_product_count > 0 else "new"


def _map_compliance(industry: str | None) -> str:
    if not industry:
        return "no"
    industry_lc = industry.lower()
    return "yes" if any(kw in industry_lc for kw in _REGULATED_KEYWORDS) else "no"


def _map_team_count(sales_segment: str | None, employee_count: int | None) -> str | None:
    seg = (sales_segment or "").lower()
    emp = employee_count or 0

    # Segment first if recognisable, fall back to employee count
    if "enterprise" in seg or emp >= 10000:
        return "large"
    if "mid-market" in seg or "mid market" in seg or 2000 <= emp < 10000:
        return "enterprise"
    if "commercial" in seg or 200 <= emp < 2000:
        return "multi"
    if "smb" in seg or "small" in seg or (0 < emp < 200):
        return "single"
    return None


def _count_products(products_in_scope: Any) -> str | None:
    """`PRODUCTS_IN_SCOPE` is a semicolon- or comma-delimited string in SF."""
    if not products_in_scope:
        return None
    if isinstance(products_in_scope, list):
        items = products_in_scope
    else:
        s = str(products_in_scope)
        # Try common Salesforce multipick delimiters
        for sep in (";", ","):
            if sep in s:
                items = [p.strip() for p in s.split(sep) if p.strip()]
                break
        else:
            items = [s.strip()] if s.strip() else []
    n = len(items)
    if n <= 0:
        return None
    if n <= 2:
        return "1-2"
    if n <= 4:
        return "3-4"
    if n <= 7:
        return "5-7"
    return "suite"


def _map_sponsor(champion: str | None, economic_buyer: str | None) -> str | None:
    blob = " ".join(filter(None, [champion, economic_buyer])).lower()
    if not blob.strip():
        return None
    if any(kw in blob for kw in _EXEC_KEYWORDS):
        return "exec"
    if any(kw in blob for kw in _MANAGER_KEYWORDS):
        return "manager"
    if any(kw in blob for kw in _ENGINEER_KEYWORDS):
        return "engineer"
    return None


def _map_urgency(close_date: Any) -> str | None:
    if not close_date:
        return "target"
    if isinstance(close_date, str):
        try:
            close_date = datetime.fromisoformat(close_date).date()
        except ValueError:
            return None
    elif isinstance(close_date, datetime):
        close_date = close_date.date()
    if not isinstance(close_date, date):
        return None
    days = (close_date - date.today()).days
    if days < 90:
        return "hard"
    if days <= 180:
        return "target"
    return "flex"


def _map_replacing_tool(incumbent_status: str | None, current_env_tools: str | None) -> str | None:
    if incumbent_status and "incumbent" in incumbent_status.lower():
        return "yes"
    if current_env_tools and current_env_tools.strip():
        return "yes"
    return None


def to_prefill(full: dict) -> dict:
    """Maps a `fetch_full` result to the prefill answer dict the questionnaire consumes."""
    account = full["account"]
    opp = full.get("opp") or {}
    dd_count = full.get("dd_product_count", 0)

    prefill: dict = {}

    prefill["ddStatus"] = _map_dd_status(dd_count)

    compliance = _map_compliance(account.get("INDUSTRY"))
    if compliance:
        prefill["compliance"] = compliance

    team = _map_team_count(account.get("SALES_SEGMENT"), account.get("EMPLOYEE_COUNT"))
    if team:
        prefill["teamCount"] = team

    products = _count_products(opp.get("PRODUCTS_IN_SCOPE"))
    if products:
        prefill["productCount"] = products

    sponsor = _map_sponsor(opp.get("CHAMPION"), opp.get("ECONOMIC_BUYER"))
    if sponsor:
        prefill["sponsor"] = sponsor

    urgency = _map_urgency(opp.get("CLOSE_DATE"))
    if urgency:
        prefill["urgency"] = urgency

    replacing = _map_replacing_tool(
        opp.get("PRIMARY_COMPETITOR_INCUMBENT_STATUS"),
        opp.get("CURRENT_ENVIRONMENT_TOOLS"),
    )
    if replacing:
        prefill["replacingTool"] = replacing

    return prefill


def to_sf_data(full: dict) -> dict:
    """Maps a `fetch_full` result to the display object used in the UI banner + scoping doc."""
    account = full["account"]
    opp = full.get("opp") or {}
    return {
        "accountId": account.get("ACCOUNT_ID"),
        "accountName": account.get("ACCOUNT_NAME"),
        "industry": account.get("INDUSTRY"),
        "salesSegment": account.get("SALES_SEGMENT"),
        "employeeCount": account.get("EMPLOYEE_COUNT"),
        "accountFamilyMRR": float(account["ACCOUNT_FAMILY_MRR"]) if account.get("ACCOUNT_FAMILY_MRR") else None,
        "customerTier": account.get("CUSTOMER_TIER"),
        "oppId": opp.get("OPPORTUNITY_ID"),
        "oppName": opp.get("OPPORTUNITY_NAME"),
        "oppStage": opp.get("STAGE"),
        "oppCloseDate": opp.get("CLOSE_DATE").isoformat() if isinstance(opp.get("CLOSE_DATE"), (date, datetime)) else opp.get("CLOSE_DATE"),
        "hasExistingDD": full.get("dd_product_count", 0) > 0,
        "prefill": to_prefill(full),
    }
