"""
CAPA GOLD — Datos listos para el reporte

Responsabilidades:
- Enriquecer Silver con nombres de variables (inferidos por IA)
- Formatear los datos para el writer (etiquetas, frecuencias, porcentajes)
- Cachear nombres de variables en SQLite (SurveyVariable)

La capa Gold es la última transformación antes de escribir el documento final.
"""

from pathlib import Path
from typing import Dict, Any, Optional

from sqlmodel import Session, select

from models.db.survey import SurveyVariable
from database import get_database


def build_gold(
    silver: Dict[str, Any],
    variable_names: Optional[Dict[int, str]] = None,
    survey_id: Optional[int] = None,
) -> Dict[int, Dict]:
    """
    Construye el layer Gold: datos listos para escribir en el Word.

    Args:
        silver: salida de silver.build_silver()
        variable_names: {1: "Edad", 2: "Género", ...} — inferidos por IA
        survey_id: si se provee, guarda los nombres en SQLite (cache)

    Returns:
        {
            1: {
                "variable": "Edad",
                "options": [
                    {"label": "18 a 30 Años", "freq": 130, "pct": 0.406},
                    ...
                ],
                "total": 320,
            },
            ...
        }
    """
    variable_names = variable_names or {}
    gold: Dict[int, Dict] = {}

    for q_num, q_data in silver["questions"].items():
        df = q_data["df_freq"]
        variable = variable_names.get(q_num, f"Variable {q_num}")

        options = [
            {
                "label": str(row["label"]),
                "freq": int(row["frecuencia"]),
                "pct": float(row["porcentaje"]),
            }
            for _, row in df.iterrows()
        ]

        gold[q_num] = {
            "variable": variable,
            "options": options,
            "total": q_data["total_valid"],
        }

    # Cachear en SQLite si se provee survey_id
    if survey_id is not None and variable_names:
        _save_variables(survey_id, silver, variable_names)

    return gold


def load_gold_variables(survey_id: int) -> Dict[int, str]:
    """
    Carga los nombres de variables cacheados en SQLite para un survey.

    Permite reutilizar inferencias IA sin llamar a la API de nuevo.

    Returns:
        {1: "Edad", 2: "Género", ...} o {} si no hay cache
    """
    db = get_database()
    with db.get_session() as session:
        stmt = select(SurveyVariable).where(SurveyVariable.survey_id == survey_id)
        variables = session.exec(stmt).all()
    return {
        v.pregunta_num: v.nombre_variable
        for v in variables
        if not v.nombre_variable.startswith("__bi__:")
    }


# ── helpers ────────────────────────────────────────────────────────────────

def _save_variables(survey_id: int, silver: Dict, variable_names: Dict[int, str]) -> None:
    """Guarda o actualiza los nombres de variables en SQLite."""
    db = get_database()
    with db.get_session() as session:
        # Evitar duplicados: eliminar existentes para este survey
        stmt = select(SurveyVariable).where(SurveyVariable.survey_id == survey_id)
        existing = session.exec(stmt).all()
        for v in existing:
            session.delete(v)
        session.commit()

        records = []
        for q_num, nombre in variable_names.items():
            q_data = silver["questions"].get(q_num)
            texto = q_data["texto_pregunta"] if q_data else f"Pregunta {q_num}"
            records.append(
                SurveyVariable(
                    survey_id=survey_id,
                    pregunta_num=q_num,
                    texto_pregunta=texto,
                    nombre_variable=nombre,
                )
            )
        session.add_all(records)
        session.commit()
