#!/usr/bin/env bash
set -e
cd frontend
export VITE_API_URL=${VITE_API_URL:-http://localhost:8000}
npm run dev
