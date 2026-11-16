"""
Schema validation for dsjson.

Features:
- Schema auto-detection (no hard-coded path required)
- Skip validation option
- Collect multiple errors (does not stop at first failure)
- Structured validation report (errors include JSON path + schema path)
- Separate validation for: metadata and rows
- Extra structural checks helpful for Dataset-JSON pipelines
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from jsonschema import Draft201909Validator
from jsonschema.exceptions import SchemaError

from dsjson.logging_config import get_logger

logger = get_logger()


@dataclass
class ValidationIssue:
    level: str  # "error" | "warning"
    message: str
    instance_path: str = ""
    schema_path: str = ""
    validator: str = ""
    validator_value: Any = None


@dataclass
class ValidationReport:
    ok: bool
    schema_used: str = ""
    validated_part: str = ""  # "dataset" | "metadata" | "rows"
    errors: Optional[List[ValidationIssue]] = None
    warnings: Optional[List[ValidationIssue]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "schema_used": self.schema_used,
            "validated_part": self.validated_part,
            "errors": [asdict(x) for x in (self.errors or [])],
            "warnings": [asdict(x) for x in (self.warnings or [])],
        }


class SchemaValidator:
    """Dataset-JSON validator (JSON Schema based)."""

    DEFAULT_SCHEMA_CANDIDATES = [
        Path("dsjson") / "validation" / "schemas" / "dataset-json-v1.1.schema.json",
        Path("dsjson") / "validation" / "schemas" / "dataset.schema.json",
        Path("dataset.schema.json"),
        Path("schemas") / "dataset-json-v1.1.schema.json",
        Path("schema") / "dataset.schema.json",
        Path("demo") / "schema" / "dataset.schema.json",
        Path("demo") / "input" / "dataset.schema.json",
    ]

    def __init__(
        self,
        schema_path: Optional[Union[str, Path]] = None,
        skip_validation: bool = False,
    ):
        self.skip_validation = skip_validation
        self.schema_path: Optional[Path] = self._resolve_schema_path(schema_path)
        self.schema: Optional[Dict[str, Any]] = None
        self._validator: Optional[Draft201909Validator] = None

        if not self.skip_validation:
            self._load_schema()

    def _resolve_schema_path(self, schema_path: Optional[Union[str, Path]]) -> Optional[Path]:
        if schema_path:
            p = Path(schema_path)
            if p.exists():
                return p.resolve()
            return p  # will error later with clearer message

        # schema shipped inside the package: works from any cwd and in a frozen app
        bundled = Path(__file__).resolve().parent / "schemas" / "dataset-json-v1.1.schema.json"
        if bundled.exists():
            return bundled

        cwd = Path.cwd()
        for rel in self.DEFAULT_SCHEMA_CANDIDATES:
            candidate = (cwd / rel).resolve()
            if candidate.exists():
                return candidate

        return None

    def _load_schema(self) -> None:
        if self.schema_path is None:
            raise FileNotFoundError(
                "Dataset-JSON schema not found. Provide schema_path or place it under "
                "dsjson/validation/schemas/ or demo/schema."
            )

        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {self.schema_path}")

        try:
            with open(self.schema_path, "r", encoding="utf-8") as f:
                self.schema = json.load(f)

            self._validator = Draft201909Validator(self.schema)
            logger.info("Schema loaded: %s", self.schema_path)

        except SchemaError as e:
            raise ValueError(f"Invalid JSON schema: {e}") from e

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def validate_dataset(
        self,
        dataset: Dict[str, Any],
        validate_rows: bool = True,
        strict_records_count: bool = True,
    ) -> ValidationReport:
        """Validate full Dataset-JSON (metadata + optional rows)."""
        if self.skip_validation:
            return ValidationReport(
                ok=True,
                schema_used=str(self.schema_path) if self.schema_path else "",
                validated_part="dataset",
                errors=[],
                warnings=[ValidationIssue(level="warning", message="Validation skipped by configuration")],
            )

        meta_report = self.validate_metadata(dataset)
        row_report = ValidationReport(ok=True, schema_used=meta_report.schema_used, validated_part="rows", errors=[], warnings=[])

        if validate_rows:
            row_report = self.validate_rows(dataset, strict_records_count=strict_records_count)

        errors = (meta_report.errors or []) + (row_report.errors or [])
        warnings = (meta_report.warnings or []) + (row_report.warnings or [])
        ok = (len(errors) == 0)

        return ValidationReport(
            ok=ok,
            schema_used=meta_report.schema_used,
            validated_part="dataset",
            errors=errors,
            warnings=warnings,
        )

    def validate_metadata(self, dataset: Dict[str, Any]) -> ValidationReport:
        """Validate top-level metadata using JSON Schema (rows optional)."""
        if self.skip_validation:
            return ValidationReport(
                ok=True,
                schema_used="",
                validated_part="metadata",
                errors=[],
                warnings=[ValidationIssue(level="warning", message="Validation skipped by configuration")],
            )

        issues = self._collect_schema_errors(dataset)
        warnings: List[ValidationIssue] = []
        warnings.extend(self._extra_metadata_checks(dataset))

        return ValidationReport(
            ok=(len(issues) == 0),
            schema_used=str(self.schema_path) if self.schema_path else "",
            validated_part="metadata",
            errors=issues,
            warnings=warnings,
        )

    def validate_rows(self, dataset: Dict[str, Any], strict_records_count: bool = True) -> ValidationReport:
        """Validate rows separately (shape + light type checks)."""
        errors: List[ValidationIssue] = []
        warnings: List[ValidationIssue] = []

        rows = dataset.get("rows", None)
        cols = dataset.get("columns", [])

        if rows is None:
            return ValidationReport(
                ok=True,
                schema_used=str(self.schema_path) if self.schema_path else "",
                validated_part="rows",
                errors=[],
                warnings=[ValidationIssue(level="warning", message="No rows present; row validation skipped")],
            )

        if not isinstance(rows, list):
            errors.append(ValidationIssue(level="error", message="rows must be an array (list of rows)", instance_path="/rows"))
            return ValidationReport(ok=False, schema_used=str(self.schema_path or ""), validated_part="rows", errors=errors, warnings=warnings)

        if not isinstance(cols, list) or len(cols) == 0:
            errors.append(ValidationIssue(level="error", message="columns must be a non-empty array when rows are present", instance_path="/columns"))
            return ValidationReport(ok=False, schema_used=str(self.schema_path or ""), validated_part="rows", errors=errors, warnings=warnings)

        col_count = len(cols)

        if strict_records_count:
            expected = dataset.get("records", None)
            if isinstance(expected, int) and expected != len(rows):
                errors.append(ValidationIssue(
                    level="error",
                    message=f"records ({expected}) does not match number of rows ({len(rows)})",
                    instance_path="/records",
                ))

        col_types = [(idx, c.get("name", f"col{idx}"), c.get("dataType")) for idx, c in enumerate(cols)]

        for r_i, row in enumerate(rows):
            if not isinstance(row, list):
                errors.append(ValidationIssue(level="error", message="Each row must be an array (list of values)", instance_path=f"/rows/{r_i}"))
                continue

            if len(row) != col_count:
                errors.append(ValidationIssue(
                    level="error",
                    message=f"Row length ({len(row)}) does not match columns length ({col_count})",
                    instance_path=f"/rows/{r_i}",
                ))
                continue

            for c_idx, c_name, c_type in col_types:
                v = row[c_idx]
                if v is None:
                    continue

                if c_type == "integer" and not isinstance(v, int):
                    warnings.append(ValidationIssue(
                        level="warning",
                        message=f"Value for {c_name} expected integer but got {type(v).__name__}",
                        instance_path=f"/rows/{r_i}/{c_idx}",
                    ))
                elif c_type in ("double", "float", "decimal") and not isinstance(v, (int, float)):
                    warnings.append(ValidationIssue(
                        level="warning",
                        message=f"Value for {c_name} expected numeric but got {type(v).__name__}",
                        instance_path=f"/rows/{r_i}/{c_idx}",
                    ))
                elif c_type == "boolean" and not isinstance(v, bool):
                    warnings.append(ValidationIssue(
                        level="warning",
                        message=f"Value for {c_name} expected boolean but got {type(v).__name__}",
                        instance_path=f"/rows/{r_i}/{c_idx}",
                    ))

        return ValidationReport(
            ok=(len(errors) == 0),
            schema_used=str(self.schema_path) if self.schema_path else "",
            validated_part="rows",
            errors=errors,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _collect_schema_errors(self, instance: Dict[str, Any]) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if self._validator is None:
            # should never happen unless skip_validation=True
            return issues

        for err in sorted(self._validator.iter_errors(instance), key=str):
            issues.append(ValidationIssue(
                level="error",
                message=err.message,
                instance_path=self._format_path(err.absolute_path),
                schema_path=self._format_path(err.absolute_schema_path),
                validator=str(err.validator),
                validator_value=err.validator_value,
            ))
        return issues

    def _extra_metadata_checks(self, dataset: Dict[str, Any]) -> List[ValidationIssue]:
        warnings: List[ValidationIssue] = []

        dt = dataset.get("datasetJSONCreationDateTime")
        if isinstance(dt, str) and dt and ("Z" not in dt) and ("+" not in dt) and ("-" not in dt[10:]):
            warnings.append(ValidationIssue(
                level="warning",
                message="datasetJSONCreationDateTime has no timezone offset/Z (allowed, but consider adding for clarity)",
                instance_path="/datasetJSONCreationDateTime",
            ))

        cols = dataset.get("columns", [])
        keyseq = []
        for c in cols:
            if isinstance(c, dict) and isinstance(c.get("keySequence"), int):
                keyseq.append(c["keySequence"])
        if len(keyseq) != len(set(keyseq)):
            warnings.append(ValidationIssue(
                level="warning",
                message="Duplicate keySequence values detected in columns",
                instance_path="/columns",
            ))

        return warnings

    @staticmethod
    def _format_path(path_obj) -> str:
        if not path_obj:
            return ""
        return "/" + "/".join([str(p) for p in path_obj])


def validate_dataset_json(
    dataset: Dict[str, Any],
    schema_path: Optional[Union[str, Path]] = None,
    skip_validation: bool = False,
    validate_rows: bool = True,
) -> Dict[str, Any]:
    """Convenience wrapper returning report as dict."""
    v = SchemaValidator(schema_path=schema_path, skip_validation=skip_validation)
    report = v.validate_dataset(dataset, validate_rows=validate_rows)
    return report.to_dict()