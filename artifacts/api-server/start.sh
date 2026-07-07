#!/usr/bin/env bash
# Launcher for the Python FastAPI backend.
# This script lives inside artifacts/api-server/ so the managed workflow can
# find it. It navigates two levels up to the workspace root where
# python-backend/ lives, then delegates to the real start script.
set -e
WORKSPACE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec bash "$WORKSPACE_ROOT/python-backend/start.sh"
