#!/usr/bin/env bash
# Run every query in this folder against the data in ../1_data/.
# Requires DuckDB installed: https://duckdb.org/docs/installation/
#
#   ./run_all.sh
#
# To run a single query interactively:
#   duckdb < 02_domain_coverage.sql

set -euo pipefail

cd "$(dirname "$0")"

if ! command -v duckdb >/dev/null 2>&1; then
  echo "duckdb not found on PATH. Install: https://duckdb.org/docs/installation/" >&2
  exit 1
fi

for f in 0[1-8]_*.sql; do
  echo
  echo "============================================================"
  echo "Running: $f"
  echo "============================================================"
  duckdb < "$f"
done
