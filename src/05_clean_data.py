"""Generate a cleaning mapping and export a cleaned CSV dataset."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from utils.config import (
    get_candidate_organization_columns,
    get_primary_sheet_profile,
    iter_sheet_chunks,
    prepare_runtime,
    select_primary_organization_column,
    validate_output_path,
)
from utils.report_writer import ensure_parent_directory, write_dataframe_csv
from utils.text_cleaner import build_cleaned_column_name, normalize_series


def load_variant_report(report_path: Path) -> pd.DataFrame:
    """Load the organization variants report required for mapping generation."""

    if not report_path.exists():
        raise FileNotFoundError(
            "Organization variants report not found. Run src/04_detect_text_variants.py first."
        )

    return pd.read_csv(report_path)


def build_cleaning_mapping(variant_report: pd.DataFrame) -> pd.DataFrame:
    """Create the auditable cleaning mapping required by the project."""

    if variant_report.empty:
        return pd.DataFrame(
            columns=[
                "original_value",
                "cleaned_value",
                "status",
                "justification",
                "similarity_score",
                "source_column",
            ]
        )

    mapping = variant_report.rename(
        columns={
            "variant_value": "original_value",
            "canonical_value": "cleaned_value",
        }
    ).copy()
    mapping["justification"] = mapping.apply(
        lambda row: (
            f"{row['match_basis']} with similarity score {row['similarity_score']}. "
            + (
                "Automatic correction permitted."
                if row["status"] == "accepted"
                else "Manual review required before correction."
            )
        ),
        axis=1,
    )

    return mapping[
        [
            "original_value",
            "cleaned_value",
            "status",
            "justification",
            "similarity_score",
            "source_column",
        ]
    ].sort_values(
        by=["status", "similarity_score", "original_value"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def build_accepted_mapping(mapping: pd.DataFrame) -> dict[str, str]:
    """Extract only automatically accepted corrections."""

    accepted = mapping.loc[mapping["status"] == "accepted", ["original_value", "cleaned_value"]]
    return {
        str(original_value).strip(): str(cleaned_value).strip()
        for original_value, cleaned_value in accepted.itertuples(index=False, name=None)
    }


def apply_cleaning_to_chunk(
    chunk: pd.DataFrame,
    organization_columns: list[str],
    primary_organization_column: str,
    accepted_mapping: dict[str, str],
) -> pd.DataFrame:
    """Create normalized and cleaned companion columns for a chunk."""

    cleaned_chunk = chunk.copy()
    for column in organization_columns:
        normalized_column = build_cleaned_column_name(column, "normalized_codex")
        cleaned_chunk[normalized_column] = normalize_series(cleaned_chunk[column])

    cleaned_column = build_cleaned_column_name(primary_organization_column, "cleaned_codex")
    cleaned_chunk[cleaned_column] = cleaned_chunk[primary_organization_column].map(
        lambda value: (
            accepted_mapping.get(str(value).strip(), value)
            if pd.notna(value)
            else pd.NA
        )
    )

    return cleaned_chunk


def export_cleaned_dataset(config, mapping: pd.DataFrame) -> None:
    """Write the cleaned dataset to CSV using chunk processing."""

    primary_sheet = get_primary_sheet_profile(config)
    primary_organization_column = select_primary_organization_column(list(primary_sheet.headers))
    if not primary_organization_column:
        raise ValueError("No primary organization column was identified for cleaning.")

    organization_columns = get_candidate_organization_columns(list(primary_sheet.headers))
    accepted_mapping = build_accepted_mapping(mapping)

    validate_output_path(config.cleaned_dataset_path, config)
    ensure_parent_directory(config.cleaned_dataset_path)

    first_chunk = True
    for chunk in iter_sheet_chunks(config, primary_sheet.name):
        cleaned_chunk = apply_cleaning_to_chunk(
            chunk,
            organization_columns,
            primary_organization_column,
            accepted_mapping,
        )
        cleaned_chunk.to_csv(
            config.cleaned_dataset_path,
            mode="w" if first_chunk else "a",
            header=first_chunk,
            index=False,
            encoding="utf-8",
        )
        first_chunk = False


def main() -> int:
    """Generate cleaning artifacts and the cleaned CSV dataset."""

    try:
        config, logger = prepare_runtime()
        logger.info("Starting cleaning mapping generation and cleaned dataset export.")

        variant_report = load_variant_report(config.organization_variants_report_path)
        mapping = build_cleaning_mapping(variant_report)
        write_dataframe_csv(
            mapping,
            config.cleaning_mapping_report_path,
            config,
            logger=logger,
        )

        export_cleaned_dataset(config, mapping)
        logger.info("Wrote cleaned dataset: %s", config.cleaned_dataset_path)
        logger.info("Dataset cleaning completed successfully.")
        return 0
    except Exception as exc:  # pragma: no cover - runtime safety net
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
