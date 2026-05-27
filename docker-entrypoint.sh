#!/bin/sh
# Cloud Run entrypoint:
#   1. Build .streamlit/secrets.toml from env vars so Streamlit's native auth
#      (st.login) finds its OAuth client + cookie config at the standard path.
#   2. exec streamlit on $PORT (Cloud Run sets PORT, defaults to 8080).
#
# The OAuth client is reused from splunk-dd-google-client-* secrets in
# Secret Manager (datadog-tam-sandbox), mounted as env vars by the Cloud Run
# --set-secrets flag at deploy time. hd=datadoghq.com restricts the Google
# sign-in screen to the Datadog Workspace; the app also re-checks the email
# domain server-side in streamlit_app.py.
set -eu

mkdir -p /app/.streamlit

# Strip trailing newlines/whitespace from secret env vars. Cloud Run mounts
# Secret Manager values verbatim, so any trailing newline (e.g. from a `print()`
# during secret creation) ends up inside the env var and corrupts the TOML
# we generate below.
trim_trailing() { printf '%s' "$1" | sed -e 's/[[:space:]]*$//'; }
OAUTH_REDIRECT_URI=$(trim_trailing "${OAUTH_REDIRECT_URI:-}")
COOKIE_SECRET=$(trim_trailing "${COOKIE_SECRET:-}")
GOOGLE_CLIENT_ID=$(trim_trailing "${GOOGLE_CLIENT_ID:-}")
GOOGLE_CLIENT_SECRET=$(trim_trailing "${GOOGLE_CLIENT_SECRET:-}")

cat > /app/.streamlit/secrets.toml <<EOF
[auth]
redirect_uri = "${OAUTH_REDIRECT_URI}"
cookie_secret = "${COOKIE_SECRET}"

[auth.google]
client_id = "${GOOGLE_CLIENT_ID}"
client_secret = "${GOOGLE_CLIENT_SECRET}"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
client_kwargs = { prompt = "select_account", hd = "datadoghq.com" }
EOF

# Debug: confirm env vars arrived and TOML got written. Mask all values longer
# than 3 chars so secret contents never reach the log.
echo "[entrypoint] env presence:"
for v in OAUTH_REDIRECT_URI COOKIE_SECRET GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET ANTHROPIC_API_KEY PORT; do
  val=$(eval echo \$$v 2>/dev/null || true)
  if [ -n "$val" ]; then
    echo "  $v: set (len=${#val})"
  else
    echo "  $v: MISSING"
  fi
done
echo "[entrypoint] secrets.toml (values masked):"
sed 's/"[^"]\{4,\}"/"****"/g' /app/.streamlit/secrets.toml | sed 's/^/  /'

exec streamlit run Scope_an_opportunity.py \
  --server.port="${PORT:-8080}" \
  --server.address=0.0.0.0 \
  --server.headless=true
