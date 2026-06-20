"""Detect exact, identifier, and probable duplicates in the primary sheet."""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date, datetime
from typing import Any

import pandas as pd

from utils.config import (
    AppConfig,
    get_primary_sheet_profile,
    iter_sheet_chunks,
    prepare_runtime,
    select_primary_organization_column,
)
from utils.report_writer import write_dataframe_csv
from utils.text_cleaner import normalize_text


def serialize_value(value: Any) -> str:
    """Serialize a scalar value into a stable string for duplicate keys."""

    if value is None or pd.isna(value):
        return "<MISSING>"
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value).isoformat()
    return str(value).strip()


def build_probable_duplicate_key(row: dict[str, Any], organization_column: str | None) -> str | None:
    """Build a review-oriented duplicate key from important business fields."""

    if not organization_column:
        return None

    organization_value = normalize_text(row.get(organization_column))
    if pd.isna(organization_value):
        return None

    agreement_title = normalize_text(
        row.get("agreement_title_en") or row.get("agreement_title_fr")
    )
    agreement_value = serialize_value(row.get("agreement_value"))
    start_date = serialize_value(row.get("agreement_start_date"))
    end_date = serialize_value(row.get("agreement_end_date"))
    owner_org = serialize_value(row.get("owner_org"))

    business_components = [
        organization_value,
        agreement_title if not pd.isna(agreement_title) else "<MISSING>",
        agreement_value,
        start_date,
        end_date,
        owner_org,
    ]

    populated_components = [component for component in business_components if component != "<MISSING>"]
    if len(populated_components) < 4:
        return None

    return " | ".join(str(component) for component in business_components)


def collect_duplicate_groups(config: AppConfig) -> pd.DataFrame:
    """Scan the primary sheet and collect duplicate groups."""

    primary_sheet = get_primary_sheet_profile(config)
    organization_column = select_primary_organization_column(list(primary_sheet.headers))
    row_number_column = "#" if "#" in primary_sheet.headers else None
    exact_columns = [column for column in primary_sheet.headers if column != row_number_column]
    identifier_columns = [
        column
        for column in ("ref_number", "agreement_number", "recipient_business_number")
        if column in primary_sheet.headers
    ]

    exact_counts: defaultdict[tuple[str, ...], int] = defaultdict(int)
    exact_examples: dict[tuple[str, ...], dict[str, str]] = {}

    identifier_counts: defaultdict[tuple[str, str], int] = defaultdict(int)
    identifier_examples: dict[tuple[str, str], dict[str, str]] = {}

    probable_counts: defaultdict[str, int] = defaultdict(int)
    probable_examples: dict[str, dict[str, str]] = {}

    for chunk in iter_sheet_chunks(config, primary_sheet.name):
        for row in chunk.to_dict(orient="records"):
            exact_key = tuple(serialize_value(row.get(column)) for column in exact_columns)
            exact_counts[exact_key] += 1
            exact_examples.setdefault(
                exact_key,
                {
                    "ref_number": serialize_value(row.get("ref_number")),
                    "organization": serialize_value(
                        row.get(organization_column) if organization_column else None
                    ),
                },
            )

            for column in identifier_columns:
                raw_value = row.get(column)
                if raw_value is None or pd.isna(raw_value):
                    continue

                identifier_key = (column, serialize_value(raw_value))
                identifier_counts[identifier_key] += 1
                identifier_examples.setdefault(
                    identifier_key,
                    {
                        "ref_number": serialize_value(row.get("ref_number")),
                        "organization": serialize_value(
                            row.get(organization_column) if organization_column else None
                        ),
                    },
                )

            probable_key = build_probable_duplicate_key(row, organization_column)
            if probable_key:
                probable_counts[probable_key] += 1
                probable_examples.setdefault(
                    probable_key,
                    {
                        "ref_number": serialize_value(row.get("ref_number")),
                        "organization": serialize_value(
                            row.get(organization_column) if organization_column else None
                        ),
                    },
                )

    duplicate_rows: list[dict[str, object]] = []

    for exact_key, occurrences in exact_counts.items():
        if occurrences < 2:
            continue

        example = exact_examples[exact_key]
        duplicate_rows.append(
            {
                "duplicate_type": "exact_duplicate",
                "rule_name": "all_columns_except_row_number",
                "duplicate_key": " || ".join(exact_key[:8]),
                "occurrences": occurrences,
                "example_ref_number": example["ref_number"],
                "example_organization": example["organization"],
                "review_recommendation": "Confirm whether the repeated rows are redundant records.",
            }
        )

    for (column, duplicate_key), occurrences in identifier_counts.items():
        if occurrences < 2:
            continue

        example = identifier_examples[(column, duplicate_key)]
        duplicate_rows.append(
            {
                "duplicate_type": "identifier_duplicate",
                "rule_name": column,
                "duplicate_key": duplicate_key,
                "occurrences": occurrences,
                "example_ref_number": example["ref_number"],
                "example_organization": example["organization"],
                "review_recommendation": (
                    "Review whether repeated identifiers represent true duplicates or legitimate amendments."
                ),
            }
        )

    for probable_key, occurrences in probable_counts.items():
        if occurrences < 2:
            continue

        example = probable_examples[probable_key]
        duplicate_rows.append(
            {
                "duplicate_type": "probable_duplicate",
                "rule_name": "organization_title_value_date_owner",
                "duplicate_key": probable_key,
                "occurrences": occurrences,
                "example_ref_number": example["ref_number"],
                "example_organization": example["organization"],
                "review_recommendation": (
                    "Manual review required because similarity on business fields does not prove redundancy."
                ),
            }
        )

    if not duplicate_rows:
        return pd.DataFrame(
            columns=[
                "duplicate_type",
                "rule_name",
                "duplicate_key",
                "occurrences",
                "example_ref_number",
                "example_organization",
                "review_recommendation",
            ]
        )

    return pd.DataFrame(duplicate_rows).sort_values(
        by=["duplicate_type", "occurrences", "rule_name"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def main() -> int:
    """Generate the duplicates CSV report."""

    try:
        config, logger = prepare_runtime()
        logger.info("Starting duplicate detection.")

        report = collect_duplicate_groups(config)
        write_dataframe_csv(
            report,
            config.duplicates_report_path,
            config,
            logger=logger,
        )

        logger.info("Duplicate detection completed successfully.")
        return 0
    except Exception as exc:  # pragma: no cover - runtime safety net
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
