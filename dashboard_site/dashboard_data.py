"""Data loading and formatting helpers for the local dashboard site."""

from __future__ import annotations

from collections import Counter
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pandas as pd

from src.utils.config import (
    build_config,
    get_candidate_duplicate_columns,
    get_candidate_organization_columns,
    get_primary_sheet_profile,
    select_primary_organization_column,
)


DISPLAY_DATE_FORMAT = "%b %d, %Y"
SEARCH_LIMIT = 75
PREVIEW_LIMIT = 30
FILTER_PREVIEW_LIMIT = 8
FOCUS_OPTION_LIMIT = 30
FOCUS_CHUNK_SIZE = 10_000
KNOWN_REGION_CODES = {
    "AB",
    "BC",
    "MB",
    "NB",
    "NL",
    "NS",
    "NT",
    "NU",
    "ON",
    "PE",
    "QC",
    "SK",
    "YT",
    "Hors du Canada",
}


@dataclass(frozen=True)
class ArtifactDefinition:
    """Metadata for a downloadable dashboard artifact."""

    slug: str
    label: str
    description: str
    path: Path
    kind: str


def _config():
    """Return the resolved application configuration."""

    return build_config()


def get_artifact_definitions() -> list[ArtifactDefinition]:
    """Return the list of downloadable pipeline artifacts."""

    config = _config()
    return [
        ArtifactDefinition(
            slug="eda-report",
            label="EDA Report",
            description="Workbook inspection summary and inferred schema profile.",
            path=config.eda_report_path,
            kind="Markdown",
        ),
        ArtifactDefinition(
            slug="missing-values",
            label="Missing Values",
            description="Column-level missingness rates and handling recommendations.",
            path=config.missing_values_report_path,
            kind="CSV",
        ),
        ArtifactDefinition(
            slug="duplicates",
            label="Duplicates",
            description="Identifier and probable duplicate groups for manual review.",
            path=config.duplicates_report_path,
            kind="CSV",
        ),
        ArtifactDefinition(
            slug="organization-variants",
            label="Organization Variants",
            description="RapidFuzz-backed organization-name mapping candidates.",
            path=config.organization_variants_report_path,
            kind="CSV",
        ),
        ArtifactDefinition(
            slug="cleaning-mapping",
            label="Cleaning Mapping",
            description="Accepted and review-only cleaning mappings with justifications.",
            path=config.cleaning_mapping_report_path,
            kind="CSV",
        ),
        ArtifactDefinition(
            slug="final-report",
            label="Final Report",
            description="Narrative summary of the cleaning pipeline and modeling readiness.",
            path=config.final_report_path,
            kind="Markdown",
        ),
        ArtifactDefinition(
            slug="cleaned-dataset",
            label="Cleaned Dataset",
            description="Processed CSV export with preserved source columns and derived cleaned fields.",
            path=config.cleaned_dataset_path,
            kind="CSV",
        ),
    ]


def get_artifact_map() -> dict[str, ArtifactDefinition]:
    """Return downloadable artifacts keyed by slug."""

    return {artifact.slug: artifact for artifact in get_artifact_definitions()}


def _artifact_signature() -> tuple[tuple[str, int, bool], ...]:
    """Build a hashable signature so cached dashboard data refreshes on file change."""

    entries = []
    for artifact in get_artifact_definitions():
        if artifact.path.exists():
            entries.append((artifact.slug, artifact.path.stat().st_mtime_ns, True))
        else:
            entries.append((artifact.slug, 0, False))
    return tuple(entries)


def _read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV artifact if it exists, otherwise return an empty DataFrame."""

    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _read_markdown(path: Path) -> str:
    """Read a Markdown report if it exists."""

    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _parse_markdown_sections(markdown_text: str) -> dict[str, str]:
    """Split a Markdown report into `##` sections."""

    sections: dict[str, list[str]] = {}
    current_heading: str | None = None

    for line in markdown_text.splitlines():
        if line.startswith("## "):
            current_heading = line[3:].strip()
            sections[current_heading] = []
            continue

        if current_heading is not None:
            sections[current_heading].append(line)

    return {heading: "\n".join(lines).strip() for heading, lines in sections.items()}


def _extract_bullets(section_text: str) -> list[str]:
    """Extract flat bullet items from a Markdown section."""

    bullets = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return bullets


def _extract_numbered_qas(section_text: str) -> list[dict[str, str]]:
    """Extract numbered question/answer blocks from the final report."""

    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None

    for raw_line in section_text.splitlines():
        line = raw_line.rstrip()
        match = re.match(r"^(\d+)\.\s+(.*)$", line.strip())
        if match:
            if current:
                current["answer"] = current["answer"].strip()
                items.append(current)
            current = {
                "number": match.group(1),
                "question": match.group(2).strip(),
                "answer": "",
            }
            continue

        if current and line.strip():
            separator = " " if current["answer"] else ""
            current["answer"] += f"{separator}{line.strip()}"

    if current:
        current["answer"] = current["answer"].strip()
        items.append(current)

    return items


def _format_int(value: int | float | None) -> str:
    """Format integers consistently for the UI."""

    if value is None or pd.isna(value):
        return "0"
    return f"{int(value):,}"


def _format_percent(value: float | int | None) -> str:
    """Format percentage-like values consistently for the UI."""

    if value is None or pd.isna(value):
        return "0%"
    numeric = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return f"{numeric}%"


def _format_currency(value: float | int | None) -> str:
    """Format currency-like values consistently for the UI."""

    if value is None or pd.isna(value):
        return "$0"
    return f"${float(value):,.0f}"


def _coerce_records(dataframe: pd.DataFrame, *, limit: int | None = None) -> list[dict[str, Any]]:
    """Convert a DataFrame into template-friendly records."""

    if dataframe.empty:
        return []

    frame = dataframe.head(limit).copy() if limit else dataframe.copy()
    frame = frame.fillna("")
    return frame.to_dict(orient="records")


def _clean_string(value: object) -> str:
    """Normalize arbitrary values into a trimmed string."""

    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_key(value: object) -> str:
    """Normalize a string value for case-insensitive comparisons."""

    return _clean_string(value).casefold()


def _is_region_like_option(value: str) -> bool:
    """Return whether a region filter option is compact enough for the dashboard."""

    return value in KNOWN_REGION_CODES


def _build_bar_rows(
    dataframe: pd.DataFrame,
    *,
    label_column: str,
    value_column: str,
    max_rows: int = 10,
) -> list[dict[str, Any]]:
    """Prepare percentage-based bar rows for the dashboard."""

    if dataframe.empty:
        return []

    frame = dataframe.head(max_rows).copy()
    max_value = max(float(frame[value_column].max()), 1.0)
    rows = []
    for row in frame.to_dict(orient="records"):
        value = float(row[value_column])
        rows.append(
            {
                "label": str(row[label_column]),
                "value": value,
                "display_value": _format_percent(value)
                if "percent" in value_column
                else _format_int(value),
                "width": round((value / max_value) * 100, 2),
            }
        )
    return rows


def _build_distribution_rows(dataframe: pd.DataFrame, label_column: str, value_column: str) -> list[dict[str, Any]]:
    """Prepare normalized distribution rows for summary cards."""

    if dataframe.empty:
        return []

    total = float(dataframe[value_column].sum()) or 1.0
    rows = []
    for row in dataframe.to_dict(orient="records"):
        value = float(row[value_column])
        rows.append(
            {
                "label": str(row[label_column]),
                "value": int(value),
                "display_value": _format_int(value),
                "share": round((value / total) * 100, 2),
            }
        )
    return rows


def _counter_to_chart_rows(counter: Counter[str], *, limit: int = 8) -> list[dict[str, Any]]:
    """Convert a counter into chart-friendly rows."""

    total = sum(counter.values()) or 1
    rows = []
    for label, value in counter.most_common(limit):
        rows.append(
            {
                "label": label,
                "value": int(value),
                "display_value": _format_int(value),
                "share": round((value / total) * 100, 2),
            }
        )
    return rows


def _top_counter_entry(counter: Counter[str]) -> tuple[str, int]:
    """Return the top counter entry or an empty fallback."""

    if not counter:
        return "", 0
    return counter.most_common(1)[0]


def _value_counter_to_chart_rows(counter: Counter[str], value_map: dict[str, float], *, limit: int = 8) -> list[dict[str, Any]]:
    """Convert grouped counts and value totals into chart-friendly rows."""

    rows = []
    for label, count in counter.most_common(limit):
        total_value = value_map.get(label, 0.0)
        rows.append(
            {
                "label": label,
                "value": int(count),
                "display_value": _format_int(count),
                "secondary": _format_currency(total_value),
            }
        )
    return rows


def _latest_update_stamp(paths: list[Path]) -> str:
    """Return the most recent artifact modification time."""

    available = [path for path in paths if path.exists()]
    if not available:
        return "No generated artifacts yet"

    latest = max(path.stat().st_mtime for path in available)
    return pd.Timestamp(latest, unit="s").strftime(DISPLAY_DATE_FORMAT)


def _read_cleaned_dataset_header(path: Path) -> list[str]:
    """Read cleaned dataset headers without loading the full CSV."""

    if not path.exists():
        return []
    return list(pd.read_csv(path, nrows=0).columns)


def _cleaned_dataset_signature() -> tuple[tuple[str, int, bool], ...]:
    """Return the current artifact signature for cache invalidation."""

    return _artifact_signature()


@lru_cache(maxsize=4)
def _read_focus_filter_options(signature: tuple[tuple[str, int, bool], ...]) -> dict[str, list[str]]:
    """Scan the cleaned dataset once to build dashboard filter options."""

    _ = signature
    config = _config()
    cleaned_path = config.cleaned_dataset_path

    if not cleaned_path.exists():
        return {"provinces": [], "owner_orgs": [], "years": []}

    province_counts: Counter[str] = Counter()
    owner_counts: Counter[str] = Counter()
    year_counts: Counter[str] = Counter()

    usecols = [
        "recipient_province_clean",
        "owner_org_title",
        "agreement_start_date",
    ]

    for chunk in pd.read_csv(cleaned_path, chunksize=FOCUS_CHUNK_SIZE, dtype=str, usecols=usecols):
        for value in chunk["recipient_province_clean"].dropna().astype(str):
            cleaned = value.strip()
            if cleaned:
                province_counts[cleaned] += 1

        for value in chunk["owner_org_title"].dropna().astype(str):
            cleaned = value.strip()
            if cleaned:
                owner_counts[cleaned] += 1

        years = chunk["agreement_start_date"].fillna("").astype(str).str[:4]
        for value in years:
            if len(value) == 4 and value.isdigit():
                year_counts[value] += 1

    top_owner_orgs = [label for label, _ in owner_counts.most_common(FOCUS_OPTION_LIMIT)]
    provinces = sorted(
        value for value in province_counts.keys() if _is_region_like_option(value)
    )
    years = sorted(year_counts.keys(), reverse=True)

    return {
        "provinces": provinces,
        "owner_orgs": top_owner_orgs,
        "years": years,
    }


def _normalize_focus_filters(filters: dict[str, str] | None) -> dict[str, str]:
    """Normalize incoming dashboard focus filters."""

    filters = filters or {}
    return {
        "search": filters.get("search", "").strip(),
        "province": filters.get("province", "").strip(),
        "owner_org": filters.get("owner_org", "").strip(),
        "year": filters.get("year", "").strip(),
    }


@lru_cache(maxsize=16)
def _build_focus_analysis(
    signature: tuple[tuple[str, int, bool], ...],
    search: str,
    province: str,
    owner_org: str,
    year: str,
) -> dict[str, Any]:
    """Build filterable analytics from the cleaned dataset."""

    _ = signature
    config = _config()
    cleaned_path = config.cleaned_dataset_path

    if not cleaned_path.exists():
        return {
            "focus_cards": [],
            "focus_owner_chart": [],
            "focus_province_chart": [],
            "focus_year_chart": [],
            "focus_preview_rows": [],
            "focus_preview_columns": [],
            "focus_record_count": 0,
            "focus_truncated": False,
            "focus_empty": True,
            "focus_applied_filters": [],
        }

    usecols = [
        "ref_number",
        "recipient_legal_name",
        "recipient_legal_name_cleaned_codex",
        "owner_org_title",
        "recipient_province_clean",
        "agreement_title_en",
        "agreement_value",
        "agreement_start_date",
        "agreement_end_date",
    ]

    preview_columns = [
        "ref_number",
        "recipient_legal_name",
        "recipient_legal_name_cleaned_codex",
        "owner_org_title",
        "recipient_province_clean",
        "agreement_title_en",
        "agreement_value",
        "agreement_start_date",
    ]

    search_value = search.casefold()
    province_filter = province.casefold()
    owner_filter = owner_org.casefold()

    record_count = 0
    total_value = 0.0
    value_count = 0
    unique_recipients: set[str] = set()
    unique_owner_orgs: set[str] = set()
    province_counts: Counter[str] = Counter()
    owner_counts: Counter[str] = Counter()
    year_counts: Counter[str] = Counter()
    year_values: dict[str, float] = {}
    preview_frames: list[pd.DataFrame] = []
    remaining_preview = FILTER_PREVIEW_LIMIT

    for chunk in pd.read_csv(cleaned_path, chunksize=FOCUS_CHUNK_SIZE, dtype=str, usecols=usecols):
        normalized = chunk.fillna("")
        mask = pd.Series(True, index=normalized.index)

        if search_value:
            search_mask = pd.Series(False, index=normalized.index)
            for column in (
                "ref_number",
                "recipient_legal_name",
                "recipient_legal_name_cleaned_codex",
                "owner_org_title",
                "agreement_title_en",
            ):
                search_mask = search_mask | normalized[column].str.contains(
                    search_value,
                    case=False,
                    regex=False,
                    na=False,
                )
            mask = mask & search_mask

        if province_filter:
            mask = mask & normalized["recipient_province_clean"].str.casefold().eq(province_filter)

        if owner_filter:
            mask = mask & normalized["owner_org_title"].str.casefold().eq(owner_filter)

        if year:
            start_year = normalized["agreement_start_date"].str[:4]
            mask = mask & start_year.eq(year)

        if not mask.any():
            continue

        filtered = normalized.loc[mask].copy()
        record_count += len(filtered)

        values = pd.to_numeric(filtered["agreement_value"], errors="coerce")
        valid_values = values.dropna()
        total_value += float(valid_values.sum())
        value_count += int(valid_values.notna().sum())

        for raw_value, cleaned_value in zip(
            filtered["recipient_legal_name"],
            filtered["recipient_legal_name_cleaned_codex"],
            strict=False,
        ):
            recipient = _clean_string(cleaned_value) or _clean_string(raw_value)
            if recipient:
                unique_recipients.add(recipient)

        for raw_value in filtered["owner_org_title"]:
            organization = _clean_string(raw_value)
            if organization:
                unique_owner_orgs.add(organization)
                owner_counts[organization] += 1

        for raw_value in filtered["recipient_province_clean"]:
            province_value = _clean_string(raw_value)
            if province_value:
                province_counts[province_value] += 1

        for start_date, agreement_value in zip(
            filtered["agreement_start_date"],
            values.fillna(0),
            strict=False,
        ):
            start_year = _clean_string(start_date)[:4]
            if len(start_year) == 4 and start_year.isdigit():
                year_counts[start_year] += 1
                year_values[start_year] = year_values.get(start_year, 0.0) + float(agreement_value)

        if remaining_preview > 0:
            preview_frames.append(filtered[preview_columns].head(remaining_preview))
            remaining_preview -= len(preview_frames[-1])

    if preview_frames:
        preview_frame = pd.concat(preview_frames, ignore_index=True).head(FILTER_PREVIEW_LIMIT)
    else:
        preview_frame = pd.DataFrame(columns=preview_columns)

    avg_value = total_value / value_count if value_count else 0.0
    top_owner_label, top_owner_count = _top_counter_entry(owner_counts)
    top_province_label, top_province_count = _top_counter_entry(province_counts)
    top_year_label, top_year_count = _top_counter_entry(year_counts)
    top_owner_share = (top_owner_count / record_count * 100) if record_count else 0.0
    top_province_share = (top_province_count / record_count * 100) if record_count else 0.0

    applied_filters = []
    if search:
        applied_filters.append(f'Search: "{search}"')
    if province:
        applied_filters.append(f"Province: {province}")
    if owner_org:
        applied_filters.append(f"Owner organization: {owner_org}")
    if year:
        applied_filters.append(f"Start year: {year}")

    recent_years = sorted(year_counts.keys(), reverse=True)[:8]
    year_chart = [
        {
            "label": year_label,
            "value": int(year_counts[year_label]),
            "display_value": _format_int(year_counts[year_label]),
            "secondary": _format_currency(year_values.get(year_label, 0.0)),
        }
        for year_label in reversed(recent_years)
    ]

    return {
        "focus_cards": [
            {
                "label": "Matching Records",
                "value": _format_int(record_count),
                "detail": "Rows in the cleaned export that match the current analysis lens.",
                "tone": "accent",
            },
            {
                "label": "Total Agreement Value",
                "value": _format_currency(total_value),
                "detail": "Sum of `agreement_value` across matching rows.",
                "tone": "gold",
            },
            {
                "label": "Average Award Value",
                "value": _format_currency(avg_value),
                "detail": "Average non-null agreement value across the filtered set.",
                "tone": "teal",
            },
            {
                "label": "Unique Recipients",
                "value": _format_int(len(unique_recipients)),
                "detail": "Distinct recipients after preferring cleaned recipient names when available.",
                "tone": "ink",
            },
        ],
        "focus_owner_chart": _counter_to_chart_rows(owner_counts, limit=8),
        "focus_province_chart": _counter_to_chart_rows(province_counts, limit=8),
        "focus_year_chart": year_chart,
        "focus_preview_rows": _coerce_records(preview_frame),
        "focus_preview_columns": preview_columns,
        "focus_record_count": record_count,
        "focus_truncated": record_count > FILTER_PREVIEW_LIMIT,
        "focus_empty": record_count == 0,
        "focus_applied_filters": applied_filters,
        "focus_unique_owner_orgs": _format_int(len(unique_owner_orgs)),
        "focus_total_value_raw": total_value,
        "focus_average_value_raw": avg_value,
        "focus_unique_recipient_count": len(unique_recipients),
        "focus_unique_owner_org_count": len(unique_owner_orgs),
        "focus_top_owner_label": top_owner_label,
        "focus_top_owner_count": top_owner_count,
        "focus_top_owner_share": round(top_owner_share, 2),
        "focus_top_province_label": top_province_label,
        "focus_top_province_count": top_province_count,
        "focus_top_province_share": round(top_province_share, 2),
        "focus_top_year_label": top_year_label,
        "focus_top_year_count": top_year_count,
        "focus_top_year_value": year_values.get(top_year_label, 0.0),
    }


@lru_cache(maxsize=4)
def _load_snapshot(signature: tuple[tuple[str, int, bool], ...]) -> dict[str, Any]:
    """Load and shape dashboard data. The signature invalidates the cache."""

    _ = signature
    config = _config()
    primary_sheet = get_primary_sheet_profile(config)

    missing_values = _read_csv(config.missing_values_report_path)
    duplicates = _read_csv(config.duplicates_report_path)
    variants = _read_csv(config.organization_variants_report_path)
    mapping = _read_csv(config.cleaning_mapping_report_path)
    final_report = _read_markdown(config.final_report_path)

    final_sections = _parse_markdown_sections(final_report)
    cleaned_headers = _read_cleaned_dataset_header(config.cleaned_dataset_path)

    missing_summary = (
        missing_values.groupby("recommendation", dropna=False)
        .size()
        .reset_index(name="column_count")
        .sort_values(by=["column_count", "recommendation"], ascending=[False, True])
        if not missing_values.empty
        else pd.DataFrame(columns=["recommendation", "column_count"])
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

    high_missing = missing_values.loc[
        missing_values["recommendation"].eq("Possible Removal")
    ] if not missing_values.empty else pd.DataFrame()
    accepted_count = int(mapping["status"].eq("accepted").sum()) if "status" in mapping else 0
    review_count = int(mapping["status"].eq("review").sum()) if "status" in mapping else 0

    summary_cards = [
        {
            "label": "Rows Analyzed",
            "value": _format_int(max(primary_sheet.row_count - 1, 0)),
            "detail": "Primary sheet rows profiled from the workbook.",
            "tone": "accent",
        },
        {
            "label": "Columns Profiled",
            "value": _format_int(primary_sheet.column_count),
            "detail": "Structured fields detected in the selected data sheet.",
            "tone": "teal",
        },
        {
            "label": "Auto Corrections",
            "value": _format_int(accepted_count),
            "detail": "Accepted organization mappings applied to derived cleaned fields only.",
            "tone": "gold",
        },
        {
            "label": "Manual Reviews",
            "value": _format_int(review_count),
            "detail": "Mappings still requiring human confirmation before correction.",
            "tone": "ink",
        },
    ]

    narrative_cards = [
        {
            "label": "Primary Sheet",
            "value": primary_sheet.name,
            "detail": "Selected by revision number, header coverage, and data-like schema strength.",
        },
        {
            "label": "Duplicate Signals",
            "value": _format_int(len(duplicates)),
            "detail": "Grouped duplicate candidates across identifier and probable business rules.",
        },
        {
            "label": "High Missing Columns",
            "value": _format_int(len(high_missing)),
            "detail": "Columns currently flagged as Possible Removal due to >70% missingness.",
        },
        {
            "label": "Processed Columns",
            "value": _format_int(len(cleaned_headers)),
            "detail": "The cleaned export includes original fields plus derived `_codex` columns.",
        },
    ]

    return {
        "project_title": "Grant Data Quality Review",
        "last_updated": _latest_update_stamp(
            [
                config.eda_report_path,
                config.missing_values_report_path,
                config.duplicates_report_path,
                config.organization_variants_report_path,
                config.cleaning_mapping_report_path,
                config.final_report_path,
                config.cleaned_dataset_path,
            ]
        ),
        "summary_cards": summary_cards,
        "narrative_cards": narrative_cards,
        "primary_sheet": primary_sheet.name,
        "duplicate_candidates": get_candidate_duplicate_columns(list(primary_sheet.headers)),
        "organization_candidates": get_candidate_organization_columns(list(primary_sheet.headers)),
        "primary_organization_column": select_primary_organization_column(list(primary_sheet.headers)),
        "missing_distribution": _build_distribution_rows(
            missing_summary,
            "recommendation",
            "column_count",
        ),
        "missing_bars": _build_bar_rows(
            missing_values.sort_values(
                by=["missing_percentage", "column_name"],
                ascending=[False, True],
            ),
            label_column="column_name",
            value_column="missing_percentage",
        ),
        "missing_table": _coerce_records(missing_values, limit=12),
        "duplicate_distribution": _build_distribution_rows(
            duplicate_summary,
            "duplicate_type",
            "group_count",
        ),
        "duplicate_table": _coerce_records(
            duplicates.sort_values(by=["occurrences", "duplicate_type"], ascending=[False, True]),
            limit=12,
        ),
        "variant_distribution": _build_distribution_rows(
            variant_summary,
            "status",
            "pair_count",
        ),
        "accepted_variants": _coerce_records(
            variants.loc[variants["status"].eq("accepted")].sort_values(
                by=["similarity_score", "canonical_count", "variant_count"],
                ascending=[False, False, False],
            ),
            limit=10,
        )
        if not variants.empty
        else [],
        "review_variants": _coerce_records(
            variants.loc[variants["status"].eq("review")].sort_values(
                by=["similarity_score", "canonical_count", "variant_count"],
                ascending=[False, False, False],
            ),
            limit=10,
        )
        if not variants.empty
        else [],
        "limitations": _extract_bullets(final_sections.get("Limitations", "")),
        "readiness_text": final_sections.get("Readiness for Unsupervised Learning", ""),
        "required_questions": _extract_numbered_qas(final_sections.get("Required Questions", "")),
        "downloads": [
            {
                "slug": artifact.slug,
                "label": artifact.label,
                "description": artifact.description,
                "kind": artifact.kind,
                "exists": artifact.path.exists(),
                "size": _format_int(artifact.path.stat().st_size) + " bytes"
                if artifact.path.exists()
                else "Unavailable",
            }
            for artifact in get_artifact_definitions()
        ],
    }


def get_dashboard_context(filters: dict[str, str] | None = None) -> dict[str, Any]:
    """Return the full dashboard context for the main page."""

    signature = _artifact_signature()
    normalized_filters = _normalize_focus_filters(filters)
    base_context = dict(_load_snapshot(signature))
    focus_options = _read_focus_filter_options(signature)
    global_focus = _build_focus_analysis(signature, "", "", "", "")
    focus_analysis = _build_focus_analysis(
        signature,
        normalized_filters["search"],
        normalized_filters["province"],
        normalized_filters["owner_org"],
        normalized_filters["year"],
    )

    active_filter_pairs = {
        key: value
        for key, value in normalized_filters.items()
        if value
    }

    base_context.update(
        {
            "focus_filters": normalized_filters,
            "focus_filter_options": focus_options,
            "focus_reset_query": "",
            "focus_query_string": urlencode(active_filter_pairs),
            "focus_active": bool(active_filter_pairs),
        }
    )
    base_context.update(focus_analysis)

    global_records = max(global_focus["focus_record_count"], 1)
    global_value = max(global_focus["focus_total_value_raw"], 1.0)
    record_share = focus_analysis["focus_record_count"] / global_records * 100
    value_share = focus_analysis["focus_total_value_raw"] / global_value * 100

    focus_top_owner_label = focus_analysis["focus_top_owner_label"] or "No dominant owner"
    focus_top_province_label = focus_analysis["focus_top_province_label"] or "No dominant region"
    focus_top_year_label = focus_analysis["focus_top_year_label"] or "No year signal"

    missing_risk = base_context["missing_bars"][0] if base_context["missing_bars"] else None
    duplicate_hotspot = base_context["duplicate_table"][0] if base_context["duplicate_table"] else None
    mapping_total = 0
    accepted_ratio = 0.0
    if base_context["variant_distribution"]:
        mapping_total = sum(item["value"] for item in base_context["variant_distribution"])
        accepted_item = next(
            (item for item in base_context["variant_distribution"] if item["label"] == "accepted"),
            None,
        )
        if accepted_item and mapping_total:
            accepted_ratio = accepted_item["value"] / mapping_total * 100

    base_context["comparison_cards"] = [
        {
            "label": "Lens share of dataset",
            "value": _format_percent(record_share),
            "detail": (
                f"{_format_int(focus_analysis['focus_record_count'])} matching rows out of "
                f"{_format_int(global_focus['focus_record_count'])}."
            ),
        },
        {
            "label": "Lens share of award value",
            "value": _format_percent(value_share),
            "detail": f"{_format_currency(focus_analysis['focus_total_value_raw'])} within the selected slice.",
        },
        {
            "label": "Dominant owner organization",
            "value": focus_top_owner_label,
            "detail": (
                f"{_format_percent(focus_analysis['focus_top_owner_share'])} of the current slice "
                f"({_format_int(focus_analysis['focus_top_owner_count'])} rows)."
                if focus_analysis["focus_top_owner_count"]
                else "No single owner organization stands out in the current slice."
            ),
        },
        {
            "label": "Dominant region",
            "value": focus_top_province_label,
            "detail": (
                f"{_format_percent(focus_analysis['focus_top_province_share'])} of the current slice "
                f"({_format_int(focus_analysis['focus_top_province_count'])} rows)."
                if focus_analysis["focus_top_province_count"]
                else "No single region stands out in the current slice."
            ),
        },
    ]
    base_context["insight_cards"] = [
        {
            "label": "Highest missing field",
            "value": missing_risk["label"] if missing_risk else "Unavailable",
            "detail": (
                f"{missing_risk['display_value']} missing and already in the highest-risk recommendation band."
                if missing_risk
                else "Missingness signals were not available."
            ),
        },
        {
            "label": "Largest duplicate hotspot",
            "value": duplicate_hotspot["duplicate_key"] if duplicate_hotspot else "Unavailable",
            "detail": (
                f"{_format_int(duplicate_hotspot['occurrences'])} rows under {duplicate_hotspot['duplicate_type']}."
                if duplicate_hotspot
                else "Duplicate clustering was not available."
            ),
        },
        {
            "label": "Automatic mapping rate",
            "value": _format_percent(accepted_ratio),
            "detail": (
                f"{_format_int(mapping_total)} organization variant pairs were evaluated across accepted and review states."
                if mapping_total
                else "Variant mapping totals were not available."
            ),
        },
        {
            "label": "Strongest start-year signal",
            "value": focus_top_year_label,
            "detail": (
                f"{_format_int(focus_analysis['focus_top_year_count'])} rows and "
                f"{_format_currency(focus_analysis['focus_top_year_value'])} in value."
                if focus_analysis["focus_top_year_count"]
                else "No dominant start-year signal is available for the current slice."
            ),
        },
    ]
    return base_context


def _dataset_display_columns(headers: list[str]) -> list[str]:
    """Choose the most useful cleaned dataset columns for explorer output."""

    preferred = [
        "ref_number",
        "recipient_legal_name",
        "recipient_legal_name_cleaned_codex",
        "owner_org_title",
        "agreement_title_en",
        "agreement_value",
        "agreement_start_date",
        "agreement_end_date",
    ]
    available = set(headers)
    return [column for column in preferred if column in available]


def search_cleaned_dataset(query: str = "", field: str = "all", limit: int = SEARCH_LIMIT) -> dict[str, Any]:
    """Return a sample or filtered slice of the cleaned dataset for the explorer."""

    config = _config()
    cleaned_path = config.cleaned_dataset_path

    if not cleaned_path.exists():
        return {
            "columns": [],
            "rows": [],
            "query": query,
            "field": field,
            "result_count": 0,
            "truncated": False,
            "error": "Cleaned dataset not found. Run the cleaning pipeline first.",
        }

    headers = _read_cleaned_dataset_header(cleaned_path)
    display_columns = _dataset_display_columns(headers)
    if not display_columns:
        return {
            "columns": [],
            "rows": [],
            "query": query,
            "field": field,
            "result_count": 0,
            "truncated": False,
            "error": "No display columns were found in the cleaned dataset.",
        }

    search_columns = {
        "all": [
            column
            for column in (
                "ref_number",
                "recipient_legal_name",
                "recipient_legal_name_cleaned_codex",
                "owner_org_title",
                "agreement_title_en",
            )
            if column in headers
        ],
        "reference": [column for column in ("ref_number",) if column in headers],
        "recipient": [
            column
            for column in (
                "recipient_legal_name",
                "recipient_legal_name_cleaned_codex",
            )
            if column in headers
        ],
        "organization": [column for column in ("owner_org_title",) if column in headers],
        "agreement": [column for column in ("agreement_title_en",) if column in headers],
    }

    chosen_columns = search_columns.get(field, search_columns["all"])
    safe_query = query.strip()

    if not safe_query:
        preview = pd.read_csv(cleaned_path, nrows=PREVIEW_LIMIT, usecols=display_columns, dtype=str)
        return {
            "columns": display_columns,
            "rows": _coerce_records(preview),
            "query": "",
            "field": field,
            "result_count": len(preview),
            "truncated": False,
            "error": "",
        }

    frames: list[pd.DataFrame] = []
    matched_rows = 0
    truncated = False

    for chunk in pd.read_csv(cleaned_path, chunksize=10_000, dtype=str, usecols=lambda name: name in set(display_columns + chosen_columns)):
        normalized = chunk.fillna("")
        mask = pd.Series(False, index=normalized.index)
        for column in chosen_columns:
            mask = mask | normalized[column].str.contains(safe_query, case=False, regex=False, na=False)

        if not mask.any():
            continue

        filtered = normalized.loc[mask, display_columns]
        frames.append(filtered)
        matched_rows += len(filtered)

        if matched_rows >= limit:
            truncated = True
            break

    if frames:
        results = pd.concat(frames, ignore_index=True).head(limit)
    else:
        results = pd.DataFrame(columns=display_columns)

    return {
        "columns": display_columns,
        "rows": _coerce_records(results),
        "query": safe_query,
        "field": field,
        "result_count": len(results),
        "truncated": truncated,
        "error": "",
    }


def get_explorer_filters() -> list[dict[str, str]]:
    """Return supported search scopes for the explorer."""

    return [
        {"value": "all", "label": "All key fields"},
        {"value": "reference", "label": "Reference number"},
        {"value": "recipient", "label": "Recipient name"},
        {"value": "organization", "label": "Owner organization"},
        {"value": "agreement", "label": "Agreement title"},
    ]
