#!/usr/bin/env bash
# Thin wrapper around scripts/setup_test_db.py so folks can use either
# entry point. See the Python script docstring for options.
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run python scripts/setup_test_db.py "$@"
