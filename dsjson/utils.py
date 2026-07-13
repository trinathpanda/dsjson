"""Utility helpers for dsjson."""

from pathlib import Path
from typing import Optional, List


# ---------------------------------------------------------------------
# File handling
# ---------------------------------------------------------------------

SUPPORTED_EXTENSIONS = [".xpt", ".sas7bdat", ".csv"]


def find_domain_file(data_dir: str, domain: str) -> Optional[Path]:
    """Find dataset file for domain."""
    data_path = Path(data_dir)

    for ext in SUPPORTED_EXTENSIONS:
        for name in (domain.upper(), domain.lower()):
            candidate = data_path / f"{name}{ext}"
            if candidate.exists():
                return candidate

    return None


# ---------------------------------------------------------------------
# Data helpers (IMPORTANT ✅)
# ---------------------------------------------------------------------

def normalize_column_name(name: str) -> str:
    return name.strip().upper()


def match_column_names(source_columns: List[str], metadata_columns: List[str]) -> dict:
    """Match column names ignoring case."""

    src = {normalize_column_name(c): c for c in source_columns}
    meta = {normalize_column_name(c): c for c in metadata_columns}

    if set(src.keys()) != set(meta.keys()):
        missing_meta = set(src.keys()) - set(meta.keys())
        missing_src = set(meta.keys()) - set(src.keys())

        raise ValueError(
            f"Column mismatch → Missing in metadata: {missing_meta}, Missing in source: {missing_src}"
        )

    return {src[k]: meta[k] for k in src}


def infer_data_type(value) -> Optional[str]:
    """Infer Dataset-JSON data type."""

    import datetime

    if isinstance(value, str):
        return "string"
    elif isinstance(value, bool):
        return "string"
    elif isinstance(value, int):
        return "integer"
    elif isinstance(value, float):
        return "double"
    elif isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return "double"
    else:
        return None