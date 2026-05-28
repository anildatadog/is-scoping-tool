# IS Scoping Tool

AE-facing scoping tool for sizing Datadog Implementation Services engagements.

Walks an AE through 11 business-language questions about a customer opportunity, pre-filled from Salesforce data where possible, and returns a recommended IS methodology with a session estimate and pre-close checklist.

## Local development

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env
uv run streamlit run Scope_an_opportunity.py
```

First Snowflake query opens a browser for Datadog SSO. Subsequent queries reuse the cached token.

Note: the app guards every screen behind `st.login()` with Google OAuth (`hd=datadoghq.com`). Local runs therefore need either a `.streamlit/secrets.toml` with a Google OAuth client, or you temporarily comment out the auth block at the top of `Scope_an_opportunity.py`.

## Project structure

```
Scope_an_opportunity.py        # UI: search, questionnaire, review, result
snowflake_lookup.py     # Snowflake connection + lookup + field mapper
methodologies.py        # QUESTIONS, METHODS, recommend, flags, next steps
scoping_doc.py          # Copy-paste summary formatter
Dockerfile              # Cloud Run container image
docker-entrypoint.sh    # Writes .streamlit/secrets.toml from env vars, exec's streamlit
```

## Reference

- Handover doc: [IS Scoping Tool, Claude Code Handover](https://docs.google.com/document/d/1wh13MJalmtK7DrlLyUCW5aM4VEJtQbG0p0pxyXUgJ2U)
- Snowflake query patterns: `dd-governed-onboarding-mcp/.claude/commands/is-salesforce-lookup.md`

## Deployment

Runs on Cloud Run in `datadog-tam-sandbox`, region `us-central1`. Howler was the original target but its `kiss-app-build` cluster blocks egress to `*.snowflakecomputing.com` (same Cilium policy that blocks Docker Hub and apt during builds), so the app was moved to Cloud Run where egress is unrestricted.

### Auth

- Cloud Run service is `--allow-unauthenticated` (so the OAuth dance can happen).
- Streamlit's native `st.login()` runs the Google OAuth flow with `hd=datadoghq.com`, which restricts the Google sign-in screen to the Datadog Workspace.
- `Scope_an_opportunity.py` re-checks `st.user.email` server-side after sign-in (defense in depth).

Same pattern as `splunk-dd-migration-mcp`.

### Snowflake auth (runtime)

In the container, Snowflake auth uses a programmatic access token (PAT):

- `authenticator=PROGRAMMATIC_ACCESS_TOKEN` with `token=<pat>` (not `password=<pat>`).
- `user=` must be the **email login form** (e.g. `IS_SCOPING_TOOL_USER@…` once the service user lands), not the user-object name.

Locally, `snowflake_lookup.py` falls back to `externalbrowser` SSO when no PAT / private-key env is present.

#### Network policy + service user (in flight, 2026-05-28)

The Snowflake side is being moved off Anil's personal user to a dedicated service user (`IS_SCOPING_TOOL_USER`) with a 1-year PAT and an IP-allowlist network policy. Tracking: [DNAINT-3266](https://datadoghq.atlassian.net/browse/DNAINT-3266) and [dd-analytics#73068](https://github.com/DataDog/dd-analytics/pull/73068).

Per [Datadog's Snowflake Access Control policy](https://datadoghq.atlassian.net/wiki/spaces/adp/pages/5289607973/Overview+Snowflake+Access+Control), a Cloud Run service serving multiple AEs is the "Shared Users — Service User" pattern, not individual SSO. The earlier personal-PAT + 24h bypass approach failed daily because Snowflake caps `MINS_TO_BYPASS_NETWORK_POLICY_REQUIREMENT` at 1440 minutes and the renewal SQL can't be run from a PAT-authenticated session.

Once the service user lands, swap the `SNOWFLAKE_USER` and `SNOWFLAKE_PAT` Secret Manager values and redeploy. No code change needed.

### Network egress (Cloud NAT)

Cloud Run egress is dynamic by default. Snowflake network policies need a stable source IP, so the service routes outbound traffic through a dedicated Cloud NAT pinned to a reserved external IP:

| Resource | Name | Value |
|---|---|---|
| Reserved external IP | `is-scoping-tool-egress-ip` | `35.192.132.11` |
| Cloud Router | `is-scoping-tool-router` | `us-central1` |
| Cloud NAT | `is-scoping-tool-nat` | bound to the reserved IP, `--nat-all-subnet-ip-ranges` |
| Serverless VPC Access connector | `is-scoping-tool-vpc` | `10.8.0.0/28`, `e2-micro`, 2–3 instances |

The Cloud Run service is attached via `--vpc-connector=is-scoping-tool-vpc --vpc-egress=all-traffic`. All outbound traffic from the container — Snowflake, Anthropic, anything — exits via `35.192.132.11`. Verified `2026-05-28` with a one-shot Cloud Run job hitting `ifconfig.me`.

Cost: ~$45/mo (Cloud NAT ~$32, VPC connector ~$10, reserved IP ~$3) plus minor egress data charges.

If the Cloud Run service is recreated, the VPC connector + egress flags must be re-applied explicitly. `gcloud run deploy --source .` preserves these across normal redeploys.

### Secrets

Stored in Secret Manager (`datadog-tam-sandbox`), mounted as env vars at deploy time via `gcloud run deploy --set-secrets`:

| Env var | Purpose |
|---|---|
| `OAUTH_REDIRECT_URI` | Public Cloud Run URL + `/oauth2callback` |
| `COOKIE_SECRET` | Streamlit session cookie signing key |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth client (reused from `splunk-dd-google-client-*`) |
| `SNOWFLAKE_USER` | Login email |
| `SNOWFLAKE_PAT` | Programmatic access token |
| `SNOWFLAKE_ACCOUNT` | `sza96462.us-east-1` |
| `SNOWFLAKE_DATABASE` | `REPORTING` |
| `SNOWFLAKE_WAREHOUSE` | `AD_HOC_DEVELOPMENT_XSMALL_WAREHOUSE` |

`docker-entrypoint.sh` reads these at container start, strips trailing whitespace (Secret Manager mounts can include newlines), and writes `/app/.streamlit/secrets.toml` before `exec streamlit`.

### Build + deploy

There is no committed Cloud Run deploy script yet — `deploy.sh` in this repo is the **stale Howler script** and should be ignored (kept only for git history; will be replaced). Deploys are currently driven by `gcloud builds submit` + `gcloud run deploy` invocations adapted from `splunk-dd-migration-mcp/deploy/deploy-web.sh`.

Container build cache: bump the `# Cache-bust marker` line in `Dockerfile` when deps change, otherwise Cloud Build can reuse a stale layer.

## Status

- **v1 deployed and AE-usable** on Cloud Run with static egress via Cloud NAT (`35.192.132.11`).
- **Snowflake service-user migration in flight** — `IS_SCOPING_TOOL_USER` via [dd-analytics#73068](https://github.com/DataDog/dd-analytics/pull/73068). 1-year PAT will replace the personal-PAT-as-Anil setup once ADP applies + issues. Swap `SNOWFLAKE_USER` / `SNOWFLAKE_PAT` secrets when it lands; no code change.
- **`deploy.sh` is stale** (Howler-only). Rewrite as a Cloud Run script when next touched.
- **v2 output redesign in progress** — diagnosis-led output (shape / motion / binding constraints / customer ownership / consequence) shipped 2026-05-27 across slices 1–3.9. `productScope` includes FinOps / Cloud Cost Management (CCM) as of 2026-05-28.
