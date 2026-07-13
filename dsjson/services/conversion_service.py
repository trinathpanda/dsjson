"""Conversion Service for dsjson

Service-layer responsibilities (best practice):
- High-level START/DONE summary logs
- No duplicate step logs (modules already log their own details)
- Grouped validation error reporting (clean + readable)
"""

import time
from collections import Counter
from typing import Dict, Optional, Any

from dsjson.metadata.define_xml import DefineXMLParser
from dsjson.readers.xpt_reader import XPTReader
from dsjson.builder.dataset_json import DatasetJSONBuilder
from dsjson.validation.schema_validator import SchemaValidator
from dsjson.logging_config import get_logger

logger = get_logger()


class ConversionService:
    """Orchestrates Define → XPT → Builder → Validator in a clean service layer."""

    def __init__(self, validator: Optional[SchemaValidator] = None):
        self.builder = DatasetJSONBuilder()
        self.validator = validator or SchemaValidator()

    def convert(
        self,
        dataset_name: str,
        define_path: str,
        xpt_path: str,
        metadata_source: str = "Define-XML",
        validate_rows: bool = True,
        strict_records_count: bool = True,
        log_grouped_warnings: bool = True,
    ) -> Dict[str, Any]:
        """
        Convert one domain dataset to Dataset-JSON (dict).
        - Detailed logs are inside modules
        - This service logs only summary + grouped validation issues
        """
        ds = dataset_name.upper()
        start_time = time.time()

        logger.info("[%s] START", ds)
        logger.info("[%s] metadata_source=%s", ds, metadata_source)

        # ------------------------------
        # Define (detailed logs inside DefineXMLParser)
        # ------------------------------
        define_parser = DefineXMLParser(define_path)
        define_parser.parse()
        define_cols = define_parser.get_dataset_json_columns(ds)
        define_label = define_parser.get_dataset_label(ds)


        # ------------------------------
        # XPT (detailed logs inside XPTReader)
        # ------------------------------
        reader = XPTReader(xpt_path)
        reader.read()
        xpt_cols = reader.get_dataset_json_columns()
        records = reader.get_records()

        # ------------------------------
        # Build (detailed logs inside DatasetJSONBuilder)
        # ------------------------------
        dataset_json = self.builder.build_dataset_json(
            dataset_name=ds,
            define_columns=define_cols,
            xpt_columns=xpt_cols,
            records=records,
            dataset_label=define_label,
            metadata_source=metadata_source,
        )

        # ------------------------------
        # Validate (grouped error reporting here)
        # ------------------------------
        report = self.validator.validate_dataset(
            dataset_json,
            validate_rows=validate_rows,
            strict_records_count=strict_records_count,
        )

        if report.ok:
            logger.info("[%s] Validation PASSED", ds)
        else:
            logger.error("[%s] Validation FAILED", ds)

            # Group errors by message
            err_list = report.errors or []
            error_counts = Counter(e.message for e in err_list)
            for msg, count in error_counts.items():
                logger.error("[%s] %s (x%d)", ds, msg, count)

        # Group warnings (optional, keeps logs tidy)
        warn_list = report.warnings or []
        if warn_list:
            if log_grouped_warnings:
                warn_counts = Counter(w.message for w in warn_list)
                for msg, count in warn_counts.items():
                    logger.warning("[%s] %s (x%d)", ds, msg, count)
            else:
                for w in warn_list:
                    logger.warning("[%s] %s", ds, w.message)

        # ------------------------------
        # Summary
        # ------------------------------
        duration = round(time.time() - start_time, 2)
        logger.info(
            "[%s] DONE | Errors: %d | Warnings: %d | Time: %ss",
            ds,
            len(report.errors or []),
            len(report.warnings or []),
            duration,
        )

        return dataset_json