#!/usr/bin/env bash
# Start local dev environment:
#   Backend: FastAPI on http://localhost:8000 (auth disabled, Snowflake wired)
#   Frontend: Vite HMR on http://localhost:3000 (auth bypassed via VITE_DEV_BYPASS_AUTH)
#
# Usage: ./dev.sh
# Stop:  Ctrl-C (stops Vite), then docker compose down

set -e

# Start backend in Docker (reads creds from .env.local)
echo "Starting backend..."
docker compose --env-file .env.local up --build -d

echo "Backend running at http://localhost:8000"
echo "Health check: http://localhost:8000/health"
echo ""

# Start frontend dev server (hot reload)
echo "Starting frontend (http://localhost:3000)..."
cd frontend && npm run dev
