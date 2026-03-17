"""
Modelos de base de datos para datos específicos de cada plan.
"""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum


class EstadoPlan(str, Enum):
    """Estados posibles de un plan de negocio."""

    BORRADOR = "borrador"
    EN_PROCESO = "en_proceso"
    COMPLETADO = "completado"
    ARCHIVADO = "archivado"


class Plan(SQLModel, table=True):
    """
    Plan de negocio principal.

    Cada plan tiene sus parámetros globales y productos asociados.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True)  # "Shawarma Cruz"
    rubro: str = Field(index=True)  # "Restaurant"
    ciudad: str = Field()  # "Santa Cruz de la Sierra"
    departamento: str = Field()  # "Santa Cruz"
    estado: EstadoPlan = Field(default=EstadoPlan.BORRADOR)

    # Fechas de control
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    # Relaciones
    parametros: Optional["ParametrosGlobales"] = Relationship(back_populates="plan")
    productos: List["Producto"] = Relationship(back_populates="plan")
    versiones: List["VersionPlan"] = Relationship(back_populates="plan")


class ParametrosGlobales(SQLModel, table=True):
    """
    Parámetros globales específicos de cada plan.

    Completa los datos que el cliente no proporcionó con defaults.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="plan.id", unique=True)

    # Ubicación
    pais: str = Field(default="Bolivia")

    # Moneda
    moneda_codigo: str = Field(default="Bs")
    tipo_cambio_usd: float = Field(default=6.96)

    # Indicadores económicos
    tasa_inflacion_anual: float = Field(default=2.0)
    tasa_interes_promedio: float = Field(default=8.5)

    # Proyección
    horizonte_anios: int = Field(default=5)
    anio_base: int = Field(default=2025)
    anio_inicio_operaciones: int = Field(default=2026)

    # Impuestos
    impuesto_iue: float = Field(default=25.0)
    impuesto_it: float = Field(default=3.0)

    # Formato
    formato_fecha: str = Field(default="%d/%m/%Y")
    decimales_monetarios: int = Field(default=2)

    # Control
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    # Relación
    plan: Optional[Plan] = Relationship(back_populates="parametros")


class Producto(SQLModel, table=True):
    """
    Productos o servicios del plan de negocio.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="plan.id", index=True)
    numero: int = Field()  # Orden del producto (1, 2, 3...)
    nombre: str = Field()  # "Shawarma De Carne De Cordero"
    unidad_medida: str = Field(default="Gramos")
    peso_volumen: float = Field(default=125.0)  # Peso o volumen por unidad

    # Control
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relación
    plan: Optional[Plan] = Relationship(back_populates="productos")


class VersionPlan(SQLModel, table=True):
    """
    Versiones del plan para trazabilidad.

    Cada vez que se genera un Excel/Word, se guarda una versión.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="plan.id", index=True)
    numero_version: int = Field()  # 1, 2, 3...

    # Archivos generados
    archivo_excel: Optional[str] = Field(default=None)  # Path al archivo
    archivo_word: Optional[str] = Field(default=None)  # Path al archivo

    # Metadata
    datos_json: Optional[str] = Field(default=None)  # Snapshot de datos
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relación
    plan: Optional[Plan] = Relationship(back_populates="versiones")
