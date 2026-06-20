"""Inspect the source workbook and generate an EDA Markdown report."""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date, datetime

import pandas as pd

from utils.config import (
    AppConfig,
    SheetProfile,
    get_candidate_duplicate_columns,
    get_candidate_organization_columns,
    get_primary_sheet_profile,
    inspect_workbook_sheets,
    iter_sheet_chunks,
    prepare_runtime,
    select_primary_organization_column,
)
from utils.report_writer import bullet_list, dataframe_to_markdown_table, write_markdown_report


TYPE_PRIORITY = ("date", "numeric", "text", "boolean", "other")


def classify_value(value: object) -> str:
    """Classify a cell value into a coarse analysis type."""

    if value is None or pd.isna(value):
        return "missing"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return "date"
    if isinstance(value, (int, float)):
        return "numeric"
    if isinstance(value, str):
        return "text"
    return "other"


def analyze_primary_sheet(config: AppConfig, primary_sheet: SheetProfile) -> pd.DataFrame:
    """Compute column-level profiling metrics using chunked workbook reads."""

    counters: dict[str, dict[str, object]] = {
        column: {
            "non_null_count": 0,
            "missing_count": 0,
            "type_counts": defaultdict(int),
            "sample_values": [],
        }
        for column in primary_sheet.headers
    }

    for chunk in iter_sheet_chunks(config, primary_sheet.name):
        for column in primary_sheet.headers:
            series = chunk[column]
            for value in series.tolist():
                value_type = classify_value(value)
                if value_type == "missing":
                    counters[column]["missing_count"] += 1
                    continue

                counters[column]["non_null_count"] += 1
                counters[column]["type_counts"][value_type] += 1

                if len(counters[column]["sample_values"]) < 3:
                    counters[column]["sample_values"].append(value)

    data_rows = []
    total_rows = max(primary_sheet.row_count - 1, 0)
    for column in primary_sheet.headers:
        type_counts = counters[column]["type_counts"]
        inferred_type = "unknown"
        if type_counts:
            inferred_type = max(
                TYPE_PRIORITY,
                key=lambda item: (type_counts[item], -TYPE_PRIORITY.index(item)),
            )

        missing_count = int(counters[column]["missing_count"])
        non_null_count = int(counters[column]["non_null_count"])
        missing_pct = round((missing_count / total_rows) * 100, 2) if total_rows else 0.0

        sample_values = ", ".join(str(value) for value in counters[column]["sample_values"])

        data_rows.append(
            {
                "column_name": column,
                "inferred_type": inferred_type,
                "non_null_count": non_null_count,
                "missing_count": missing_count,
                "missing_percentage": missing_pct,
                "sample_values": sample_values,
            }
        )

    return pd.DataFrame(data_rows)


def build_eda_report(
    config: AppConfig,
    sheet_profiles: list[SheetProfile],
    primary_sheet: SheetProfile,
    column_profile: pd.DataFrame,
) -> str:
    """Build the Markdown EDA report content."""

    text_columns = column_profile.loc[
        column_profile["inferred_type"] == "text", "column_name"
    ].tolist()
    numeric_columns = column_profile.loc[
        column_profile["inferred_type"] == "numeric", "column_name"
    ].tolist()
    date_columns = column_profile.loc[
        column_profile["inferred_type"] == "date", "column_name"
    ].tolist()

    duplicate_candidates = get_candidate_duplicate_columns(list(primary_sheet.headers))
    organization_candidates = get_candidate_organization_columns(list(primary_sheet.headers))
    primary_organization_column = select_primary_organization_column(list(primary_sheet.headers))

    sheet_summary = pd.DataFrame(
        [
            {
                "sheet_name": profile.name,
                "row_count": max(profile.row_count - 1, 0),
                "column_count": profile.column_count,
                "non_empty_headers": profile.non_empty_headers,
                "revision_number": profile.revision_number if profile.revision_number >= 0 else "",
                "is_data_candidate": profile.is_data_candidate,
            }
            for profile in sheet_profiles
        ]
    )

    top_missing = column_profile.sort_values(
        by=["missing_percentage", "column_name"],
        ascending=[False, True],
    ).head(10)

    return f"""
# EDA Report

## Dataset Summary

- Source workbook: `{config.raw_dataset_path}`
- Selected primary sheet: `{primary_sheet.name}`
- Data rows in primary sheet: {max(primary_sheet.row_count - 1, 0):,}
- Column count in primary sheet: {primary_sheet.column_count}
- Primary sheet selection rationale: highest structured header coverage, highest revision, and strongest data-like schema

## Workbook Sheets

{dataframe_to_markdown_table(sheet_summary)}

## Inferred Column Types

- Text columns ({len(text_columns)}): {", ".join(text_columns) if text_columns else "None"}
- Numeric columns ({len(numeric_columns)}): {", ".join(numeric_columns) if numeric_columns else "None"}
- Date columns ({len(date_columns)}): {", ".join(date_columns) if date_columns else "None"}

## Candidate Columns

Duplicate detection candidates:
{bullet_list(duplicate_candidates)}

Organization variant detection candidates:
{bullet_list(organization_candidates)}

- Preferred organization column: `{primary_organization_column or "None identified"}`

## Top Missing Columns

{dataframe_to_markdown_table(top_missing)}

## Column Profile

{dataframe_to_markdown_table(column_profile, max_rows=50)}
"""


def main() -> int:
    """Run workbook inspection and write the EDA report."""

    try:
        config, logger = prepare_runtime()
        logger.info("Inspecting workbook structure at %s", config.raw_dataset_path)

        sheet_profiles = inspect_workbook_sheets(config)
        primary_sheet = get_primary_sheet_profile(config)
        logger.info("Selected primary sheet: %s", primary_sheet.name)

        column_profile = analyze_primary_sheet(config, primary_sheet)
        report_content = build_eda_report(config, sheet_profiles, primary_sheet, column_profile)
        write_markdown_report(report_content, config.eda_report_path, config, logger=logger)

        logger.info("EDA inspection completed successfully.")
        return 0
    except Exception as exc:  # pragma: no cover - runtime safety net
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
