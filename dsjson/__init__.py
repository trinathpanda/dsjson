"""
dsjson
======

A submission-focused Python library and CLI tool for creating CDISC Dataset-JSON
from SDTM datasets and metadata.
"""

__version__ = "0.1.0"

from .services.conversion_service import ConversionService

__all__ = ["ConversionService"]