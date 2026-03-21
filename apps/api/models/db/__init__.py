"""
Modelos de base de datos SQLModel.
"""

from .global_data import Moneda, Impuesto, Ciudad, TipoCambio, IndicadorEconomico
from .plan_data import (
    Plan,
    ParametrosGlobales,
    Producto,
    VersionPlan,
    EstadoPlan,
    DatosNegocio,
    BuyerPersona,
    ConfiguracionMetodologica,
)
from .trazabilidad import Auditoria, LogProcesamiento, TipoCambio as TipoCambioEnum
from .survey import Survey, SurveyResponse, SurveyVariable

__all__ = [
    # Datos globales
    "Moneda",
    "Impuesto",
    "Ciudad",
    "TipoCambio",
    "IndicadorEconomico",
    # Datos del plan
    "Plan",
    "ParametrosGlobales",
    "Producto",
    "VersionPlan",
    "EstadoPlan",
    # Datos específicos del plan (Sprint 1)
    "DatosNegocio",
    "BuyerPersona",
    "ConfiguracionMetodologica",
    # Trazabilidad
    "Auditoria",
    "LogProcesamiento",
    "TipoCambioEnum",
    # Encuestas (Sprint 2)
    "Survey",
    "SurveyResponse",
    "SurveyVariable",
]
