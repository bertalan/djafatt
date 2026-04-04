#!/usr/bin/env bash
# Deploy djafatt to fatt.betabi.it (bare metal, aaPanel server)
set -euo pipefail

REMOTE="guzzi-days.net"
APP_DIR="/www/wwwroot/fatt.betabi.it"
VENV="$APP_DIR/venv"

echo "=== djafatt deploy ==="

# 1. Push latest to GitHub
echo "→ Pushing to GitHub..."
git push origin main

# 2. Remote setup
echo "→ Remote deploy..."
ssh "$REMOTE" bash -s <<'EOF'
set -euo pipefail
APP_DIR="/www/wwwroot/fatt.betabi.it"
VENV="$APP_DIR/venv"

# Clone or pull
if [ ! -d "$APP_DIR/.git" ]; then
    echo "  Cloning repo..."
    git clone https://github.com/bertalan/djafatt.git "$APP_DIR"
else
    echo "  Pulling latest..."
    cd "$APP_DIR"
    git fetch origin
    git reset --hard origin/main
fi

cd "$APP_DIR"

# Create venv if needed
if [ ! -d "$VENV" ]; then
    echo "  Creating virtualenv..."
    python3 -m venv "$VENV"
fi

source "$VENV/bin/activate"

# Install deps
echo "  Installing Python deps..."
pip install --quiet --upgrade pip
pip install --quiet -e .

# Build frontend
echo "  Building frontend..."
if [ ! -d node_modules ]; then
    npm install --silent
fi
npx vite build

# Load env
set -a; source .env; set +a

# Migrate
echo "  Running migrations..."
python manage.py migrate --noinput

# Seed groups
python manage.py seed_groups 2>/dev/null || true

# Collectstatic
echo "  Collecting static files..."
python manage.py collectstatic --noinput --clear

# Restart services
echo "  Restarting services..."
sudo systemctl restart djafatt djafatt-celery 2>/dev/null || echo "  (services not yet created)"

echo "✓ Deploy complete"
EOF

echo "=== Done ==="
