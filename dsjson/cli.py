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
import os
import sys
from typing import Optional

from dsjson.services.conversion_service import ConversionService
from dsjson.logging_config import setup_logger
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
        default="output",
        help="Output directory for Dataset-JSON files (default: ./output)"
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

    # ----------------------------
    # convert-all command (batch)
    # ----------------------------
    convert_all = subparsers.add_parser(
        "convert-all", help="Convert every XPT in a folder that Define-XML describes"
    )
    convert_all.add_argument("--data-dir", "-i", required=True, help="Folder with SDTM XPT files")
    convert_all.add_argument("--define", "-d", required=True, help="Path to Define-XML file (define.xml)")
    convert_all.add_argument("--datasets", nargs="+", default=None, help="Only these datasets, e.g. DM AE (default: all)")
    convert_all.add_argument("--out-dir", "-o", default="output", help="Output directory (default: ./output)")
    convert_all.add_argument("--report-dir", "-r", default=None, help="Validation reports (default: <out-dir>/validation_report)")
    convert_all.add_argument("--log-dir", "-l", default=None, help="Log folder (default: <out-dir>/logs)")
    convert_all.add_argument("--no-validate", action="store_true", help="Skip schema validation and reports")
    convert_all.add_argument("-v", "--verbose", action="store_true", help="Verbose output (DEBUG level)")
    convert_all.add_argument(
        "--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default=None,
        help="Explicit log level (overrides --verbose)",
    )

    return parser


def _resolve_defaults(args) -> None:
    """Set default folders based on out-dir."""
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

        # write Dataset-JSON + validation report (report only if validation enabled)
        paths = service.write_outputs(dataset_json, args.out_dir, args.report_dir)
        print(f"\n Dataset-JSON created: {paths['dataset_json']}")

        if "validation_report" in paths:
            print(f"Validation report created: {paths['validation_report']}")

            if not service.last_validation[0].ok:
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


def _run_convert_all(args) -> int:
    _resolve_defaults(args)

    setup_logger(
        output_dir=args.log_dir,
        log_level=_effective_log_level(args.verbose, args.log_level),
        enable_console=True,
        enable_file=True,
    )

    service = ConversionService(validator=SchemaValidator(skip_validation=args.no_validate))

    try:
        results = service.convert_folder(
            data_dir=args.data_dir,
            define_path=args.define,
            out_dir=args.out_dir,
            report_dir=None if args.no_validate else args.report_dir,
            datasets=args.datasets,
        )
    except KeyboardInterrupt:
        print("\n Conversion interrupted by user.")
        return 130
    except DSJSONError as e:
        print(f"\n {e}")
        return 1

    print(f"\n{'Dataset':<10}{'Status':<11}{'Records':>9}{'Columns':>9}{'Errors':>8}{'Warnings':>10}{'Time(s)':>9}")
    for r in results:
        print(
            f"{r['dataset']:<10}{r['status']:<11}{r.get('records', '-'):>9}{r.get('columns', '-'):>9}"
            f"{r.get('errors', '-'):>8}{r.get('warnings', '-'):>10}{r.get('seconds', '-'):>9}"
            + (f"  {r['message']}" if r.get("message") else "")
        )

    failed = sum(1 for r in results if r["status"] == "FAIL")
    print(f"\n{len(results) - failed}/{len(results)} datasets without failures. Output: {args.out_dir}")
    return 1 if failed else 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "convert":
        return _run_convert(args)
    if args.command == "convert-all":
        return _run_convert_all(args)

    return 1


if __name__ == "__main__":
    sys.exit(main())