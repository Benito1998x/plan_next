"""
Excepciones personalizadas para el proyecto BPAE.

Jerarquía de excepciones:
    BPAEError (base)
    ├── ValidationError (datos inválidos)
    ├── ProcessingError (error de procesamiento)
    ├── TemplateError (error con plantillas)
    └── DatabaseError (error de base de datos)
"""

from typing import Optional, Any


class BPAEError(Exception):
    """
    Excepción base para todos los errores del proyecto BPAE.

    Todas las excepciones personalizadas heredan de esta clase.
    """

    def __init__(
        self, message: str, code: Optional[str] = None, details: Optional[dict] = None
    ):
        """
        Inicializa la excepción.

        Args:
            message: Mensaje de error descriptivo
            code: Código de error (ej: "VAL001", "TEMP001")
            details: Detalles adicionales del error
        """
        self.message = message
        self.code = code or "UNKNOWN"
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"[{self.code}] {self.message} - {self.details}"
        return f"[{self.code}] {self.message}"

    def to_dict(self) -> dict:
        """Convierte la excepción a diccionario para respuesta API."""
        return {"error": self.code, "message": self.message, "details": self.details}


class ValidationError(BPAEError):
    """
    Error de validación de datos.

    Se lanza cuando los datos de entrada no cumplen con los requisitos.

    Ejemplos:
        - Archivo Excel vacío
        - Campos obligatorios faltantes
        - Formato de dato incorrecto
    """

    def __init__(
        self,
        message: str = "Error de validación",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        code: Optional[str] = None,
    ):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(message=message, code=code or "VAL001", details=details)


class ProcessingError(BPAEError):
    """
    Error durante el procesamiento de archivos.

    Se lanza cuando hay un error al procesar Excel o Word.

    Ejemplos:
        - Error al leer Excel
        - Error al escribir Word
        - Error al generar plantilla
    """

    def __init__(
        self,
        message: str = "Error de procesamiento",
        file_name: Optional[str] = None,
        operation: Optional[str] = None,
        code: Optional[str] = None,
    ):
        details = {}
        if file_name:
            details["file"] = file_name
        if operation:
            details["operation"] = operation

        super().__init__(message=message, code=code or "PROC001", details=details)


class TemplateError(BPAEError):
    """
    Error con las plantillas Excel o Word.

    Se lanza cuando hay problemas con las plantillas.

    Ejemplos:
        - Plantilla no encontrada
        - Plantilla corrupta
        - Celda esperada no existe
    """

    def __init__(
        self,
        message: str = "Error con plantilla",
        template_name: Optional[str] = None,
        cell: Optional[str] = None,
        code: Optional[str] = None,
    ):
        details = {}
        if template_name:
            details["template"] = template_name
        if cell:
            details["cell"] = cell

        super().__init__(message=message, code=code or "TEMP001", details=details)


class DatabaseError(BPAEError):
    """
    Error de base de datos.

    Se lanza cuando hay problemas con SQLite/SQLModel.

    Ejemplos:
        - Error de conexión
        - Registro no encontrado
        - Violación de constraint
    """

    def __init__(
        self,
        message: str = "Error de base de datos",
        table: Optional[str] = None,
        operation: Optional[str] = None,
        code: Optional[str] = None,
    ):
        details = {}
        if table:
            details["table"] = table
        if operation:
            details["operation"] = operation

        super().__init__(message=message, code=code or "DB001", details=details)


# Códigos de error predefinidos
class ErrorCodes:
    """Códigos de error estándar."""

    # Validación (VALxxx)
    EMPTY_FILE = "VAL001"
    MISSING_FIELD = "VAL002"
    INVALID_FORMAT = "VAL003"
    INVALID_EXTENSION = "VAL004"
    FILE_TOO_LARGE = "VAL005"

    # Procesamiento (PROCxxx)
    EXCEL_READ_ERROR = "PROC001"
    EXCEL_WRITE_ERROR = "PROC002"
    WORD_GENERATION_ERROR = "PROC003"
    DATA_EXTRACTION_ERROR = "PROC004"

    # Plantillas (TEMPxxx)
    TEMPLATE_NOT_FOUND = "TEMP001"
    TEMPLATE_CORRUPTED = "TEMP002"
    MISSING_CELL = "TEMP003"
    INVALID_RANGE = "TEMP004"

    # Base de datos (DBxxx)
    CONNECTION_ERROR = "DB001"
    RECORD_NOT_FOUND = "DB002"
    CONSTRAINT_VIOLATION = "DB003"
    QUERY_ERROR = "DB004"
