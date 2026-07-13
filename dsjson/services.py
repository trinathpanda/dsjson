"""High-level orchestration services for dsjson."""

from pathlib import Path
from typing import Iterable, Optional

from .logging_config import setup_logger
from .reports.conversion_report import ConversionReport


def convert_dataset(
    data_path: str,
    output_dir: str,
    domain: Optional[str] = None,
    define_path: Optional[str] = None,
    validate: bool = True,
):
    """Convert a single dataset into Dataset-JSON.

    This is a placeholder orchestration function. Implementation will be added
    step by step as readers, metadata extraction, builder, and validation mature.
    """
    raise NotImplementedError("Single dataset conversion will be implemented in the next step.")


def convert_submission_package(
    data_dir: str,
    domains: Iterable[str],
    output_dir: str,
    define_path: Optional[str] = None,
    validate: bool = True,
    log_level: str = "INFO",
):
    """Convert selected SDTM domains into Dataset-JSON files."""
    logger = setup_logger(output_dir=output_dir, log_level=log_level)
    report = ConversionReport()

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    logger.info("Starting Dataset-JSON conversion")
    logger.info("Input data directory: %s", data_dir)
    logger.info("Define-XML path: %s", define_path or "Not provided")
    logger.info("Domains selected: %s", ", ".join(domains))
    logger.info("Validation enabled: %s", validate)

    
    for domain in domains:
        logger.info("[%s] Conversion placeholder - implementation pending", domain)
        report.add_result(domain=domain, status="PENDING", message="Implementation pending")

    report_path = Path(output_dir) / "validation_report.json"
    report.write_json(report_path)
    logger.info("Conversion report written to: %s", report_path)
    logger.info("Dataset-JSON conversion completed")
