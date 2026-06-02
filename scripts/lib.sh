#!/usr/bin/env bash
# Shared helpers for MyDrive scripts. Source from other scripts: source "$(dirname "$0")/lib.sh"

MYDRIVE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

mydrive_cd() {
  cd "$MYDRIVE_ROOT"
}

mydrive_python() {
  mydrive_cd
  if [[ -x "$MYDRIVE_ROOT/.venv/bin/python" ]]; then
    echo "$MYDRIVE_ROOT/.venv/bin/python"
  else
    command -v python3
  fi
}

mydrive_prepare_python() {
  mydrive_cd
  export PYTHONPATH="$MYDRIVE_ROOT${PYTHONPATH:+:$PYTHONPATH}"
  if [[ -f "$MYDRIVE_ROOT/.venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "$MYDRIVE_ROOT/.venv/bin/activate"
  fi
}

mydrive_lan_ip() {
  ipconfig getifaddr en0 2>/dev/null \
    || ipconfig getifaddr en1 2>/dev/null \
    || hostname -I 2>/dev/null | awk '{print $1}' \
    || echo "127.0.0.1"
}

mydrive_ensure_demo() {
  mydrive_cd
  if [[ ! -f data/processed/fused.csv ]]; then
    echo "→ First run: building demo data…"
    "$(mydrive_python)" scripts/generate_sample_data.py
    "$(mydrive_python)" scripts/setup_demo_data.py
  fi
}

mydrive_ensure_venv() {
  mydrive_cd
  if [[ ! -x .venv/bin/python ]]; then
    echo "✗ No virtualenv at .venv"
    echo "  Run once:  ./scripts/dev.sh setup"
    exit 1
  fi
}

mydrive_api_running() {
  curl -sf --max-time 2 "http://127.0.0.1:8000/api/health" >/dev/null 2>&1
}

mydrive_ensure_expo_assets() {
  mkdir -p "$MYDRIVE_ROOT/mobile-native/assets/images"
}

mydrive_print_banner() {
  echo ""
  echo "  MyDrive — your drive, your way"
  echo "  ─────────────────────────────"
  echo ""
}
