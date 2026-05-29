#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

echo "==> Coldcraft setup"

OS_NAME=""
case "$(uname -s)" in
  Darwin) OS_NAME="macos" ;;
  Linux) OS_NAME="linux" ;;
  *)
    echo "Unsupported OS. This script supports macOS and Linux."
    exit 1
    ;;
esac

run_with_privilege() {
  if command_exists sudo; then
    sudo "$@"
  else
    "$@"
  fi
}

install_python_macos() {
  echo "==> Checking Homebrew"
  if ! command_exists brew; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [[ -x /opt/homebrew/bin/brew ]]; then
      eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -x /usr/local/bin/brew ]]; then
      eval "$(/usr/local/bin/brew shellenv)"
    fi
  fi

  if ! command_exists python3; then
    echo "==> Installing Python via Homebrew"
    brew install python@3.11
  fi
}

install_python_linux() {
  if command_exists python3; then
    return 0
  fi

  if command_exists apt-get; then
    echo "==> Installing Python via apt-get"
    run_with_privilege apt-get update
    run_with_privilege apt-get install -y python3 python3-venv python3-pip
  elif command_exists dnf; then
    echo "==> Installing Python via dnf"
    run_with_privilege dnf install -y python3 python3-pip
  elif command_exists yum; then
    echo "==> Installing Python via yum"
    run_with_privilege yum install -y python3 python3-pip
  elif command_exists pacman; then
    echo "==> Installing Python via pacman"
    run_with_privilege pacman -S --noconfirm python python-pip
  else
    echo "No supported package manager found. Install Python 3 and pip manually."
    exit 1
  fi
}

if [[ "$OS_NAME" == "macos" ]]; then
  install_python_macos
else
  install_python_linux
fi

echo "==> Creating virtual environment"
PYTHON_BIN=""
if command_exists python3.11; then
  PYTHON_BIN="python3.11"
else
  PYTHON_BIN="python3"
fi

if ! "$PYTHON_BIN" -m venv .venv; then
  if [[ "$OS_NAME" == "linux" ]] && command_exists apt-get; then
    echo "==> Installing python3-venv via apt-get"
    run_with_privilege apt-get install -y python3-venv
    "$PYTHON_BIN" -m venv .venv
  else
    echo "Failed to create virtual environment. Ensure venv is installed."
    exit 1
  fi
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if command_exists playwright; then
  echo "==> Installing Playwright Chromium"
  if [[ "$OS_NAME" == "linux" ]]; then
    playwright install --with-deps chromium
  else
    playwright install chromium
  fi
else
  echo "==> Installing Playwright Chromium via python -m playwright"
  if [[ "$OS_NAME" == "linux" ]]; then
    python -m playwright install --with-deps chromium
  else
    python -m playwright install chromium
  fi
fi

if [[ -f .env.example && ! -f .env ]]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
fi

echo "==> Setup complete"
