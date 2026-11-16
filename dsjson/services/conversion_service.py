"""Conversion Service for dsjson

Service-layer responsibilities (best practice):
- High-level START/DONE summary logs
- No duplicate step logs (modules already log their own details)
- Grouped validation error reporting (clean + readable)
"""

import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Any, Iterable

from dsjson.metadata.define_xml import DefineXMLParser
from dsjson.readers.xpt_reader import XPTReader
from dsjson.builder.dataset_json import DatasetJSONBuilder
from dsjson.validation.schema_validator import SchemaValidator, ValidationReport
from dsjson.reports.conversion_report import ConversionReport
from dsjson.reports.validation_report import ValidationReportBuilder
from dsjson.logging_config import get_logger

logger = get_logger()


class ConversionService:
    """Orchestrates Define → XPT → Builder → Validator in a clean service layer."""

    def __init__(self, validator: Optional[SchemaValidator] = None):
        self.builder = DatasetJSONBuilder()
        self.validator = validator or SchemaValidator()
        # (full, metadata, rows) reports of the last convert(); metadata/rows are None when skipped
        self.last_validation: Optional[tuple] = None

    def convert(
        self,
        dataset_name: str,
        define_path: str,
        xpt_path: str,
        metadata_source: str = "Define-XML",
        validate_rows: bool = True,
        strict_records_count: bool = True,
        log_grouped_warnings: bool = True,
        define_parser: Optional[DefineXMLParser] = None,
    ) -> Dict[str, Any]:
        """
        Convert one domain dataset to Dataset-JSON (dict).
        - Detailed logs are inside modules
        - This service logs only summary + grouped validation issues
        - Pass an already parsed define_parser to avoid re-parsing in batch runs
        """
        ds = dataset_name.upper()
        start_time = time.time()

        logger.info("[%s] START", ds)
        logger.info("[%s] metadata_source=%s", ds, metadata_source)

        # ------------------------------
        # Define (detailed logs inside DefineXMLParser)
        # ------------------------------
        if define_parser is None:
            define_parser = DefineXMLParser(define_path)
            define_parser.parse()
        define_cols = define_parser.get_dataset_json_columns(ds)
        define_label = define_parser.get_dataset_label(ds)
        item_group_oid = define_parser.get_item_group_oid(ds)

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
            item_group_oid=item_group_oid,
        )

        # ------------------------------
        # Validate once; reports are kept for write_outputs()
        # ------------------------------
        report = self._validate(dataset_json, validate_rows, strict_records_count)

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

    def _validate(self, dataset_json: Dict[str, Any], validate_rows: bool, strict_records_count: bool) -> ValidationReport:
        """Run metadata + row validation once and keep the parts for the report file."""
        if self.validator.skip_validation:
            full = self.validator.validate_dataset(dataset_json)
            self.last_validation = (full, None, None)
            return full

        meta = self.validator.validate_metadata(dataset_json)
        if validate_rows:
            rows = self.validator.validate_rows(dataset_json, strict_records_count=strict_records_count)
        else:
            rows = ValidationReport(ok=True, schema_used=meta.schema_used, validated_part="rows", errors=[], warnings=[])

        errors = (meta.errors or []) + (rows.errors or [])
        warnings = (meta.warnings or []) + (rows.warnings or [])
        full = ValidationReport(
            ok=not errors,
            schema_used=meta.schema_used,
            validated_part="dataset",
            errors=errors,
            warnings=warnings,
        )
        self.last_validation = (full, meta, rows)
        return full

    def write_outputs(
        self,
        dataset_json: Dict[str, Any],
        out_dir: str,
        report_dir: Optional[str] = None,
    ) -> Dict[str, str]:
        """Write <DS>.json and, when validation ran, <report_dir>/<DS>_validation.json."""
        ds = dataset_json["name"]
        os.makedirs(out_dir, exist_ok=True)

        out_file = os.path.join(out_dir, f"{ds}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(dataset_json, f, indent=4)
        paths = {"dataset_json": out_file}

        if report_dir and self.last_validation and self.last_validation[1] is not None:
            full, meta, rows = self.last_validation
            os.makedirs(report_dir, exist_ok=True)
            report_file = os.path.join(report_dir, f"{ds}_validation.json")
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(ValidationReportBuilder.build(ds, full, meta, rows), f, indent=4)
            paths["validation_report"] = report_file

        return paths

    def convert_folder(
        self,
        data_dir: str,
        define_path: str,
        out_dir: str,
        report_dir: Optional[str] = None,
        datasets: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Convert every XPT in data_dir that Define-XML describes; one failure does not stop the batch."""
        define_parser = DefineXMLParser(define_path)
        define_parser.parse()
        define_names = set(define_parser.get_dataset_names())
        wanted = {d.upper() for d in datasets} if datasets else None

        xpt_files = {p.stem.upper(): p for p in sorted(Path(data_dir).glob("*.xpt"))}
        logger.info("Batch: %d XPT files in %s, %d datasets in Define-XML", len(xpt_files), data_dir, len(define_names))

        for ds in sorted(define_names - set(xpt_files)):
            if wanted is None or ds in wanted:
                logger.warning("[%s] In Define-XML but no XPT file found", ds)

        results: List[Dict[str, Any]] = []
        for ds, xpt_path in xpt_files.items():
            if wanted is not None and ds not in wanted:
                continue
            if ds not in define_names:
                logger.warning("[%s] XPT not described in Define-XML; skipped", ds)
                results.append({"dataset": ds, "status": "SKIPPED", "message": "Not in Define-XML"})
                continue

            start = time.time()
            row: Dict[str, Any] = {"dataset": ds}
            try:
                dataset_json = self.convert(ds, define_path, str(xpt_path), define_parser=define_parser)
                self.write_outputs(dataset_json, out_dir, report_dir)
                full = self.last_validation[0]
                row.update(
                    records=dataset_json["records"],
                    columns=len(dataset_json["columns"]),
                    status="PASS" if full.ok else "FAIL",
                    errors=len(full.errors or []),
                    warnings=len(full.warnings or []),
                    message="",
                )
            except Exception as e:  # keep going: report the failure for this dataset only
                logger.exception("[%s] Conversion failed: %s", ds, e)
                row.update(status="FAIL", message=str(e))
            row["seconds"] = round(time.time() - start, 2)
            results.append(row)

        report = ConversionReport()
        for row in results:
            report.add_result(
                domain=row["dataset"],
                status=row["status"],
                message=row.get("message", ""),
                **{k: v for k, v in row.items() if k not in ("dataset", "status", "message")},
            )
        summary_path = Path(out_dir) / "conversion_summary.json"
        report.write_json(summary_path)
        logger.info("Batch summary written: %s", summary_path)

        return results
