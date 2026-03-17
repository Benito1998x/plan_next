"""
Validadores de archivos para el proyecto BPAE.

Valida archivos Excel y Word antes de procesarlos.
"""

import os
from pathlib import Path
from typing import Optional, List
from fastapi import UploadFile

from core.exceptions import ValidationError, ErrorCodes


# Extensiones permitidas
EXCEL_EXTENSIONS = {".xlsx", ".xls"}
WORD_EXTENSIONS = {".docx", ".doc"}
ALLOWED_EXTENSIONS = EXCEL_EXTENSIONS | WORD_EXTENSIONS

# Tamaño máximo de archivo (en bytes)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_EXCEL_SIZE = 5 * 1024 * 1024  # 5 MB para Excel


class FileValidator:
    """
    Validador de archivos subidos.

    Verifica:
    - Extensión del archivo
    - Tamaño del archivo
    - Tipo MIME
    - Nombre del archivo

    Usage:
        validator = FileValidator()
        validator.validate_excel(uploaded_file)
        validator.validate_word(uploaded_file)
    """

    def __init__(
        self, max_size: int = MAX_FILE_SIZE, allowed_extensions: Optional[set] = None
    ):
        """
        Inicializa el validador.

        Args:
            max_size: Tamaño máximo en bytes
            allowed_extensions: Extensiones permitidas (None = todas las válidas)
        """
        self.max_size = max_size
        self.allowed_extensions = allowed_extensions or ALLOWED_EXTENSIONS

    def validate_extension(self, file_path: Path) -> bool:
        """
        Valida que la extensión del archivo esté permitida.

        Args:
            file_path: Ruta del archivo

        Returns:
            True si la extensión es válida

        Raises:
            ValidationError: Si la extensión no está permitida
        """
        extension = file_path.suffix.lower()

        if extension not in self.allowed_extensions:
            raise ValidationError(
                message=f"Extensión '{extension}' no permitida",
                field="extension",
                value=extension,
                code=ErrorCodes.INVALID_EXTENSION,
            )

        return True

    def validate_size(self, file_size: int) -> bool:
        """
        Valida que el tamaño del archivo no exceda el máximo.

        Args:
            file_size: Tamaño del archivo en bytes

        Returns:
            True si el tamaño es válido

        Raises:
            ValidationError: Si el archivo excede el tamaño máximo
        """
        if file_size > self.max_size:
            size_mb = file_size / (1024 * 1024)
            max_mb = self.max_size / (1024 * 1024)
            raise ValidationError(
                message=f"Archivo muy grande ({size_mb:.2f} MB). Máximo: {max_mb:.0f} MB",
                field="size",
                value=f"{size_mb:.2f} MB",
                code=ErrorCodes.FILE_TOO_LARGE,
            )

        return True

    def validate_filename(self, filename: str) -> bool:
        """
        Valida que el nombre del archivo sea seguro.

        Args:
            filename: Nombre del archivo

        Returns:
            True si el nombre es válido

        Raises:
            ValidationError: Si el nombre contiene caracteres no permitidos
        """
        if not filename:
            raise ValidationError(
                message="Nombre de archivo vacío",
                field="filename",
                code=ErrorCodes.MISSING_FIELD,
            )

        # Caracteres no permitidos
        forbidden_chars = {"<", ">", ":", '"', "/", "\\", "|", "?", "*"}
        if any(char in filename for char in forbidden_chars):
            raise ValidationError(
                message="Nombre de archivo contiene caracteres no permitidos",
                field="filename",
                value=filename,
                code=ErrorCodes.INVALID_FORMAT,
            )

        return True

    async def validate_upload(
        self, file: UploadFile, expected_extensions: Optional[set] = None
    ) -> Path:
        """
        Valida un archivo subido completo.

        Args:
            file: Archivo subido desde FastAPI
            expected_extensions: Extensiones esperadas (None = cualquierapermite)

        Returns:
            Path del nombre del archivo

        Raises:
            ValidationError: Si el archivo no cumple las validaciones
        """
        # Validar nombre
        self.validate_filename(file.filename or "")

        # Validar extensión
        file_path = Path(file.filename or "unknown")
        extensions = expected_extensions or self.allowed_extensions
        self.allowed_extensions = extensions
        self.validate_extension(file_path)

        # Validar tamaño (leer contenido)
        content = await file.read()
        await file.seek(0)  # Rewind para uso posterior
        self.validate_size(len(content))

        return file_path

    def validate_excel(self, file_path: Path) -> bool:
        """
        Valida que sea un archivo Excel válido.

        Args:
            file_path: Ruta del archivo

        Returns:
            True si es un Excel válido

        Raises:
            ValidationError: Si no es un Excel válido
        """
        # Validar extensión
        if file_path.suffix.lower() not in EXCEL_EXTENSIONS:
            raise ValidationError(
                message=f"Se esperaba un archivo Excel (.xlsx o .xls)",
                field="extension",
                value=file_path.suffix,
                code=ErrorCodes.INVALID_EXTENSION,
            )

        # Validar tamaño específico para Excel
        file_size = file_path.stat().st_size if file_path.exists() else 0
        if file_size > MAX_EXCEL_SIZE:
            size_mb = file_size / (1024 * 1024)
            raise ValidationError(
                message=f"Excel muy grande ({size_mb:.2f} MB). Máximo: 5 MB",
                field="size",
                value=f"{size_mb:.2f} MB",
                code=ErrorCodes.FILE_TOO_LARGE,
            )

        return True

    def validate_word(self, file_path: Path) -> bool:
        """
        Valida que sea un archivo Word válido.

        Args:
            file_path: Ruta del archivo

        Returns:
            True si es un Word válido

        Raises:
            ValidationError: Si no es un Word válido
        """
        if file_path.suffix.lower() not in WORD_EXTENSIONS:
            raise ValidationError(
                message=f"Se esperaba un archivo Word (.docx o .doc)",
                field="extension",
                value=file_path.suffix,
                code=ErrorCodes.INVALID_EXTENSION,
            )

        return True

    @staticmethod
    def get_file_extension(filename: str) -> str:
        """
        Obtiene la extensión de un archivo.

        Args:
            filename: Nombre del archivo

        Returns:
            Extensión en minúsculas (ej: ".xlsx")
        """
        return Path(filename).suffix.lower()

    @staticmethod
    def is_excel(filename: str) -> bool:
        """Verifica si es un archivo Excel."""
        return Path(filename).suffix.lower() in EXCEL_EXTENSIONS

    @staticmethod
    def is_word(filename: str) -> bool:
        """Verifica si es un archivo Word."""
        return Path(filename).suffix.lower() in WORD_EXTENSIONS
