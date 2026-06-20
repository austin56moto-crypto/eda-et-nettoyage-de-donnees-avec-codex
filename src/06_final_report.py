"""Compile the final Markdown report from generated project artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from utils.config import get_primary_sheet_profile, prepare_runtime
from utils.report_writer import dataframe_to_markdown_table, write_markdown_report


def load_required_csv(path: Path, description: str) -> pd.DataFrame:
    """Load a required CSV artifact and raise a clear error if missing."""

    if not path.exists():
        raise FileNotFoundError(f"{description} not found at '{path}'.")
    return pd.read_csv(path)


def build_final_report(config) -> str:
    """Assemble the final Markdown report."""

    primary_sheet = get_primary_sheet_profile(config)
    total_rows = max(primary_sheet.row_count - 1, 0)
    total_columns = primary_sheet.column_count

    missing_values = load_required_csv(
        config.missing_values_report_path,
        "Missing values report",
    )
    duplicates = load_required_csv(
        config.duplicates_report_path,
        "Duplicates report",
    )
    variants = load_required_csv(
        config.organization_variants_report_path,
        "Organization variants report",
    )
    mapping = load_required_csv(
        config.cleaning_mapping_report_path,
        "Cleaning mapping report",
    )

    missing_summary = (
        missing_values.groupby("recommendation", dropna=False)
        .size()
        .reset_index(name="column_count")
        .sort_values(by=["column_count", "recommendation"], ascending=[False, True])
    )
    duplicate_summary = (
        duplicates.groupby("duplicate_type", dropna=False)
        .size()
        .reset_index(name="group_count")
        .sort_values(by=["group_count", "duplicate_type"], ascending=[False, True])
        if not duplicates.empty
        else pd.DataFrame(columns=["duplicate_type", "group_count"])
    )
    variant_summary = (
        variants.groupby("status", dropna=False)
        .size()
        .reset_index(name="pair_count")
        .sort_values(by=["pair_count", "status"], ascending=[False, True])
        if not variants.empty
        else pd.DataFrame(columns=["status", "pair_count"])
    )
    cleaning_summary = (
        mapping.groupby("status", dropna=False)
        .size()
        .reset_index(name="mapping_count")
        .sort_values(by=["mapping_count", "status"], ascending=[False, True])
        if not mapping.empty
        else pd.DataFrame(columns=["status", "mapping_count"])
    )

    top_missing = missing_values.head(10)
    top_duplicate_groups = duplicates.head(10)
    top_variant_pairs = variants.head(10)

    automatic_count = int((mapping["status"] == "accepted").sum()) if "status" in mapping else 0
    manual_review_count = int((mapping["status"] == "review").sum()) if "status" in mapping else 0

    return f"""
# Final Report

## Dataset Summary

- Source workbook: `{config.raw_dataset_path}`
- Primary sheet: `{primary_sheet.name}`
- Data rows analyzed: {total_rows:,}
- Columns analyzed: {total_columns}
- Cleaned dataset output: `{config.cleaned_dataset_path}`

## Missing Values Summary

{dataframe_to_markdown_table(missing_summary)}

Top missing columns:

{dataframe_to_markdown_table(top_missing)}

## Duplicate Summary

{dataframe_to_markdown_table(duplicate_summary)}

Top duplicate groups:

{dataframe_to_markdown_table(top_duplicate_groups)}

## Organization Analysis

{dataframe_to_markdown_table(variant_summary)}

Top organization variant candidates:

{dataframe_to_markdown_table(top_variant_pairs)}

## Cleaning Summary

{dataframe_to_markdown_table(cleaning_summary)}

- Automatic corrections applied: {automatic_count}
- Manual review mappings retained without auto-correction: {manual_review_count}

## Limitations

- Excel workbooks do not support native pandas chunk streaming, so chunk processing is implemented through `openpyxl` row iteration before conversion into pandas DataFrames.
- Probable duplicates are review-oriented heuristics, not proof of redundant records.
- Organization similarity scores can suggest likely matches, but ambiguous names still require human validation.
- The source workbook already contains revision and intermediate cleaning columns, so downstream analysis may reflect prior upstream transformations.

## Readiness for Unsupervised Learning

The dataset is more suitable for unsupervised learning after cleaning because missingness patterns, duplicate risks, and organization-name inconsistencies have been surfaced in auditable reports. It is not fully analysis-ready until review-status organization mappings and probable duplicate groups are manually validated.

## Required Questions

1. Why clean data before unsupervised learning?
   Cleaning reduces noise, inconsistent scales, and naming fragmentation that would otherwise distort distance-based grouping and cluster interpretation.
2. Why can multiple organization names represent the same entity?
   Administrative datasets often mix punctuation changes, abbreviations, accent differences, legal suffix variations, upstream exports, and manual entry inconsistencies for the same recipient.
3. Why must ambiguous values be reviewed?
   Similar names can belong to different entities, so forcing a correction can merge unrelated organizations and corrupt downstream analysis.
4. Why preserve original columns?
   Original columns maintain auditability, let reviewers trace each change, and protect the source evidence if a cleaning rule needs to be reversed.
5. Why create cleaned columns?
   Separate cleaned columns make modeling easier without destroying source fidelity, and they allow side-by-side validation of automated transformations.
6. How do missing values affect clustering?
   Missing values can bias imputation, reduce comparable features, and create artificial similarity or dissimilarity between records.
7. How do duplicates affect clustering?
   Duplicates overweight repeated entities, inflate cluster density, and can mislead algorithms into treating repeated records as stronger patterns than they really are.
8. Why use chunk processing?
   Chunk processing limits memory pressure on large Excel-derived datasets and allows full-dataset profiling without loading every row into one in-memory DataFrame.
9. Which corrections were automatic?
   Automatic corrections were limited to the {automatic_count} accepted mappings whose normalized or fuzzy similarity scores met the project acceptance threshold.
10. Which require manual review?
   Manual review is still required for the {manual_review_count} review-status organization mappings and for probable duplicate groups flagged in the duplicates report.
"""


def main() -> int:
    """Generate the final Markdown report."""

    try:
        config, logger = prepare_runtime()
        logger.info("Starting final report generation.")

        report = build_final_report(config)
        write_markdown_report(report, config.final_report_path, config, logger=logger)

        logger.info("Final report generation completed successfully.")
        return 0
    except Exception as exc:  # pragma: no cover - runtime safety net
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
