"""Base reader contracts."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import pandas as pd


@dataclass
class DatasetReadResult:
    """Standard output from dataset readers."""
    dataframe: pd.DataFrame
    dataset_name: str
    dataset_label: Optional[str] = None
    variable_labels: Dict[str, str] = field(default_factory=dict)
    source_metadata: Dict[str, Any] = field(default_factory=dict)
