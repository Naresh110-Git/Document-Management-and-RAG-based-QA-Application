#!/usr/bin/env bash
# Run backend tests with backend on PYTHONPATH
set -euo pipefail
basedir="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$basedir"
python3 -m pytest "$@"
