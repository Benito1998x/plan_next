"""
Core module - Utilidades base del proyecto BPAE.

Contiene:
- Excepciones personalizadas
- Validadores
- Utilidades comunes
"""

from .exceptions import (
    BPAEError,
    ValidationError,
    ProcessingError,
    TemplateError,
    DatabaseError,
    ErrorCodes,
)
from .validators import (
    FileValidator,
    EXCEL_EXTENSIONS,
    WORD_EXTENSIONS,
    MAX_FILE_SIZE,
    MAX_EXCEL_SIZE,
)

__all__ = [
    # Exceptions
    "BPAEError",
    "ValidationError",
    "ProcessingError",
    "TemplateError",
    "DatabaseError",
    "ErrorCodes",
    # Validators
    "FileValidator",
    "EXCEL_EXTENSIONS",
    "WORD_EXTENSIONS",
    "MAX_FILE_SIZE",
    "MAX_EXCEL_SIZE",
]
