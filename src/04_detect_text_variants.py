"""Detect likely organization-name variants using RapidFuzz."""

from __future__ import annotations

import sys
from collections import defaultdict

import pandas as pd

from utils.config import (
    get_primary_sheet_profile,
    iter_sheet_chunks,
    prepare_runtime,
    select_primary_organization_column,
)
from utils.report_writer import write_dataframe_csv
from utils.similarity import deduplicate_matches, detect_exact_normalized_matches, detect_fuzzy_matches
from utils.text_cleaner import normalize_series


def build_value_counts(config) -> tuple[str, pd.DataFrame]:
    """Aggregate original and normalized organization names from the workbook."""

    primary_sheet = get_primary_sheet_profile(config)
    organization_column = select_primary_organization_column(list(primary_sheet.headers))
    if not organization_column:
        raise ValueError("No organization column was identified in the primary sheet.")

    counts: defaultdict[tuple[str, str], int] = defaultdict(int)
    for chunk in iter_sheet_chunks(config, primary_sheet.name):
        normalized = normalize_series(chunk[organization_column])
        for original_value, normalized_value in zip(chunk[organization_column], normalized, strict=False):
            if pd.isna(original_value) or pd.isna(normalized_value):
                continue

            original_text = str(original_value).strip()
            normalized_text = str(normalized_value).strip()
            if not original_text or not normalized_text:
                continue

            counts[(original_text, normalized_text)] += 1

    value_counts = pd.DataFrame(
        [
            {
                "original_value": original_value,
                "normalized_value": normalized_value,
                "frequency": frequency,
            }
            for (original_value, normalized_value), frequency in counts.items()
        ]
    )

    if not value_counts.empty:
        value_counts = value_counts.sort_values(
            by=["frequency", "original_value"],
            ascending=[False, True],
        ).reset_index(drop=True)

    return organization_column, value_counts


def build_variant_report(config) -> pd.DataFrame:
    """Create the organization variant detection report."""

    organization_column, value_counts = build_value_counts(config)
    if value_counts.empty:
        return pd.DataFrame(
            columns=[
                "source_column",
                "variant_value",
                "canonical_value",
                "normalized_variant",
                "normalized_canonical",
                "variant_count",
                "canonical_count",
                "similarity_score",
                "status",
                "match_basis",
                "justification",
            ]
        )

    exact_matches = detect_exact_normalized_matches(value_counts)
    fuzzy_matches = detect_fuzzy_matches(
        value_counts,
        config.similarity_thresholds,
        min_similarity=float(config.similarity_thresholds.review_min),
    )

    combined = deduplicate_matches([*exact_matches, *fuzzy_matches])
    if combined.empty:
        return combined

    combined.insert(0, "source_column", organization_column)
    combined = combined.sort_values(
        by=["status", "similarity_score", "canonical_count", "variant_count"],
        ascending=[True, False, False, False],
    ).reset_index(drop=True)
    return combined


def main() -> int:
    """Generate the organization variants CSV report."""

    try:
        config, logger = prepare_runtime()
        logger.info("Starting organization variant detection.")

        report = build_variant_report(config)
        write_dataframe_csv(
            report,
            config.organization_variants_report_path,
            config,
            logger=logger,
        )

        logger.info("Organization variant detection completed successfully.")
        return 0
    except Exception as exc:  # pragma: no cover - runtime safety net
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
