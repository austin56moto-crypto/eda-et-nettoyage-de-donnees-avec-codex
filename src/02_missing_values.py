"""Analyze missing values in the primary workbook sheet."""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date, datetime

import pandas as pd

from utils.config import (
    AppConfig,
    get_missing_value_recommendation,
    get_primary_sheet_profile,
    iter_sheet_chunks,
    prepare_runtime,
)
from utils.report_writer import write_dataframe_csv


def classify_value(value: object) -> str:
    """Infer a coarse data type for reporting purposes."""

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


def build_missing_values_report(config: AppConfig) -> pd.DataFrame:
    """Scan the primary sheet and summarize missingness by column."""

    primary_sheet = get_primary_sheet_profile(config)
    total_rows = max(primary_sheet.row_count - 1, 0)

    counters: dict[str, dict[str, object]] = {
        column: {
            "missing_count": 0,
            "type_counts": defaultdict(int),
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
                else:
                    counters[column]["type_counts"][value_type] += 1

    rows = []
    for column in primary_sheet.headers:
        missing_count = int(counters[column]["missing_count"])
        missing_pct = round((missing_count / total_rows) * 100, 2) if total_rows else 0.0
        type_counts = counters[column]["type_counts"]
        inferred_type = (
            max(type_counts, key=type_counts.get)
            if type_counts
            else "unknown"
        )

        rows.append(
            {
                "column_name": column,
                "inferred_type": inferred_type,
                "total_rows": total_rows,
                "missing_count": missing_count,
                "missing_percentage": missing_pct,
                "recommendation": get_missing_value_recommendation(
                    missing_pct,
                    config.missing_value_thresholds,
                ),
            }
        )

    return pd.DataFrame(rows).sort_values(
        by=["missing_percentage", "column_name"],
        ascending=[False, True],
    ).reset_index(drop=True)


def main() -> int:
    """Generate the missing values CSV report."""

    try:
        config, logger = prepare_runtime()
        logger.info("Starting missing value analysis.")

        report = build_missing_values_report(config)
        write_dataframe_csv(
            report,
            config.missing_values_report_path,
            config,
            logger=logger,
        )

        logger.info("Missing value analysis completed successfully.")
        return 0
    except Exception as exc:  # pragma: no cover - runtime safety net
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
