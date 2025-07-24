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

REQ_FILE="requirements.txt"
VENV_DIR=".venv"
PYTHON_BIN="python3"

# ---------- 0. Ensure Python3 ----------
if ! command -v $PYTHON_BIN &>/dev/null; then
  echo "[ERROR] No suitble Python found. Make sure Python Version ≥3.10" >&2
  exit 1
fi

# ---------- 1. Create New venv ----------
if [[ ! -d "$VENV_DIR" ]]; then
  echo "[INFO] New virtual environment: $VENV_DIR"
  $PYTHON_BIN -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate" 2>/dev/null || \
source "$VENV_DIR/Scripts/activate"  # Windows (Git‑bash / PowerShell)

echo "[INFO] Python Version: $(python -V)"

# ---------- 2. Upgrade pip / wheel / setuptools ----------
python -m pip install --upgrade pip wheel setuptools --quiet

# ---------- 3. Install or Upgrade dependences ----------
if [[ "${1:-""}" == "--update" ]]; then
  echo "[INFO] Updgrade requirements.txt to new version"
  pip install --upgrade -r "$REQ_FILE"
else
  echo "[INFO] Install dependences"
  pip install -r "$REQ_FILE"
fi

# ---------- 4. Install spaCy  ----------
python -m spacy validate | grep -q "en_core_web_sm.*OK" || {
  echo "[INFO] Download spaCy en_core_web_sm ..."
  python -m spacy download en_core_web_sm
}

# ---------- 5. Dependency integrity check ----------
echo "[INFO] 运行 pip check ..."
pip check

# ---------- 6. List Obsolete Packages ----------
echo "[INFO] The following packages have updated versions (for reference only, not errors):"
pip list --outdated || true

echo -e "\n[OK] All right. Now you can activate the environment using \n  source $VENV_DIR/bin/activate\n"
