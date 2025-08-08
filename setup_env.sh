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

# 0. Ensure Python3 with version 3.11-3.12
if ! command -v $PYTHON_BIN &>/dev/null; then
  echo -e "${RED}[ERROR] No suitable Python found. Make sure Python Version 3.11-3.12${RESET}" >&2
  exit 1
fi

# Get Python version
PYTHON_VERSION=$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${BLUE}[INFO] Found Python version: $PYTHON_VERSION${RESET}"

# Check if Python version is in acceptable range (3.11-3.12)
if ! [[ "$PYTHON_VERSION" =~ ^3\.1[12]$ ]]; then
  echo -e "${RED}[ERROR] Python version $PYTHON_VERSION is not supported. Required version: 3.11-3.12${RESET}" >&2
  
  # Check if pyenv is available
  if ! command -v pyenv &>/dev/null; then
    echo -e "${RED}[ERROR] pyenv not found. Please install pyenv first:${RESET}" >&2
    echo -e "${RED}  curl https://pyenv.run | bash${RESET}" >&2
    echo -e "${RED}  Then restart your shell and run this script again${RESET}" >&2
    exit 1
  fi
  
  echo -e "${BLUE}[INFO] Installing Python 3.12.2 using pyenv...${RESET}"
  if ! pyenv install 3.12.2; then
    echo -e "${RED}[ERROR] Failed to install Python 3.12.2 using pyenv${RESET}" >&2
    exit 1
  fi
  
  echo -e "${BLUE}[INFO] Setting Python 3.12.2 as local version...${RESET}"
  pyenv local 3.12.2
  PYTHON_BIN="python3.12"
  
  # Verify the installation
  PYTHON_VERSION=$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  echo -e "${GREEN}[INFO] Now using Python version: $PYTHON_VERSION${RESET}"
fi

# 1. Create New venv with correct Python version
if [[ ! -d "$VENV_DIR" ]]; then
  echo -e "${BLUE}[INFO] New virtual environment: $VENV_DIR with Python $PYTHON_VERSION${RESET}"
  $PYTHON_BIN -m venv "$VENV_DIR"
else
  echo -e "${BLUE}[INFO] Virtual environment already exists: $VENV_DIR${RESET}"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate" 2>/dev/null || \
source "$VENV_DIR/Scripts/activate"  # Windows (Git-bash / PowerShell)

# Verify Python version in virtual environment
VENV_PYTHON_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${BLUE}[INFO] Virtual environment Python version: $VENV_PYTHON_VERSION${RESET}"

# Double-check that the virtual environment is using the correct Python version
if ! [[ "$VENV_PYTHON_VERSION" =~ ^3\.1[12]$ ]]; then
  echo -e "${RED}[ERROR] Virtual environment is using Python $VENV_PYTHON_VERSION, but 3.11-3.12 is required${RESET}" >&2
  echo -e "${RED}[ERROR] Please remove the existing virtual environment and run this script again:${RESET}" >&2
  echo -e "${RED}  rm -rf $VENV_DIR${RESET}" >&2
  exit 1
fi

# 2. Upgrade pip / wheel / setuptools 
python -m pip install --upgrade pip wheel setuptools --quiet

# 3. Install or Upgrade dependencies 
if [[ "${1:-""}" == "--update" ]]; then
  echo -e "${BLUE}[INFO] Upgrade requirements.txt to new version${RESET}"
  pip install --upgrade -r "$REQ_FILE"
else
  echo -e "${BLUE}[INFO] Install dependencies${RESET}"
  pip install -r "$REQ_FILE"
fi

# 4. Dependency integrity check 
echo -e "${BLUE}[INFO] Package conflict check ...${RESET}"
pip check

# 5. List Obsolete Packages 
echo -e "${BLUE}[INFO] The following packages have updated versions (for reference only, not errors):${RESET}"
pip list --outdated || true

echo -e "\n${GREEN}[OK] All right.  you can activate the environment using${RESET} \n source $VENV_DIR/bin/activate"
