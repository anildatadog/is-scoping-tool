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

Note: the app guards every screen behind `st.login()` with Google OAuth (`hd=datadoghq.com`). Local runs therefore need either a `.streamlit/secrets.toml` with a Google OAuth client, or you temporarily comment out the auth block at the top of `streamlit_app.py`.

## Project structure

```
streamlit_app.py        # UI: search, questionnaire, review, result
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
- `streamlit_app.py` re-checks `st.user.email` server-side after sign-in (defense in depth).

Same pattern as `splunk-dd-migration-mcp`.

### Snowflake auth (runtime)

In the container, Snowflake auth uses a programmatic access token (PAT):

- `authenticator=PROGRAMMATIC_ACCESS_TOKEN` with `token=<pat>` (not `password=<pat>`).
- `user=` must be the **email login form** (e.g. `ANILKUMAR.PAPPU@DATADOGHQ.COM`), not the user-object name.
- The PAT has network-policy bypass enabled in Snowsight. This is alpha-grade; v2 needs a real `NETWORK_POLICY` on the user.

Locally, `snowflake_lookup.py` falls back to `externalbrowser` SSO when no PAT / private-key env is present.

The DNAINT-tracked Snowflake service user (key-pair auth) is **no longer required** — the PAT path replaces it.

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

- **v1 deployed and AE-usable** on Cloud Run.
- **`deploy.sh` is stale** (Howler-only). Rewrite as a Cloud Run script when next touched.
- **v2 output redesign locked but not implemented** — replaces the 9-methodology selector with a structured diagnosis (shape / posture / dominant constraint / customer ownership / consequence / commercial footer).
