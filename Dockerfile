FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# daemontools provides `envdir` — the Howler secret pattern.
# Howler writes encrypted secrets to /etc/datadog/secrets and `envdir` loads them as env vars.
RUN apt-get update \
 && apt-get install -y --no-install-recommends daemontools ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv \
 && uv sync --no-dev --frozen

COPY methodologies.py scoping_doc.py snowflake_lookup.py streamlit_app.py ./

EXPOSE 8000

# Howler's fabric routing-domain config points the public domain at the
# Kubernetes service on port 8000, so the container must listen there.
# `envdir` loads the secrets mounted at /etc/datadog/secrets as env vars before
# launching streamlit. When running locally outside Howler, secrets are read
# from the environment directly.
CMD ["sh", "-c", "if [ -d /etc/datadog/secrets ]; then exec envdir /etc/datadog/secrets uv run streamlit run streamlit_app.py --server.port=8000 --server.address=0.0.0.0 --server.headless=true; else exec uv run streamlit run streamlit_app.py --server.port=8000 --server.address=0.0.0.0 --server.headless=true; fi"]
