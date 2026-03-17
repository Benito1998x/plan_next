"""
Modelos de base de datos SQLModel.
"""

from .global_data import Moneda, Impuesto, Ciudad, TipoCambio, IndicadorEconomico
from .plan_data import Plan, ParametrosGlobales, Producto, VersionPlan, EstadoPlan
from .trazabilidad import Auditoria, LogProcesamiento, TipoCambio
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
    # Trazabilidad
    "Auditoria",
    "LogProcesamiento",
    # Encuestas (Sprint 2)
    "Survey",
    "SurveyResponse",
    "SurveyVariable",
]
