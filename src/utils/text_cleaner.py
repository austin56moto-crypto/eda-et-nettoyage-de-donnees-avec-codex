"""Text normalization utilities for the data cleaning pipeline.

The project needs deterministic text cleanup to support duplicate analysis,
organization variant detection, and safe creation of derived cleaned columns.
The helpers in this module preserve null values, avoid mutating original
columns, and apply the normalization rules described in the project plan.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

import pandas as pd


ZERO_WIDTH_PATTERN = re.compile(r"[\u200b\u200c\u200d\ufeff]")
WHITESPACE_PATTERN = re.compile(r"\s+")
PUNCTUATION_PATTERN = re.compile(r"[^\w\s]")
UNDERSCORE_PATTERN = re.compile(r"_+")


def is_missing_text(value: Any) -> bool:
    """Return whether a value should be treated as a missing text value."""

    if value is None:
        return True
    return bool(pd.isna(value))


def strip_accents(value: str) -> str:
    """Remove accents and diacritics from a string."""

    normalized = unicodedata.normalize("NFKD", value)
    return "".join(character for character in normalized if not unicodedata.combining(character))


def normalize_text(
    value: Any,
    *,
    uppercase: bool = True,
    remove_accents: bool = True,
    remove_punctuation: bool = True,
    collapse_whitespace: bool = True,
) -> Any:
    """Normalize a text value according to the project rules.

    Args:
        value: Raw value to normalize.
        uppercase: Whether to convert the text to uppercase.
        remove_accents: Whether to remove accents and diacritics.
        remove_punctuation: Whether to remove punctuation and most special
            characters.
        collapse_whitespace: Whether to collapse repeated whitespace.

    Returns:
        The normalized string or the original missing marker for null values.
    """

    if is_missing_text(value):
        return pd.NA

    normalized = str(value)
    normalized = ZERO_WIDTH_PATTERN.sub("", normalized)
    normalized = normalized.replace("\xa0", " ")
    normalized = normalized.strip()

    if remove_accents:
        normalized = strip_accents(normalized)

    if uppercase:
        normalized = normalized.upper()

    if remove_punctuation:
        normalized = PUNCTUATION_PATTERN.sub(" ", normalized)
        normalized = UNDERSCORE_PATTERN.sub(" ", normalized)

    if collapse_whitespace:
        normalized = WHITESPACE_PATTERN.sub(" ", normalized).strip()

    return normalized or pd.NA


def normalize_series(
    series: pd.Series,
    *,
    logger: logging.Logger | None = None,
    **normalize_kwargs: Any,
) -> pd.Series:
    """Normalize an entire pandas Series while preserving null semantics."""

    if logger:
        logger.debug("Normalizing text series '%s' with %d rows.", series.name, len(series))

    return series.map(lambda value: normalize_text(value, **normalize_kwargs))


def build_cleaned_column_name(column_name: str, suffix: str) -> str:
    """Build a derived-column name without altering the original column."""

    safe_suffix = suffix.strip().replace(" ", "_")
    return f"{column_name}_{safe_suffix}"


def add_normalized_text_column(
    dataframe: pd.DataFrame,
    source_column: str,
    *,
    suffix: str = "normalized_codex",
    logger: logging.Logger | None = None,
    **normalize_kwargs: Any,
) -> str:
    """Create a normalized companion column and return its name.

    Args:
        dataframe: Input DataFrame to extend.
        source_column: Existing text column to normalize.
        suffix: Suffix for the derived column name.
        logger: Optional logger for traceability.
        normalize_kwargs: Keyword arguments forwarded to :func:`normalize_text`.

    Returns:
        The created column name.

    Raises:
        KeyError: If the source column does not exist.
    """

    if source_column not in dataframe.columns:
        raise KeyError(f"Column '{source_column}' does not exist in the DataFrame.")

    cleaned_column_name = build_cleaned_column_name(source_column, suffix)
    dataframe[cleaned_column_name] = normalize_series(
        dataframe[source_column],
        logger=logger,
        **normalize_kwargs,
    )

    if logger:
        logger.debug(
            "Created normalized column '%s' from '%s'.",
            cleaned_column_name,
            source_column,
        )

    return cleaned_column_name
