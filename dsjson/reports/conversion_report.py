"""Conversion report generation."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class ConversionReport:
    """Collect and write conversion results."""
    results: List[Dict] = field(default_factory=list)

    def add_result(self, domain: str, status: str, message: str = "") -> None:
        self.results.append({
            "domain": domain,
            "status": status,
            "message": message,
        })

    def to_dict(self) -> Dict:
        return {
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for item in self.results if item["status"] == "PASS"),
                "failed": sum(1 for item in self.results if item["status"] == "FAIL"),
                "pending": sum(1 for item in self.results if item["status"] == "PENDING"),
            },
            "results": self.results,
        }

    def write_json(self, path: str) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
