"""Custom exceptions for the dsjson package (Final Professional Version)."""

from typing import Optional, List


# ---------------------------------------------------------------------
# Base Exception
# ---------------------------------------------------------------------
class DSJSONError(Exception):
    """Base exception for all dsjson errors."""

    def __init__(self, message: str = "An error occurred", details: Optional[dict] = None):
        super().__init__(message)
        self.details = details or {}


# ---------------------------------------------------------------------
# Configuration / CLI exceptions
# ---------------------------------------------------------------------
class DSJSONConfigurationError(DSJSONError):
    """Raised when CLI arguments or configuration is invalid."""


class UnsupportedFileTypeError(DSJSONError):
    """Raised when an unsupported file type is provided."""

    def __init__(self, file_type: str):
        super().__init__(f"Unsupported file type: {file_type}")


class DomainNotFoundError(DSJSONError):
    """Raised when the requested domain is missing."""

    def __init__(self, domain: str):
        super().__init__(f"Domain not found: {domain}")


# ---------------------------------------------------------------------
# Dataset reading exceptions
# ---------------------------------------------------------------------
class DatasetReadError(DSJSONError):
    def __init__(self, file_path: str, message: str = "Dataset read failed"):
        super().__init__(f"{message}: {file_path}")


class DatasetEmptyError(DSJSONError):
    """Raised when input dataset is empty."""

    def __init__(self, dataset_name: str):
        super().__init__(f"Dataset is empty: {dataset_name}")


class DatasetColumnMismatchError(DSJSONError):
    """Raised when dataset columns mismatch metadata."""

    def __init__(self, message: str):
        super().__init__(f"Column mismatch: {message}")


# ---------------------------------------------------------------------
# Metadata exceptions
# ---------------------------------------------------------------------
class MetadataExtractionError(DSJSONError):
    """Raised when metadata extraction fails."""


class DefineXMLParseError(MetadataExtractionError):
    def __init__(self, file_path: str, details: str):
        super().__init__(f"Failed to parse Define-XML: {file_path} -> {details}")


class DefineXMLDomainNotFoundError(MetadataExtractionError):
    def __init__(self, domain: str):
        super().__init__(f"Domain not found in Define-XML: {domain}")


class DefineXMLVariableNotFoundError(MetadataExtractionError):
    def __init__(self, variable: str):
        super().__init__(f"Variable not found in Define-XML: {variable}")


class SpecificationFileError(MetadataExtractionError):
    def __init__(self, file_path: str):
        super().__init__(f"Specification file error: {file_path}")


class MetadataInferenceError(MetadataExtractionError):
    def __init__(self, dataset_name: str):
        super().__init__(f"Metadata inference failed for dataset: {dataset_name}")


class MetadataValidationError(MetadataExtractionError):
    def __init__(self, message: str):
        super().__init__(f"Invalid metadata: {message}")


# ---------------------------------------------------------------------
# Dataset-JSON build exceptions
# ---------------------------------------------------------------------
class DatasetJSONBuildError(DSJSONError):
    def __init__(self, dataset_name: str, details: str):
        super().__init__(f"Failed to build Dataset-JSON for {dataset_name}: {details}")


class DatasetJSONWriteError(DSJSONError):
    def __init__(self, file_path: str):
        super().__init__(f"Failed to write Dataset-JSON: {file_path}")


class DatasetJSONReadError(DSJSONError):
    def __init__(self, file_path: str):
        super().__init__(f"Failed to read Dataset-JSON: {file_path}")


# ---------------------------------------------------------------------
# Validation exceptions
# ---------------------------------------------------------------------
class SchemaValidationError(DSJSONError):
    def __init__(self, dataset_name: str, errors: Optional[List[str]] = None):
        self.dataset_name = dataset_name
        self.errors = errors or []

        message = f"Schema validation failed for {dataset_name}"
        if self.errors:
            message += f" ({len(self.errors)} errors)"

        super().__init__(message)


class SchemaLoadError(SchemaValidationError):
    def __init__(self, schema_path: str):
        super().__init__("SCHEMA", [])
        self.details = {"schema_path": schema_path}


class ValidationReportError(DSJSONError):
    def __init__(self, dataset_name: str):
        super().__init__(f"Failed to create validation report for {dataset_name}")