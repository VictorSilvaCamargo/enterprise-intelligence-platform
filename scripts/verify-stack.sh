#!/usr/bin/env bash
set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

if [[ -f ".env" ]]; then
  while IFS='=' read -r key value; do
    case "$key" in
      BACKEND_PORT) BACKEND_PORT="${value:-$BACKEND_PORT}" ;;
      FRONTEND_PORT) FRONTEND_PORT="${value:-$FRONTEND_PORT}" ;;
    esac
  done < <(grep -E '^(BACKEND_PORT|FRONTEND_PORT)=' .env || true)
fi

echo "==> Checking Docker Compose service status..."
docker compose ps

echo "==> Verifying backend liveness: http://localhost:${BACKEND_PORT}/health"
curl --fail --silent --show-error "http://localhost:${BACKEND_PORT}/health" | grep -q '"status":"ok"'
echo "    OK: /health returned status=ok"

echo "==> Verifying backend readiness: http://localhost:${BACKEND_PORT}/health/ready"
READINESS_JSON="$(curl --fail --silent --show-error "http://localhost:${BACKEND_PORT}/health/ready")"
echo "$READINESS_JSON" | grep -q '"status":"ready"'
echo "$READINESS_JSON" | grep -q '"postgresql":{"status":"up"'
echo "$READINESS_JSON" | grep -q '"redis":{"status":"up"'
echo "    OK: /health/ready confirmed postgresql=up and redis=up"

echo "==> Verifying OpenAPI specification: http://localhost:${BACKEND_PORT}/openapi.json"
curl --fail --silent --show-error "http://localhost:${BACKEND_PORT}/openapi.json" | grep -q '"/health/ready"'
echo "    OK: OpenAPI schema exposes /health and /health/ready"

echo "==> Verifying frontend HTTP response: http://localhost:${FRONTEND_PORT}/"
HTTP_CODE="$(curl --silent --output /dev/null --write-out '%{http_code}' "http://localhost:${FRONTEND_PORT}/")"
if [[ "$HTTP_CODE" != "200" ]]; then
  echo "Frontend returned HTTP $HTTP_CODE" >&2
  exit 1
fi
echo "    OK: Frontend returned HTTP 200"

echo "All Stage 1 stack checks passed."
