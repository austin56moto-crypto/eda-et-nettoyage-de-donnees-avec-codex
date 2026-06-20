# EDA et nettoyage de donnees avec Codex

Python project for exploratory data analysis, missing value assessment,
duplicate detection, organization-name variant detection, auditable cleaning
mapping generation, cleaned dataset export, final reporting, and a local visual
dashboard for review.

## What is included

- `src/`: pipeline scripts for inspection, missingness, duplicates, variants,
  cleaning, and final synthesis
- `src/utils/`: shared configuration, text cleaning, similarity, and reporting
  helpers
- `reports/`: generated Markdown and CSV artifacts
- `data/raw/`: placeholder for the original Excel workbook
- `data/processed/`: placeholder for generated cleaned exports
- `dashboard_site/`: Flask templates, styling, and dashboard data layer
- `run_dashboard.py`: local dashboard entrypoint
- `launch_dashboard.command`: one-click launcher for macOS

The original workbook and large processed exports are intentionally not committed
to the public repository. Place the source Excel file in `data/raw/` before
running the pipeline locally.

## Install

```bash
python3 -m pip install -r requirements.txt
```

## Run the data pipeline

1. `python3 src/01_inspect_file.py`
2. `python3 src/02_missing_values.py`
3. `python3 src/03_detect_duplicates.py`
4. `python3 src/04_detect_text_variants.py`
5. `python3 src/05_clean_data.py`
6. `python3 src/06_final_report.py`

## Run the dashboard site

Option 1:

```bash
python3 run_dashboard.py
```

Then open `http://127.0.0.1:8000`.

Option 2 on macOS:

```bash
open ./launch_dashboard.command
```

This starts the Flask app and opens the dashboard in the browser.

## Outputs

- `reports/eda_report.md`
- `reports/missing_values_report.csv`
- `reports/duplicates_report.csv`
- `reports/organization_variants_report.csv`
- `reports/cleaning_mapping.csv`
- `reports/final_report.md`
- `data/processed/fichier_nettoye.csv`

Large outputs are generated locally and remain excluded from git.

## Dashboard features

- Executive overview of dataset health and cleaning posture
- Missingness, duplicate, and organization-variant review panels
- Download links for every generated artifact
- Searchable cleaned-dataset explorer backed by chunked CSV reads
