"""Background worker for running dsjson CLI conversion from the desktop app."""

from __future__ import annotations

import os
import subprocess
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot


class ConversionWorker(QObject):
    """Run dsjson CLI conversion in a background Qt worker."""

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
        """Execute CLI conversion in background."""
        try:
            self._validate_inputs()

            self.log_message.emit(f"[{self.domain}] Starting conversion")
            self.log_message.emit(f"[{self.domain}] XPT file: {self.xpt_path}")
            self.log_message.emit(f"[{self.domain}] Define-XML: {self.define_path}")
            self.log_message.emit(f"[{self.domain}] Output folder: {self.output_dir}")

            self._run_cli_backend()

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

    def _run_cli_backend(self) -> None:
        """Call the same CLI backend used by command-line execution.

        The desktop app does not create Dataset-JSON or validation reports.
        The CLI/backend remains the single source of truth.
        """
        output_dir = Path(self.output_dir)
        report_dir = output_dir / "validation_report"
        log_dir = output_dir / "logs"

        report_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            "-m",
            "dsjson.cli",
            "convert",
            "--domain",
            self.domain,
            "--define",
            self.define_path,
            "--input",
            self.xpt_path,
            "--out-dir",
            str(output_dir),
            "--report-dir",
            str(report_dir),
            "--log-dir",
            str(log_dir),
            "--log-level",
            self.log_level,
        ]

        if not self.validate:
            cmd.append("--no-validate")

        self.log_message.emit(f"[{self.domain}] Calling CLI backend")

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(Path.cwd()),
            env=env,
        )

        if process.stdout:
            for line in process.stdout:
                clean_line = line.strip()
                if clean_line:
                    self.log_message.emit(clean_line)

        return_code = process.wait()

        if return_code != 0:
            raise RuntimeError(
                f"CLI backend failed with exit code {return_code}"
            )

        dataset_json_path = output_dir / f"{self.domain}.json"
        validation_report_path = report_dir / f"{self.domain}_validation.json"
        log_path = log_dir / "conversion.log"

        if dataset_json_path.exists():
            self.log_message.emit(
                f"[{self.domain}] Dataset-JSON created: {dataset_json_path}"
            )
        else:
            self.log_message.emit(
                f"[{self.domain}] Warning: Dataset-JSON file not found at {dataset_json_path}"
            )

        if validation_report_path.exists():
            self.log_message.emit(
                f"[{self.domain}] Validation report created: {validation_report_path}"
            )
        else:
            self.log_message.emit(
                f"[{self.domain}] Warning: Validation report not found at {validation_report_path}"
            )

        if log_path.exists():
            self.log_message.emit(
                f"[{self.domain}] Log file created: {log_path}"
            )