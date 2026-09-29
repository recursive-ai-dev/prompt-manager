#!/usr/bin/env bash
set -euo pipefail

# Usage: ./launch.sh [prompt-manager arguments]
# Setup: python3 -m venv .venv && .venv/bin/python -m pip install -e .
# Set PYTHON to override the interpreter (for example, PYTHON=python3.13).
REPO_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ -n "${PYTHON:-}" ]]; then
    PYTHON_BIN="${PYTHON}"
elif [[ -x "${REPO_DIR}/.venv/bin/python" ]]; then
    PYTHON_BIN="${REPO_DIR}/.venv/bin/python"
else
    PYTHON_BIN="python3"
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    printf 'Error: Python interpreter not found: %s\n' "${PYTHON_BIN}" >&2
    printf 'Install Python 3.10+ or set PYTHON to its executable path.\n' >&2
    exit 1
fi

# Keep the caller's directory so relative file arguments work as supplied.
export PYTHONPATH="${REPO_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
exec "${PYTHON_BIN}" -m prompt_manager.app "$@"
