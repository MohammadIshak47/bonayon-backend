#!/usr/bin/env bash
# Render build step: install dependencies, migrate the Neon database, seed reference data.
set -o errexit
pip install -r requirements.txt
alembic upgrade head
python -m scripts.release
