#!/bin/bash
set -e

REMOTE_DIR="/home/pi/potify"
PYTHON_VERSION="3.11.9"

echo "==> Opravuji apt sources (přidávám archive.debian.org pro Buster)..."
# Odstraň nefunkční raspbian repo
sudo sed -i 's|^deb http://raspbian.raspberrypi.org|# deb http://raspbian.raspberrypi.org|g' /etc/apt/sources.list
# Odstraň případné staré záznamy archive.debian.org
sudo sed -i '/archive.debian.org/d' /etc/apt/sources.list

# Přidej archivovaný Debian Buster s [trusted=yes]
echo "deb [trusted=yes] http://archive.debian.org/debian buster main contrib non-free" | sudo tee -a /etc/apt/sources.list
echo "deb [trusted=yes] http://archive.debian.org/debian-security buster/updates main contrib non-free" | sudo tee -a /etc/apt/sources.list

echo "==> Přidávám chybějící GPG klíče..."
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys \
    648ACFD622F3D138 0E98404D386FA1D9 DCC9EFBF77E11517 112695A0E562B32A 54404762BBB6E853 || true

echo "==> Aktualizuji apt cache..."
sudo apt-get update -o Acquire::Check-Valid-Until=false 2>&1 | grep -v "^W:" || true

echo "==> Instaluji build závislosti pro Python..."
sudo apt-get install -y --no-install-recommends --allow-unauthenticated \
    git curl build-essential \
    libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev libffi-dev \
    xz-utils

echo "==> Instaluji pyenv (pokud ještě není)..."
if [ ! -d "$HOME/.pyenv" ]; then
    curl -fsSL https://pyenv.run | bash
fi

export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

echo "==> Instaluji Python $PYTHON_VERSION (může trvat 15-30 minut na RPi3)..."
pyenv install -s $PYTHON_VERSION
pyenv global $PYTHON_VERSION

echo "==> Python verze: $(python --version)"

echo "==> Vytvářím venv v $REMOTE_DIR..."
cd "$REMOTE_DIR"
rm -rf .venv
python -m venv .venv

echo "==> Instaluji Python závislosti..."
.venv/bin/pip install --upgrade pip
# Instalace numpy/trimesh odděleně kvůli kompatibilitě s GLIBC na Raspbian Buster.
.venv/bin/pip install --extra-index-url https://www.piwheels.org/simple --only-binary :all: "numpy==1.23.5" || \
    .venv/bin/pip install --no-binary numpy "numpy==1.23.5"
.venv/bin/pip install --extra-index-url https://www.piwheels.org/simple --only-binary :all: "trimesh==3.23.5"
.venv/bin/pip install -e . --no-deps
.venv/bin/pip install --extra-index-url https://www.piwheels.org/simple lxml networkx flask Pillow

echo "==> Nastavuji systemd service..."
sudo cp "$REMOTE_DIR/potify.service" /etc/systemd/system/potify.service
sudo systemctl daemon-reload
sudo systemctl enable potify
sudo systemctl restart potify

echo ""
echo "==> Hotovo! Stav service:"
sudo systemctl status potify --no-pager

echo ""
echo "==> Aplikace beží na http://$(hostname -I | awk '{print $1}'):50555"
