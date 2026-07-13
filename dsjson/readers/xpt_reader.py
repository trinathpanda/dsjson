"""XPT Reader for dsjson.

Reads SAS XPT files and extracts:
- Data records
- Column metadata (Dataset-JSON compatible)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Any, Tuple
import pandas as pd
import pyreadstat

from dsjson.logging_config import get_logger

logger = get_logger()


class XPTReader:
    """Reader for SAS XPT datasets."""

    def __init__(self, xpt_path: str | Path):
        self.xpt_path = Path(xpt_path)

        if not self.xpt_path.exists():
            raise FileNotFoundError(f"XPT file not found: {xpt_path}")

        self.df: pd.DataFrame | None = None
        self.meta = None

    # ---------------------------------------------------------------------
    # Load file
    # ---------------------------------------------------------------------

    def read(self) -> None:
        """Read XPT file using pyreadstat."""
        try:
            logger.info("Reading XPT file: %s", self.xpt_path)

            self.df, self.meta = pyreadstat.read_xport(str(self.xpt_path))

            logger.info("XPT loaded successfully")
            logger.info(
                "Rows: %s | Columns: %s",
                self.df.shape[0],
                self.df.shape[1],
            )

        except Exception as e:
            logger.error("Error reading XPT: %s", str(e))
            raise

    # ---------------------------------------------------------------------
    # Data extraction
    # ---------------------------------------------------------------------

    def get_records(self) -> List[Dict[str, Any]]:
        """Return dataset records as list of dictionaries."""
        if self.df is None:
            raise RuntimeError("Call read() before accessing records.")

        # Replace NaN → None (JSON-safe)
        df_clean = self.df.where(pd.notnull(self.df), None)

        return df_clean.to_dict(orient="records")

    # ---------------------------------------------------------------------
    # Raw metadata (robust ✅)
    # ---------------------------------------------------------------------

    def get_raw_metadata(self) -> Dict[str, Dict]:
        """Return column metadata from XPT."""

        if self.df is None:
            raise RuntimeError("Call read() first.")

        metadata = {}

        col_names = self.meta.column_names or []
        col_labels = self.meta.column_labels or []
        col_types = self.meta.readstat_variable_types

        for i, col in enumerate(col_names):

            # ✅ Label handling
            if isinstance(col_labels, list):
                label = col_labels[i] if i < len(col_labels) else None
            elif isinstance(col_labels, dict):
                label = col_labels.get(col)
            else:
                label = None

            # ✅ Type handling (FULL FIX)
            if isinstance(col_types, list):
                var_type = col_types[i] if i < len(col_types) else None
            elif isinstance(col_types, dict):
                var_type = col_types.get(col)
            else:
                var_type = None

            metadata[col] = {
                "label": label,
                "type": var_type,
            }

        return metadata

    # ---------------------------------------------------------------------
    # Dataset-JSON compatible columns ✅
    # ---------------------------------------------------------------------

    def get_dataset_json_columns(self) -> List[Dict]:
        """Return Dataset-JSON column structure."""

        if self.df is None:
            raise RuntimeError("Call read() first.")

        columns = []

        col_names = self.meta.column_names or []
        col_labels = self.meta.column_labels or []
        col_types = self.meta.readstat_variable_types

        for i, col in enumerate(col_names):

            # -------------------------
            # ✅ Label handling (robust)
            # -------------------------
            if isinstance(col_labels, list):
                label = col_labels[i] if i < len(col_labels) else col
            elif isinstance(col_labels, dict):
                label = col_labels.get(col, col)
            else:
                label = col  # fallback

            # -------------------------
            # ✅ Type handling (robust)
            # -------------------------
            if isinstance(col_types, list):
                var_type = col_types[i] if i < len(col_types) else None
            elif isinstance(col_types, dict):
                var_type = col_types.get(col)
            else:
                var_type = None

            column = {
                "name": col,
                "label": label if label else col,
                "dataType": self._map_type(var_type),
            }

            columns.append(column)

        return columns

    # ---------------------------------------------------------------------
    # Data type mapping
    # ---------------------------------------------------------------------

    def _map_type(self, var_type: str | None) -> str:
        """Map pyreadstat type → Dataset-JSON type."""

        if not var_type:
            return "string"

        var_type = str(var_type).lower()

        if any(x in var_type for x in ["char", "string"]):
            return "string"
        elif "int" in var_type:
            return "integer"
        elif any(x in var_type for x in ["float", "double", "numeric", "num"]):
            return "double"
        else:
            return "string"

    # ---------------------------------------------------------------------
    # Combined output
    # ---------------------------------------------------------------------

    def get_dataset(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Return:
        - columns (Dataset-JSON)
        - records (data)
        """
        columns = self.get_dataset_json_columns()
        records = self.get_records()

        return columns, records