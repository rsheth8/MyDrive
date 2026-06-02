#!/usr/bin/env bash
# Build demo CSVs + model only.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"
mydrive_prepare_python
mydrive_cd
"$(mydrive_python)" scripts/generate_sample_data.py
"$(mydrive_python)" scripts/setup_demo_data.py
echo ""
echo "Demo ready."
echo "  ./scripts/dev.sh mobile"
echo "  ./scripts/dev.sh desktop"
