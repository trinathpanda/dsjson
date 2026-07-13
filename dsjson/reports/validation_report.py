"""Validation Report Generator for dsjson."""

from datetime import datetime
from typing import Dict


class ValidationReportBuilder:
    """Build structured validation report."""

    @staticmethod
    def build(
        dataset_name: str,
        full_report,
        metadata_report,
        row_report
    ) -> Dict:
        """Create final validation report."""

        def count_issues(report):
            return len(report.errors or []), len(report.warnings or [])

        total_errors, total_warnings = count_issues(full_report)

        report = {
            "dataset": dataset_name,
            "status": "PASS" if full_report.ok else "FAIL",
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),

            "summary": {
                "errors": total_errors,
                "warnings": total_warnings
            },

            "metadata": {
                "status": "PASS" if metadata_report.ok else "FAIL",
                "errors": [e.message for e in metadata_report.errors],
                "warnings": [w.message for w in metadata_report.warnings]
            },

            "rows": {
                "status": "PASS" if row_report.ok else "FAIL",
                "errors": [
                    {"message": e.message, "path": e.instance_path}
                    for e in row_report.errors
                ],
                "warnings": [
                    {"message": w.message, "path": w.instance_path}
                    for w in row_report.warnings
                ]
            }
        }

        return report