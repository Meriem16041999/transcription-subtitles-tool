#!/usr/bin/env bash
set -e
source .venv/bin/activate
export WHISPER_MODEL=${WHISPER_MODEL:-small}
export DEVICE=${DEVICE:-cpu}
export COMPUTE_TYPE=${COMPUTE_TYPE:-int8}
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
