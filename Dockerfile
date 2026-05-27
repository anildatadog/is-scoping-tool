# Cloud Run target: public Python image, standard apt + PyPI access (no
# Datadog-internal registry needed — GCP Cloud Build can reach Docker Hub +
# pypi.org freely).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./
# Cache-bust marker (bump when deps change so Cloud Build doesn't reuse a stale layer):
# 2026-05-27 slice-2-anthropic
RUN pip install --no-cache-dir --upgrade -r requirements.txt \
 && python -c "import authlib; print('authlib', authlib.__version__)" \
 && python -c "from authlib.integrations.starlette_client import OAuth; print('starlette_client OAuth import OK')" \
 && python -c "import streamlit; print('streamlit', streamlit.__version__)" \
 && python -c "import streamlit.web.server.starlette.starlette_auth_routes as m; print('streamlit auth routes import OK')" \
 && python -c "import anthropic; print('anthropic', anthropic.__version__)"

COPY diagnosis.py methodologies.py prose.py scoping_doc.py snowflake_lookup.py streamlit_app.py docker-entrypoint.sh ./
COPY pages/ ./pages/
RUN chmod +x docker-entrypoint.sh

# Cloud Run injects $PORT (default 8080). The entrypoint generates
# .streamlit/secrets.toml from env vars (OAuth client, cookie secret) before
# launching Streamlit so st.login() works.
EXPOSE 8080

ENTRYPOINT ["/app/docker-entrypoint.sh"]
