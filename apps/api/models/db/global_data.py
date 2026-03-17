"""
Modelos de base de datos para datos globales.
Son constantes que sirven para cualquier plan de negocio.
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Moneda(SQLModel, table=True):
    """
    Monedas disponibles para planes de negocio.

    Ejemplo: Boliviano (Bs), Dólar (USD)
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(unique=True, index=True)  # "BS", "USD"
    nombre: str = Field()  # "Boliviano"
    simbolo: str = Field()  # "Bs"
    es_default: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Impuesto(SQLModel, table=True):
    """
    Tipos de impuestos aplicables en planes.

    Ejemplo: IUE (25%), IT (3%)
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(unique=True, index=True)  # "IUE", "IT"
    nombre: str = Field()  # "Impuesto a las Utilidades"
    porcentaje: float = Field()  # 25.0
    descripcion: Optional[str] = Field(default=None)
    es_activo: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class Ciudad(SQLModel, table=True):
    """
    Ciudades disponibles para planes de negocio.

    Ejemplo: Santa Cruz de la Sierra, La Paz
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True)  # "Santa Cruz de la Sierra"
    departamento: str = Field()  # "Santa Cruz"
    pais: str = Field(default="Bolivia")
    codigo_postal: Optional[str] = Field(default=None)
    es_activo: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TipoCambio(SQLModel, table=True):
    """
    Histórico de tipos de cambio entre monedas.

    ejemplo: 1 USD = 6.96 Bs
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    moneda_origen_id: int = Field(foreign_key="moneda.id")
    moneda_destino_id: int = Field(foreign_key="moneda.id")
    valor: float = Field()  # 6.96
    fecha: datetime = Field(default_factory=datetime.utcnow, index=True)
    fuente: Optional[str] = Field(default="manual")  # "manual", "api"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IndicadorEconomico(SQLModel, table=True):
    """
    Indicadores económicos por país.

    ejemplo: Inflación, Tasa de interés
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    pais: str = Field(default="Bolivia", index=True)
    nombre: str = Field()  # "Inflación Anual"
    valor: float = Field()  # 2.0
    unidad: str = Field()  # "%"
    anio: int = Field(default=2025)
    es_activo: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
