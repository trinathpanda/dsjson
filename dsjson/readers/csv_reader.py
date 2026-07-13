"""CSV reader for SDTM datasets."""

from pathlib import Path

import pandas as pd

from .base import DatasetReadResult


def read_csv_dataset(file_path: str) -> DatasetReadResult:
    """Read a CSV dataset into a standard DatasetReadResult."""
    path = Path(file_path)
    df = pd.read_csv(path)
    return DatasetReadResult(
        dataframe=df,
        dataset_name=path.stem.upper(),
        dataset_label=path.stem.upper(),
        variable_labels={col: col for col in df.columns},
        source_metadata={"source_type": "csv", "source_path": str(path)},
    )
