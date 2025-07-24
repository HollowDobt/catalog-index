#!/usr/bin/env bash
# ------------------------------------------------------------------
# setup_env.sh
#   Automatically set the environment.
#
# Usage
#   ./setup_env.sh                # First to install
#   ./setup_env.sh --update       # Upgrade
# ------------------------------------------------------------------
set -euo pipefail

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RESET='\033[0m'

REQ_FILE="requirements.txt"
VENV_DIR=".venv"
PYTHON_BIN="python3"

# ---------- 0. Ensure Python3 ----------
if ! command -v $PYTHON_BIN &>/dev/null; then
  echo -e "${RED}[ERROR] No suitable Python found. Make sure Python Version ≥3.10${RESET}" >&2
  exit 1
fi

# ---------- 1. Create New venv ----------
if [[ ! -d "$VENV_DIR" ]]; then
  echo -e "${BLUE}[INFO] New virtual environment: $VENV_DIR${RESET}"
  $PYTHON_BIN -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate" 2>/dev/null || \
source "$VENV_DIR/Scripts/activate"  # Windows (Git-bash / PowerShell)

echo -e "${BLUE}[INFO] Python Version: $(python -V)${RESET}"

# ---------- 2. Upgrade pip / wheel / setuptools ----------
python -m pip install --upgrade pip wheel setuptools --quiet

# ---------- 3. Install or Upgrade dependencies ----------
if [[ "${1:-""}" == "--update" ]]; then
  echo -e "${BLUE}[INFO] Upgrade requirements.txt to new version${RESET}"
  pip install --upgrade -r "$REQ_FILE"
else
  echo -e "${BLUE}[INFO] Install dependencies${RESET}"
  pip install -r "$REQ_FILE"
fi

# ---------- 4. Install spaCy model ----------
python -m spacy validate | grep -q "en_core_web_sm.*OK" || {
  echo -e "${BLUE}[INFO] Download spaCy en_core_web_sm ...${RESET}"
  python -m spacy download en_core_web_sm
}

# ---------- 5. Dependency integrity check ----------
echo -e "${BLUE}[INFO] Package conflict check ...${RESET}"
pip check

# ---------- 6. List Obsolete Packages ----------
echo -e "${BLUE}[INFO] The following packages have updated versions (for reference only, not errors):${RESET}"
pip list --outdated || true

echo -e "\n${GREEN}[OK] All right.  you can activate the environment using${RESET} \n source $VENV_DIR/bin/activate"
