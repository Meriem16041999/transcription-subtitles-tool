#!/usr/bin/env bash
set -e

echo "==> Verification de Python"
python3 --version

echo "==> Creation de l'environnement virtuel"
python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r backend/requirements.txt

echo "==> Installation des dependances frontend"
cd frontend
npm install
cd ..

echo "==> Termine"
echo "Lance ensuite: ./run_backend.sh puis ./run_frontend.sh dans un autre terminal"
