"""Background worker that runs dsjson conversion in-process for the desktop app."""

from __future__ import annotations

import logging
import time
import traceback
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, Signal, Slot

from dsjson.logging_config import setup_logger
from dsjson.services.conversion_service import ConversionService
from dsjson.validation.schema_validator import SchemaValidator


class _SignalLogHandler(logging.Handler):
    """Forward dsjson log records to the UI (queued across threads by Qt)."""

    def __init__(self, signal) -> None:
        super().__init__()
        self._signal = signal

    def emit(self, record: logging.LogRecord) -> None:
        self._signal.emit(self.format(record))


class ConversionWorker(QObject):
    """Convert one XPT (single mode) or a folder of XPTs (batch mode) in a background thread.

    Uses the same ConversionService as the CLI, so no Python on PATH is needed.
    """

    log_message = Signal(str)
    results_ready = Signal(list)
    finished = Signal(bool, str)

    def __init__(
        self,
        define_path: str,
        output_dir: str,
        domain: str = "",
        xpt_path: str = "",
        data_dir: str = "",
        datasets: Optional[List[str]] = None,
        validate: bool = True,
        log_level: str = "INFO",
    ) -> None:
        super().__init__()

        self.domain = domain.strip().upper()
        self.xpt_path = xpt_path
        self.data_dir = data_dir
        self.datasets = datasets
        self.define_path = define_path
        self.output_dir = output_dir
        self.validate = validate
        self.log_level = log_level

    @Slot()
    def run(self) -> None:
        """Execute conversion in background."""
        output_dir = Path(self.output_dir)
        report_dir = output_dir / "validation_report"
        logger = None

        try:
            self._validate_inputs()

            # setup_logger resets handlers; add the UI handler afterwards
            logger = setup_logger(
                output_dir=output_dir / "logs",
                log_level=self.log_level,
                enable_console=False,
                enable_file=True,
            )
            handler = _SignalLogHandler(self.log_message)
            handler.setLevel(logger.level)
            handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", "%H:%M:%S"))
            logger.addHandler(handler)

            service = ConversionService(validator=SchemaValidator(skip_validation=not self.validate))

            if self.data_dir:
                results = service.convert_folder(
                    data_dir=self.data_dir,
                    define_path=self.define_path,
                    out_dir=str(output_dir),
                    report_dir=str(report_dir) if self.validate else None,
                    datasets=self.datasets,
                )
            else:
                results = [self._convert_single(service, output_dir, report_dir)]

            self.results_ready.emit(results)

            failed = [r["dataset"] for r in results if r["status"] == "FAIL"]
            done = [r for r in results if r["status"] != "SKIPPED"]
            if failed:
                self.finished.emit(False, f"{len(done) - len(failed)}/{len(done)} converted. Failed: {', '.join(failed)}")
            else:
                self.finished.emit(True, f"{len(done)} dataset(s) converted successfully.")

        except Exception as exc:
            self.log_message.emit(f"Conversion failed: {exc}")
            self.log_message.emit(traceback.format_exc())
            self.finished.emit(False, f"Conversion failed: {exc}")

        finally:
            if logger is not None:
                # close the log file so it is not locked between runs
                for h in list(logger.handlers):
                    h.close()
                    logger.removeHandler(h)

    def _convert_single(self, service: ConversionService, output_dir: Path, report_dir: Path) -> dict:
        start = time.time()
        dataset_json = service.convert(self.domain, self.define_path, self.xpt_path)
        service.write_outputs(dataset_json, str(output_dir), str(report_dir) if self.validate else None)
        full = service.last_validation[0]
        return {
            "dataset": self.domain,
            "status": "PASS" if full.ok else "FAIL",
            "records": dataset_json["records"],
            "columns": len(dataset_json["columns"]),
            "errors": len(full.errors or []),
            "warnings": len(full.warnings or []),
            "message": "",
            "seconds": round(time.time() - start, 2),
        }

    def _validate_inputs(self) -> None:
        """Validate desktop app inputs before running conversion."""
        if not self.define_path:
            raise ValueError("Define-XML file is required.")
        if not self.output_dir:
            raise ValueError("Output folder is required.")

        define = Path(self.define_path)
        if not define.exists():
            raise FileNotFoundError(f"Define-XML file not found: {define}")
        if define.suffix.lower() != ".xml":
            raise ValueError("Define file must be an XML file.")

        if self.data_dir:
            if not Path(self.data_dir).is_dir():
                raise FileNotFoundError(f"XPT folder not found: {self.data_dir}")
        else:
            if not self.domain:
                raise ValueError("Domain is required. Example: DM")
            xpt = Path(self.xpt_path)
            if not xpt.exists():
                raise FileNotFoundError(f"XPT file not found: {xpt}")
            if xpt.suffix.lower() != ".xpt":
                raise ValueError("Input dataset must be an XPT file.")

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
