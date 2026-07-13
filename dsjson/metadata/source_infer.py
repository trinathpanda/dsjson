"""Fallback metadata inference from source datasets."""

from typing import List, Dict

import pandas as pd


def infer_column_metadata(df: pd.DataFrame, domain: str) -> List[Dict]:
    """Infer basic Dataset-JSON column metadata from a pandas DataFrame."""
    columns = []
    for order, column in enumerate(df.columns, start=1):
        series = df[column].dropna()
        if pd.api.types.is_integer_dtype(series):
            data_type = "integer"
        elif pd.api.types.is_float_dtype(series):
            data_type = "double"
        else:
            data_type = "string"

        columns.append({
            "itemOID": f"IT.{domain.upper()}.{column}",
            "name": column,
            "label": column,
            "dataType": data_type,
            "targetDataType": data_type,
            "length": None,
            "displayFormat": None,
            "keySequence": None,
        })
    return columns
