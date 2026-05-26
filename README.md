# IS Scoping Tool

AE-facing scoping tool for sizing Datadog Implementation Services engagements.

Walks an AE through 11 business-language questions about a customer opportunity, pre-filled from Salesforce data where possible, and returns a recommended IS methodology with a session estimate and pre-close checklist.

## Local development

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env
uv run streamlit run streamlit_app.py
```

First Snowflake query opens a browser for Datadog SSO. Subsequent queries reuse the cached token.

## Project structure

```
streamlit_app.py        # UI: search, questionnaire, result
snowflake_lookup.py     # Snowflake connection + lookup + field mapper
methodologies.py        # QUESTIONS, METHODS, recommend, flags, next steps
scoping_doc.py          # Copy-paste summary formatter
```

## Reference

- Handover doc: [IS Scoping Tool, Claude Code Handover](https://docs.google.com/document/d/1wh13MJalmtK7DrlLyUCW5aM4VEJtQbG0p0pxyXUgJ2U)
- Snowflake query patterns: `dd-governed-onboarding-mcp/.claude/commands/is-salesforce-lookup.md`
- Plan: `~/.claude/plans/velvety-dreaming-spark.md`

## Deploying to Howler

Howler is Datadog's heroku-style internal hosting (behind AppGate VPN, so Datadog-employee-only by default). Streamlit is a known pattern there.

The service has already been created at `https://is-scoping.us1.staging.dog` (Howler service ID `276`).

Prereq: a Snowflake **service user** with key-pair auth. Local dev uses your SSO; Howler can't open a browser, so it needs the service user. Request via the [DNAINT project](https://datadoghq.atlassian.net/projects/DNAINT) (see `DNAINT-2917` as a recent example).

### Howler secrets

Set these on the service page (encrypted, mounted at `/etc/datadog/secrets`):

| Secret | Value |
|---|---|
| `SNOWFLAKE_USER` | the service user login (e.g. `IS_SCOPING_TOOL_SVC`) |
| `SNOWFLAKE_PRIVATE_KEY` | full PEM of the RSA private key |
| `SNOWFLAKE_ACCOUNT` | `sza96462.us-east-1` |
| `SNOWFLAKE_DATABASE` | `REPORTING` |
| `SNOWFLAKE_WAREHOUSE` | `AD_HOC_DEVELOPMENT_XSMALL_WAREHOUSE` |

### Build + deploy

Connect to AppGate VPN, then:

```bash
./deploy.sh             # build + push only (regular update flow)
./deploy.sh --route     # one-time: also apply fabric destination + routing-domain
```

`--route` is required on the very first deploy to expose the service to the ISP; once applied it doesn't need to run again. Initial build takes 10–15 min; subsequent builds 2–3 min.

When `SNOWFLAKE_PRIVATE_KEY` is present, `snowflake_lookup.py` uses key-pair auth automatically. When it's absent (local dev), it falls back to `externalbrowser` SSO.

### Logs

```bash
# Build logs (during deploy):
kubectl --context gizmo.us1.staging.dog -n kiss-app-build logs -f -l app=build-is-scoping -c kaniko

# Service logs (once running):
kubectl --context gizmo.us1.staging.dog -n kiss-app-build logs -f -l app=is-scoping -c is-scoping
```

## Status

v1 local dev: working. Deploy to Howler: pending Snowflake service user (in flight via DNAINT).
