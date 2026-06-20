"""Similarity helpers for organization name variant detection.

The goal of this module is to detect likely name variants without doing an
expensive all-vs-all comparison across every distinct value in a large dataset.
It uses lightweight blocking keys to narrow comparisons before applying
RapidFuzz scoring.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Iterable, Sequence

import pandas as pd
from rapidfuzz import fuzz

from utils.config import SimilarityThresholds, classify_similarity_score


def build_block_keys(normalized_value: str) -> set[str]:
    """Build blocking keys that group likely textual neighbors together."""

    tokens = [token for token in normalized_value.split() if token]
    compact = "".join(tokens)
    first_token = tokens[0] if tokens else ""
    initials = "".join(token[0] for token in tokens[:4])
    length_bucket = len(compact) // 5

    return {
        f"prefix:{compact[:6]}:{length_bucket}",
        f"token:{first_token[:8]}:{length_bucket}",
        f"initials:{initials}:{length_bucket}",
    }


def select_canonical_value(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    """Pick a canonical representative from grouped organization values."""

    return max(
        rows,
        key=lambda row: (
            int(row["frequency"]),
            len(str(row["original_value"])),
            str(row["original_value"]),
        ),
    )


def prepare_value_counts(series: pd.Series, normalized_series: pd.Series) -> pd.DataFrame:
    """Aggregate original organization values with normalized companions."""

    working = pd.DataFrame(
        {
            "original_value": series,
            "normalized_value": normalized_series,
        }
    ).dropna(subset=["original_value", "normalized_value"])

    if working.empty:
        return pd.DataFrame(
            columns=["original_value", "normalized_value", "frequency"]
        )

    working["original_value"] = working["original_value"].astype("string").str.strip()
    working["normalized_value"] = working["normalized_value"].astype("string").str.strip()
    working = working[(working["original_value"] != "") & (working["normalized_value"] != "")]

    grouped = (
        working.groupby(["original_value", "normalized_value"], dropna=False)
        .size()
        .reset_index(name="frequency")
        .sort_values(["frequency", "original_value"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return grouped


def detect_exact_normalized_matches(value_counts: pd.DataFrame) -> list[dict[str, object]]:
    """Generate accepted mappings for values that normalize identically."""

    matches: list[dict[str, object]] = []

    for _, group in value_counts.groupby("normalized_value", dropna=False):
        if len(group) < 2:
            continue

        group_rows = group.to_dict(orient="records")
        canonical_row = select_canonical_value(group_rows)

        for row in group_rows:
            if row["original_value"] == canonical_row["original_value"]:
                continue

            matches.append(
                {
                    "variant_value": row["original_value"],
                    "canonical_value": canonical_row["original_value"],
                    "normalized_variant": row["normalized_value"],
                    "normalized_canonical": canonical_row["normalized_value"],
                    "variant_count": int(row["frequency"]),
                    "canonical_count": int(canonical_row["frequency"]),
                    "similarity_score": 100.0,
                    "status": "accepted",
                    "match_basis": "exact_normalized_match",
                    "justification": (
                        "Values become identical after deterministic text normalization."
                    ),
                }
            )

    return matches


def detect_fuzzy_matches(
    value_counts: pd.DataFrame,
    thresholds: SimilarityThresholds,
    *,
    min_similarity: float = 80.0,
    max_block_size: int = 750,
) -> list[dict[str, object]]:
    """Find likely textual variants using blocked RapidFuzz comparisons."""

    representative_rows = []
    for normalized_value, group in value_counts.groupby("normalized_value", dropna=False):
        group_rows = group.to_dict(orient="records")
        canonical_row = select_canonical_value(group_rows)
        canonical_row = dict(canonical_row)
        canonical_row["normalized_value"] = normalized_value
        representative_rows.append(canonical_row)

    blocks: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in representative_rows:
        for block_key in build_block_keys(str(row["normalized_value"])):
            blocks[block_key].append(row)

    seen_pairs: set[tuple[str, str]] = set()
    matches: list[dict[str, object]] = []

    for block_rows in blocks.values():
        if len(block_rows) < 2:
            continue
        if len(block_rows) > max_block_size:
            block_rows = sorted(
                block_rows,
                key=lambda row: (int(row["frequency"]), len(str(row["original_value"]))),
                reverse=True,
            )[:max_block_size]

        for left_row, right_row in combinations(block_rows, 2):
            pair_key = tuple(
                sorted(
                    (
                        str(left_row["normalized_value"]),
                        str(right_row["normalized_value"]),
                    )
                )
            )
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            left_normalized = str(left_row["normalized_value"])
            right_normalized = str(right_row["normalized_value"])
            if left_normalized == right_normalized:
                continue

            similarity_score = float(fuzz.WRatio(left_normalized, right_normalized))
            if similarity_score < min_similarity:
                continue

            status = classify_similarity_score(similarity_score, thresholds)
            canonical_row, variant_row = sorted(
                (left_row, right_row),
                key=lambda row: (
                    int(row["frequency"]),
                    len(str(row["original_value"])),
                    str(row["original_value"]),
                ),
                reverse=True,
            )

            matches.append(
                {
                    "variant_value": variant_row["original_value"],
                    "canonical_value": canonical_row["original_value"],
                    "normalized_variant": variant_row["normalized_value"],
                    "normalized_canonical": canonical_row["normalized_value"],
                    "variant_count": int(variant_row["frequency"]),
                    "canonical_count": int(canonical_row["frequency"]),
                    "similarity_score": round(similarity_score, 2),
                    "status": status,
                    "match_basis": "fuzzy_blocked_match",
                    "justification": (
                        "RapidFuzz WRatio on normalized organization names within the same block."
                    ),
                }
            )

    return matches


def deduplicate_matches(match_rows: Iterable[dict[str, object]]) -> pd.DataFrame:
    """Keep the strongest mapping per variant value."""

    dataframe = pd.DataFrame(list(match_rows))
    if dataframe.empty:
        return pd.DataFrame(
            columns=[
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

    dataframe = dataframe.sort_values(
        by=["variant_value", "similarity_score", "canonical_count", "canonical_value"],
        ascending=[True, False, False, True],
    )
    dataframe = dataframe.drop_duplicates(subset=["variant_value"], keep="first")
    return dataframe.reset_index(drop=True)


def detect_text_variants(
    series: pd.Series,
    normalized_series: pd.Series,
    thresholds: SimilarityThresholds,
) -> pd.DataFrame:
    """Detect organization text variants and return a review-ready report."""

    value_counts = prepare_value_counts(series, normalized_series)
    exact_matches = detect_exact_normalized_matches(value_counts)
    fuzzy_matches = detect_fuzzy_matches(value_counts, thresholds)

    combined = deduplicate_matches([*exact_matches, *fuzzy_matches])
    if combined.empty:
        return combined

    combined = combined.sort_values(
        by=["status", "similarity_score", "canonical_count", "variant_count"],
        ascending=[True, False, False, False],
    ).reset_index(drop=True)
    return combined
