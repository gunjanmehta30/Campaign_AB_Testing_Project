#!/usr/bin/env bash
set -e
pip install -r requirements.txt
python src/01_clean_data.py
python src/02_load_and_run_sql.py
python src/03_ab_analysis.py
echo "Done. See charts/, dashboard_data/, docs/REPORT.md"
