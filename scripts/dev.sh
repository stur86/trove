#!/usr/bin/env bash
# Run backend and frontend dev servers together.
# Ctrl+C kills both.
set -e
trap 'kill 0' EXIT

echo "Backend  → http://localhost:8001"
echo "Frontend → http://localhost:5173"
echo ""

uvicorn backend.main:app --reload --port 8001 &
cd frontend && bun run dev
