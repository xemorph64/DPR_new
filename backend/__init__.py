"""
Backend __init__.py for package initialization.
"""

__version__ = "1.0.0"
__author__ = "DPR Compliance Team"

from .services import (
    initialize_ocr,
    initialize_rag,
    process_dpr_file,
    get_job_status,
)

__all__ = [
    "initialize_ocr",
    "initialize_rag",
    "process_dpr_file",
    "get_job_status",
]
