#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "=== djafatt — restart ==="

# Rebuild web if Dockerfile/deps changed
if [[ "${1:-}" == "--build" ]]; then
    echo "→ Rebuilding web image..."
    docker compose build web
fi

# Stop everything
echo "→ Stopping containers..."
docker compose down

# Install node_modules if missing
if [[ ! -d node_modules ]]; then
    echo "→ Installing node_modules..."
    docker compose run --rm node npm install
fi

# Start all services
echo "→ Starting db, redis, web, node..."
docker compose up -d

# Wait for db
echo "→ Waiting for PostgreSQL..."
until docker compose exec -T db pg_isready -U djafatt -q 2>/dev/null; do
    sleep 1
done

# Migrations
echo "→ Running migrations..."
docker compose exec -T web python manage.py migrate --noinput

# Build frontend assets
echo "→ Building Vite assets..."
docker compose exec -T node npx vite build

# Collect static files (clear stale assets first)
echo "→ Collecting static files..."
docker compose exec -T web rm -rf /app/staticfiles/assets/
docker compose exec -T web python manage.py collectstatic --noinput

echo ""
echo "✓ djafatt running:"
echo "  Web:  http://localhost:${APP_PORT:-8000}"
echo "  Vite: http://localhost:5173"
echo ""
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
