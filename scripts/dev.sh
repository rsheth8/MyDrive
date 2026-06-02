#!/usr/bin/env bash
# MyDrive — one entry point for local development.
#
#   ./scripts/dev.sh setup     # once: venv, pip, demo data, npm
#   ./scripts/dev.sh mobile    # API + phone PWA  → http://localhost:8000
#   ./scripts/dev.sh desktop   # Streamlit dashboard
#   ./scripts/dev.sh expo      # Expo Go (API should be running)
#   ./scripts/dev.sh check     # quick health check
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

CMD="${1:-help}"

cmd_setup() {
  mydrive_print_banner
  mydrive_cd
  echo "→ Creating Python virtualenv…"
  if [[ ! -d .venv ]]; then
    python3 -m venv .venv
  fi
  mydrive_prepare_python
  echo "→ Installing Python packages…"
  pip install -q -r requirements.txt
  echo "→ Building demo data…"
  python scripts/generate_sample_data.py
  python scripts/setup_demo_data.py
  echo "→ Installing Expo dependencies…"
  mydrive_ensure_expo_assets
  cd mobile-native
  npm install
  npx expo install --fix 2>/dev/null || true
  cd "$MYDRIVE_ROOT"
  echo ""
  echo "✓ Setup complete. Next:"
  echo "    ./scripts/dev.sh mobile    # terminal 1"
  echo "    ./scripts/dev.sh expo      # terminal 2 (optional)"
  echo "    ./scripts/dev.sh desktop   # or Streamlit on laptop"
}

cmd_mobile() {
  mydrive_print_banner
  mydrive_ensure_venv
  mydrive_prepare_python
  mydrive_ensure_demo
  LAN="$(mydrive_lan_ip)"
  echo "→ API + PWA"
  echo "    Computer:  http://localhost:8000"
  echo "    Phone:     http://${LAN}:8000  (same Wi‑Fi)"
  echo ""
  echo "  Press Ctrl+C to stop."
  echo ""
  exec "$(mydrive_python)" -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
}

cmd_desktop() {
  mydrive_print_banner
  mydrive_ensure_venv
  mydrive_prepare_python
  mydrive_ensure_demo
  echo "→ Streamlit desktop UI"
  echo "    http://localhost:8501"
  echo ""
  exec "$(mydrive_python)" -m streamlit run streamlit_app.py
}

cmd_expo() {
  mydrive_print_banner
  mydrive_ensure_expo_assets

  if ! mydrive_api_running; then
    echo "⚠ API is not running on port 8000."
    echo "  Start it first (another terminal):  ./scripts/dev.sh mobile"
    if [[ -t 0 ]]; then
      echo ""
      read -r -p "Continue anyway? [y/N] " ans
      [[ "${ans:-}" =~ ^[yY] ]] || exit 1
    else
      echo "  (non-interactive — continuing)"
    fi
  fi

  LAN="$(mydrive_lan_ip)"
  export EXPO_PUBLIC_API_URL="${EXPO_PUBLIC_API_URL:-http://${LAN}:8000}"
  # Expo Go only — no EAS login required for QR scan
  export EXPO_NO_TELEMETRY=1
  export CI=1

  echo "→ Expo Go"
  echo "    API:     ${EXPO_PUBLIC_API_URL}"
  echo "    Phone:   Install Expo Go → scan QR in terminal"
  echo "    Simulator: open Expo Go app manually; do not press 'i' (may ask for login)"
  echo ""
  cd "$MYDRIVE_ROOT/mobile-native"
  if [[ ! -d node_modules ]]; then
    echo "→ Installing npm packages…"
    npm install
  fi
  exec npx expo start --go "$@"
}

cmd_check() {
  mydrive_cd
  echo "MyDrive check"
  echo "─────────────"
  if [[ -x .venv/bin/python ]]; then
    echo "✓ Python venv"
  else
    echo "✗ Python venv missing — run: ./scripts/dev.sh setup"
  fi
  if [[ -f data/processed/fused.csv ]]; then
    echo "✓ Demo data"
  else
    echo "✗ Demo data missing — run: ./scripts/dev.sh setup"
  fi
  if mydrive_api_running; then
    echo "✓ API http://localhost:8000"
  else
    echo "○ API not running — run: ./scripts/dev.sh mobile"
  fi
  if [[ -d mobile-native/node_modules ]]; then
    echo "✓ Expo node_modules"
  else
    echo "○ Expo deps missing — run: ./scripts/dev.sh setup"
  fi
  if [[ -d mobile-native/assets/images ]]; then
    echo "✓ Expo assets folder"
  else
    echo "✗ Expo assets missing — run: ./scripts/dev.sh setup"
  fi
  if [[ -x .venv/bin/python ]]; then
    mydrive_prepare_python
    if ./scripts/verify.sh >/dev/null 2>&1; then
      echo "✓ Python imports"
    else
      echo "✗ Python verify failed — run: ./scripts/verify.sh"
    fi
  fi
}

cmd_help() {
  mydrive_print_banner
  cat <<'EOF'
Usage:  ./scripts/dev.sh <command>

  setup     One-time install (venv, pip, demo data, npm)
  mobile    API + PWA on :8000  ← start this first
  expo      Expo Go app (scan QR; needs API)
  desktop   Streamlit on :8501
  check     See what's installed / running
  help      This message

Typical flow:
  1. ./scripts/dev.sh setup
  2. ./scripts/dev.sh mobile     # leave running
  3. ./scripts/dev.sh expo       # optional; scan QR with Expo Go

PWA only (no Expo): step 2 is enough — open http://localhost:8000
EOF
}

case "$CMD" in
  setup) cmd_setup ;;
  mobile|web|api) cmd_mobile ;;
  desktop|streamlit) cmd_desktop ;;
  expo|native) cmd_expo "${@:2}" ;;
  check|status) cmd_check ;;
  help|-h|--help) cmd_help ;;
  *)
    echo "Unknown command: $CMD"
    cmd_help
    exit 1
    ;;
esac
