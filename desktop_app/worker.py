"""Background worker for running dsjson conversion from the desktop app."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from dsjson.logging_config import setup_logger


class ConversionWorker(QObject):
    """Run dsjson conversion in a background Qt worker."""

    log_message = Signal(str)
    finished = Signal(bool, str)

    def __init__(
        self,
        domain: str,
        xpt_path: str,
        define_path: str,
        output_dir: str,
        validate: bool = True,
        log_level: str = "INFO",
    ) -> None:
        super().__init__()

        self.domain = domain.strip().upper()
        self.xpt_path = xpt_path
        self.define_path = define_path
        self.output_dir = output_dir
        self.validate = validate
        self.log_level = log_level

    @Slot()
    def run(self) -> None:
        """Execute conversion in background."""
        try:
            self._validate_inputs()

            log_dir = Path(self.output_dir) / "logs"
            setup_logger(output_dir=log_dir, log_level=self.log_level)

            self.log_message.emit(f"[{self.domain}] Starting conversion")
            self.log_message.emit(f"[{self.domain}] XPT file: {self.xpt_path}")
            self.log_message.emit(f"[{self.domain}] Define-XML: {self.define_path}")
            self.log_message.emit(f"[{self.domain}] Output folder: {self.output_dir}")

            dataset_json = self._run_backend_conversion()

            dataset_json_path = self._write_dataset_json(dataset_json)
            validation_report_path = self._write_basic_validation_report(dataset_json)

            self.log_message.emit(
                f"[{self.domain}] Dataset-JSON written: {dataset_json_path}"
            )
            self.log_message.emit(
                f"[{self.domain}] Validation report written: {validation_report_path}"
            )
            self.log_message.emit(f"[{self.domain}] Conversion completed successfully")

            self.finished.emit(
                True,
                f"{self.domain} conversion completed successfully.",
            )

        except Exception as exc:
            error_message = f"{self.domain} conversion failed: {exc}"

            self.log_message.emit(error_message)
            self.log_message.emit(traceback.format_exc())

            self.finished.emit(False, error_message)

    def _validate_inputs(self) -> None:
        """Validate desktop app inputs before running conversion."""
        if not self.domain:
            raise ValueError("Domain is required. Example: DM")

        if not self.xpt_path:
            raise ValueError("XPT file is required.")

        if not self.define_path:
            raise ValueError("Define-XML file is required.")

        if not self.output_dir:
            raise ValueError("Output folder is required.")

        xpt = Path(self.xpt_path)
        define = Path(self.define_path)
        output = Path(self.output_dir)

        if not xpt.exists():
            raise FileNotFoundError(f"XPT file not found: {xpt}")

        if xpt.suffix.lower() != ".xpt":
            raise ValueError("Input dataset must be an XPT file for this prototype.")

        if not define.exists():
            raise FileNotFoundError(f"Define-XML file not found: {define}")

        if define.suffix.lower() != ".xml":
            raise ValueError("Define file must be an XML file.")

        output.mkdir(parents=True, exist_ok=True)

    def _run_backend_conversion(self) -> dict:
        """Run dsjson backend conversion using current ConversionService signature."""
        from dsjson.services.conversion_service import ConversionService

        service = ConversionService()

        self.log_message.emit(f"[{self.domain}] Calling dsjson conversion service")

        dataset_json = service.convert(
            dataset_name=self.domain,
            define_path=self.define_path,
            xpt_path=self.xpt_path,
            metadata_source="Define-XML",
            validate_rows=self.validate,
            strict_records_count=True,
            log_grouped_warnings=True,
        )

        if not isinstance(dataset_json, dict):
            raise TypeError(
                "ConversionService.convert() must return a Dataset-JSON dictionary."
            )

        return dataset_json

    def _write_dataset_json(self, dataset_json: dict) -> Path:
        """Write Dataset-JSON file to output folder."""
        output_dir = Path(self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        dataset_json_path = output_dir / f"{self.domain}.json"

        with dataset_json_path.open("w", encoding="utf-8") as file:
            json.dump(
                dataset_json,
                file,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        return dataset_json_path

    def _write_basic_validation_report(self, dataset_json: dict) -> Path:
        """Write a simple desktop validation report.

        The backend service already logs validation using SchemaValidator.
        This report is a simple output artifact for the desktop app.
        """
        report_dir = Path(self.output_dir) / "validation_report"
        report_dir.mkdir(parents=True, exist_ok=True)

        report_path = report_dir / f"{self.domain}_validation.json"

        required_fields = [
            "datasetJSONCreationDateTime",
            "datasetJSONVersion",
            "name",
            "columns",
            "rows",
        ]

        errors = []
        for field in required_fields:
            if field not in dataset_json:
                errors.append(f"Missing required field: {field}")

        report = {
            "domain": self.domain,
            "ok": len(errors) == 0,
            "errors": errors,
            "warnings": [],
            "records": dataset_json.get("records"),
            "columns": len(dataset_json.get("columns", [])),
            "output_file": str(Path(self.output_dir) / f"{self.domain}.json"),
        }

        with report_path.open("w", encoding="utf-8") as file:
            json.dump(
                report,
                file,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        return report_path