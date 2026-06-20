# PROJECT_PLAN.md

## 14B-TP-EDA-CODEX-NETTOYAGE-DONNEES

### Project Objective

Build a complete Python project that performs exploratory data analysis (EDA), missing value analysis, duplicate detection, text normalization, organization variant detection, cleaning recommendation generation, dataset cleaning, and reporting on a large administrative dataset.

The final solution must satisfy every requirement of the assignment specification.

---

# Dataset

Primary dataset location:

data/raw/2026-05-13_donnees-ouvertes_divulgation-octrois-subventions-et-contributions.xlsx

Before implementing any cleaning logic:

1. Inspect workbook sheets.
2. Determine the primary data sheet.
3. Determine row count.
4. Determine column count.
5. Identify data types.
6. Identify text columns.
7. Identify numeric columns.
8. Identify date columns.
9. Identify candidate columns for duplicate detection.
10. Identify candidate columns for organization variant detection.

Do not make assumptions without inspecting the workbook.

---

# Project Folder Structure

14b-tp-eda-codex-nettoyage-donnees/

├── data/
├── reports/
├── src/
├── README.md
├── requirements.txt
├── AGENTS.md
└── PROJECT_PLAN.md

---

# Required Python Packages

pandas
numpy
rapidfuzz
tabulate
python-dateutil
openpyxl

---

# Coding Standards

- modular architecture
- reusable functions
- type hints
- docstrings
- logging
- robust error handling
- production-quality code

---

# Implementation Order

1. requirements.txt
2. AGENTS.md
3. README.md
4. src/utils/config.py
5. src/utils/file_helpers.py
6. src/utils/text_cleaner.py
7. src/utils/similarity.py
8. src/utils/report_writer.py
9. src/01_inspect_file.py
10. src/02_missing_values.py
11. src/03_detect_duplicates.py
12. src/04_detect_text_variants.py
13. src/05_clean_data.py
14. src/06_final_report.py

---

# Step 1 — Dataset Inspection

Generate reports/eda_report.md

Responsibilities:
- inspect workbook
- identify sheets
- identify primary sheet
- analyze columns
- analyze data types
- produce markdown report

---

# Step 2 — Missing Value Analysis

Generate reports/missing_values_report.csv

Rules:

0% -> Nothing
<5% -> Simple Imputation
5-40% -> Imputation + Missing Flag
>40% -> Evaluate Utility
>70% -> Possible Removal

---

# Step 3 — Duplicate Detection

Generate reports/duplicates_report.csv

Detect:
- exact duplicates
- identifier duplicates
- probable duplicates

---

# Step 4 — Text Normalization

Create normalize_text()

Apply:
- trim spaces
- uppercase conversion
- accent removal
- punctuation removal
- special character cleanup
- multiple space cleanup

---

# Step 5 — Organization Variant Detection

Use RapidFuzz.

Decision Rules:

95-100 -> accepted
80-94 -> review
<80 -> rejected

Generate reports/organization_variants_report.csv

Never auto-correct ambiguous values.

---

# Step 6 — Cleaning Mapping

Generate reports/cleaning_mapping.csv

Columns:
- original_value
- cleaned_value
- status
- justification

---

# Step 7 — Dataset Cleaning

Apply only accepted mappings.

Preserve original values.

Create cleaned columns.

Generate:

data/processed/fichier_nettoye.csv

---

# Step 8 — Final Report

Generate reports/final_report.md

Include:
- dataset summary
- missing values summary
- duplicate summary
- organization analysis
- cleaning summary
- limitations
- readiness for unsupervised learning

---

# Required Questions

1. Why clean data before unsupervised learning?
2. Why can multiple organization names represent the same entity?
3. Why must ambiguous values be reviewed?
4. Why preserve original columns?
5. Why create cleaned columns?
6. How do missing values affect clustering?
7. How do duplicates affect clustering?
8. Why use chunk processing?
9. Which corrections were automatic?
10. Which require manual review?

---

# Final Deliverables

- eda_report.md
- missing_values_report.csv
- duplicates_report.csv
- organization_variants_report.csv
- cleaning_mapping.csv
- final_report.md
- fichier_nettoye.csv
