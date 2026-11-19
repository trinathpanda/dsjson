"""Dataset JSON Builder for dsjson (Schema-Compliant Final Version)"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from dsjson.logging_config import get_logger

logger = get_logger()

OPTIONAL_TOP_LEVEL_KEYS = (
    "fileOID",
    "dbLastModifiedDateTime",
    "originator",
    "sourceSystem",
    "studyOID",
    "metaDataVersionOID",
    "metaDataRef",
)


class DatasetJSONBuilder:
    """Build Dataset-JSON using Define + XPT."""

    # ✅ Allowed schema fields ONLY
    ALLOWED_COLUMN_KEYS = {
        "itemOID",
        "name",
        "label",
        "dataType",
        "length",
        "keySequence",
    }

    def __init__(self):
        pass

    # ---------------------------------------------------------------------
    # Merge columns (Define priority ✅)
    # ---------------------------------------------------------------------
    def merge_columns(self, define_cols: List[Dict], xpt_cols: List[Dict]) -> List[Dict]:
        """Merge Define metadata with XPT metadata."""

        if not define_cols:
            logger.warning("Define columns missing; using XPT columns only")
            return xpt_cols

        xpt_col_map = {col.get("name"): col for col in xpt_cols if col.get("name")}
        merged: List[Dict] = []

        for dcol in define_cols:
            name = dcol.get("name")

            # ✅ Keep full metadata internally
            final_col = dict(dcol)

            xcol = xpt_col_map.get(name)

            if xcol:
                if not final_col.get("label"):
                    final_col["label"] = xcol.get("label", name)

                if not final_col.get("dataType"):
                    final_col["dataType"] = xcol.get("dataType", "string")

                if not final_col.get("itemOID"):
                    final_col["itemOID"] = xcol.get("itemOID") or f"IT.{name}"

            # ✅ Ensure required minimal fields
            if not final_col.get("label"):
                final_col["label"] = name

            if not final_col.get("dataType"):
                final_col["dataType"] = "string"

            merged.append(final_col)

        logger.info("Merged columns: %d", len(merged))
        return merged

    # ---------------------------------------------------------------------
    # ✅ FILTER FOR SCHEMA
    # ---------------------------------------------------------------------
    def _filter_schema_columns(self, columns: List[Dict]) -> List[Dict]:
        """Keep only schema-compliant keys."""
        filtered = []

        for col in columns:
            clean_col = {k: v for k, v in col.items() if k in self.ALLOWED_COLUMN_KEYS}

            # ✅ Ensure required fields
            if "itemOID" not in clean_col:
                clean_col["itemOID"] = f"IT.{clean_col.get('name', 'UNKNOWN')}"

            filtered.append(clean_col)

        logger.debug("Filtered columns for schema compliance")
        return filtered

    # ---------------------------------------------------------------------
    # Convert records → rows
    # ---------------------------------------------------------------------
    def build_rows(self, records: List[Dict[str, Any]], columns: List[Dict]) -> List[List]:
        def _normalize_value(value):
            if isinstance(value, float) and value.is_integer():
                return int(value)
            return value

        col_order = [col["name"] for col in columns if "name" in col]

        rows: List[List] = []

        for record in records:
            row = [_normalize_value(record.get(col_name)) for col_name in col_order] # -- this need to fix for some specific variable to avoide generalization
            rows.append(row)

        logger.info("Built rows: %d", len(rows))
        return rows

    # ---------------------------------------------------------------------
    # ✅ FINAL BUILD
    # ---------------------------------------------------------------------
    def build_dataset_json(
        self,
        dataset_name: str,
        define_columns: List[Dict],
        xpt_columns: List[Dict],
        records: List[Dict],
        dataset_label: Optional[str] = None,
        metadata_source: str = "Define-XML",
        item_group_oid: Optional[str] = None,
        file_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        """file_metadata: optional top-level fields (fileOID, studyOID, ...); empty values are left out."""

        ds = dataset_name.upper()

        logger.debug("[%s] Building Dataset-JSON", ds)

        # Step 1: merge metadata
        merged_columns = self.merge_columns(define_columns, xpt_columns)

        # Step 2: build rows BEFORE filtering (order matters)
        rows = self.build_rows(records, merged_columns)

        # Step 3: filter columns for schema compliance ✅
        columns = self._filter_schema_columns(merged_columns)

        # ✅ Timestamp with timezone (better)
        creation_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        dataset_json = {
            "datasetJSONCreationDateTime": creation_time,
            "datasetJSONVersion": "1.1.0",
        }
        # Optional fields in the order of the Dataset-JSON v1.1 specification
        for key in OPTIONAL_TOP_LEVEL_KEYS:
            value = (file_metadata or {}).get(key)
            if value:
                dataset_json[key] = value
        dataset_json |= {
            "itemGroupOID": item_group_oid or f"IG.{ds}",
            "records": len(rows),  # spec order: records before name/label (helps streaming readers)
            "name": ds,
            "label": dataset_label or ds,
            "columns": columns,
            "rows": rows,
        }

        logger.info("[%s] Dataset-JSON ready (rows=%d, cols=%d)", ds, len(rows), len(columns))

        return dataset_json