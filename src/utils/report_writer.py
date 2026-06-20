"""Helpers for writing project reports and exported datasets."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import pandas as pd
from tabulate import tabulate

from utils.config import AppConfig, validate_output_path


def ensure_parent_directory(path: Path) -> None:
    """Create the parent directory for a file path when necessary."""

    path.parent.mkdir(parents=True, exist_ok=True)


def write_dataframe_csv(
    dataframe: pd.DataFrame,
    output_path: Path,
    config: AppConfig,
    *,
    logger: logging.Logger | None = None,
    index: bool = False,
) -> None:
    """Write a DataFrame to CSV after validating the output path."""

    validate_output_path(output_path, config)
    ensure_parent_directory(output_path)
    dataframe.to_csv(output_path, index=index, encoding="utf-8")

    if logger:
        logger.info("Wrote CSV report: %s", output_path)


def dataframe_to_markdown_table(
    dataframe: pd.DataFrame,
    *,
    max_rows: int = 20,
) -> str:
    """Render a compact Markdown table from a DataFrame."""

    if dataframe.empty:
        return "_No rows available._"

    preview = dataframe.head(max_rows).copy()
    preview = preview.fillna("")
    return tabulate(preview, headers="keys", tablefmt="github", showindex=False)


def bullet_list(items: Iterable[str]) -> str:
    """Render a flat Markdown bullet list."""

    materialized = [item for item in items if item]
    if not materialized:
        return "- None"
    return "\n".join(f"- {item}" for item in materialized)


def write_markdown_report(
    content: str,
    output_path: Path,
    config: AppConfig,
    *,
    logger: logging.Logger | None = None,
) -> None:
    """Write a Markdown report after validating the output path."""

    validate_output_path(output_path, config)
    ensure_parent_directory(output_path)
    output_path.write_text(content.strip() + "\n", encoding="utf-8")

    if logger:
        logger.info("Wrote Markdown report: %s", output_path)
