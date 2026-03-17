"""
Modelos de base de datos para trazabilidad y auditoría.
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class TipoCambio(str, Enum):
    """Tipos de cambios registrados en auditoría."""

    CREACION = "creacion"
    ACTUALIZACION = "actualizacion"
    ELIMINACION = "eliminacion"
    VERSION = "version"


class Auditoria(SQLModel, table=True):
    """
    Registro de auditoría para cambios importantes.

    Mantiene trazabilidad de quién hizo qué y cuándo.
    """

    id: Optional[int] = Field(default=None, primary_key=True)

    # Qué tabla afectó
    tabla: str = Field(index=True)  # "plan", "producto", "parametros"
    registro_id: int = Field(index=True)  # ID del registro afectado

    # Qué cambió
    tipo_cambio: TipoCambio = Field()  # "creacion", "actualizacion", etc.
    datos_anteriores: Optional[str] = Field(default=None)  # JSON
    datos_nuevos: Optional[str] = Field(default=None)  # JSON

    # Quiéncambió
    usuario: Optional[str] = Field(default="sistema")  # Usuario o "sistema"

    # Cuándo cambió
    fecha: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Contexto adicional
    descripcion: Optional[str] = Field(default=None)


class LogProcesamiento(SQLModel, table=True):
    """
    Log de procesamiento de archivos Excel/Word.

    Registra cada vez que se procesa un archivo.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: Optional[int] = Field(default=None, foreign_key="plan.id")

    # Archivo procesado
    archivo_entrada: str = Field()  # Nombre del archivo Excel recibido
    archivo_salida_excel: Optional[str] = Field(default=None)
    archivo_salida_word: Optional[str] = Field(default=None)

    # Estado del procesamiento
    estado: str = Field(
        default="pendiente"
    )  # "pendiente", "procesando", "completado", "error"
    mensaje_error: Optional[str] = Field(default=None)

    # Tiempos
    inicio: datetime = Field(default_factory=datetime.utcnow)
    fin: Optional[datetime] = Field(default=None)

    # Duración en segundos
    duracion_segundos: Optional[float] = Field(default=None)
