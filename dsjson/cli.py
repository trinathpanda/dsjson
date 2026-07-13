"""
Command-line interface for dsjson.

Provides a clean CLI similar to dsjconvert style:
- dsjson convert (single dataset/domain)
- logging configuration (log-dir, verbose/log-level)
- validation toggle
- writes Dataset-JSON output + validation report

Examples (PowerShell):
  python -m dsjson.cli convert --domain DM --define demo/input/define.xml --input demo/input/sdtm/dm.xpt

  # Multi-line PowerShell (use backtick `, not \)
  python -m dsjson.cli convert `
    --domain DM `
    --define demo/input/define.xml `
    --input demo/input/sdtm/dm.xpt `
    --out-dir demo/output `
    --report-dir demo/output/validation_report `
    --log-dir demo/output/logs `
    --log-level INFO
"""

import argparse
import json
import os
import sys
from typing import Optional

from dsjson.services.conversion_service import ConversionService
from dsjson.logging_config import setup_logger
from dsjson.reports.validation_report import ValidationReportBuilder
from dsjson.validation.schema_validator import SchemaValidator
from dsjson.exceptions import DSJSONError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dsjson",
        description="dsjson - Convert SDTM datasets (XPT) + Define-XML metadata into CDISC Dataset-JSON v1.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert DM.xpt using Define.xml
  dsjson convert --domain DM --define demo/input/define.xml --input demo/input/sdtm/dm.xpt

  # Save output + report to custom folders
  dsjson convert --domain DM --define demo/input/define.xml --input demo/input/sdtm/dm.xpt --out-dir demo/output --report-dir demo/output/validation_report

  # Disable validation
  dsjson convert --domain DM --define demo/input/define.xml --input demo/input/sdtm/dm.xpt --no-validate

  # Enable verbose logs (DEBUG)
  dsjson convert --domain DM --define demo/input/define.xml --input demo/input/sdtm/dm.xpt -v
"""
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ----------------------------
    # convert command
    # ----------------------------
    convert = subparsers.add_parser("convert", help="Convert one SDTM domain XPT to Dataset-JSON")

    convert.add_argument(
        "--domain", "-m",
        required=True,
        help="Domain/dataset name (e.g., DM, AE, IE, CO)"
    )

    convert.add_argument(
        "--define", "-d",
        required=True,
        help="Path to Define-XML file (define.xml)"
    )

    convert.add_argument(
        "--input", "-i",
        required=True,
        help="Path to input XPT file (e.g., dm.xpt)"
    )

    convert.add_argument(
        "--out-dir", "-o",
        default=True,
        help="Output directory for Dataset-JSON files"
    )

    convert.add_argument(
        "--report-dir", "-r",
        default=None,
        help="Output directory for validation reports (default: <out-dir>/validation_report)"
    )

    convert.add_argument(
        "--log-dir", "-l",
        default=None,
        help="Directory for log file conversion.log (default: <out-dir>/logs)"
    )

    # validation control
    convert.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip schema validation and report generation"
    )

    # logging control
    convert.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output (DEBUG level)"
    )

    convert.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="Explicit log level (overrides --verbose)"
    )

    return parser


def _resolve_defaults(args) -> None:
    """Set default folders based on cwd and out-dir."""
    cwd = os.getcwd()

    if args.report_dir is None:
        args.report_dir = os.path.join(args.out_dir, "validation_report")

    if args.log_dir is None:
        args.log_dir = os.path.join(args.out_dir, "logs")


def _effective_log_level(verbose: bool, log_level: Optional[str]) -> str:
    if log_level:
        return log_level
    return "DEBUG" if verbose else "INFO"


def _run_convert(args) -> int:
    _resolve_defaults(args)

    dataset_name = args.domain.upper()
    define_path = args.define
    xpt_path = args.input

    # setup dsjson logger once per CLI invocation
    setup_logger(
        output_dir=args.log_dir,
        log_level=_effective_log_level(args.verbose, args.log_level),
        enable_console=True,
        enable_file=True,
    )

    # ensure output dirs exist
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.report_dir, exist_ok=True)

    # If user requested no validation, create a validator in skip mode
    validator = SchemaValidator(skip_validation=args.no_validate)

    # Service orchestrates conversion (and uses validator we pass)
    service = ConversionService(validator=validator)

    try:
        dataset_json = service.convert(
            dataset_name=dataset_name,
            define_path=define_path,
            xpt_path=xpt_path,
            metadata_source="Define-XML",
            validate_rows=(not args.no_validate),
        )

        # write Dataset-JSON output
        out_file = os.path.join(args.out_dir, f"{dataset_name}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(dataset_json, f, indent=4)

        print(f"\n Dataset-JSON created: {out_file}")

        # write validation report (only if validation enabled)
        if not args.no_validate:
            full_report = validator.validate_dataset(dataset_json)
            metadata_report = validator.validate_metadata(dataset_json)
            row_report = validator.validate_rows(dataset_json)

            report_data = ValidationReportBuilder.build(
                dataset_name,
                full_report,
                metadata_report,
                row_report
            )

            report_file = os.path.join(args.report_dir, f"{dataset_name}_validation.json")
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=4)

            print(f"Validation report created: {report_file}")

            if not full_report.ok:
                print("Validation FAILED. See report and logs for details.")
                return 1

        print("Conversion completed successfully")
        return 0

    except KeyboardInterrupt:
        print("\n Conversion interrupted by user.")
        return 130

    except DSJSONError as e:
        print(f"\n {e}")
        return 1

    except Exception as e:
        print(f"\n Unexpected error: {e}")
        return 1


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "convert":
        return _run_convert(args)

    return 1


if __name__ == "__main__":
    sys.exit(main())