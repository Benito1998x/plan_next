"""
Clasificador Dinámico de Variables de Encuesta (Sprint 3)

Orquesta el análisis de variables usando el AIAgent:
  - Llama a ai_agent.analyze_survey_variables() con preguntas + opciones del Gold
  - Cachea la clasificación en SQLite (SurveyVariable, campo extendido)
  - Retorna el mapa de tipos y conversiones por pregunta

El sistema es DINÁMICO: no hay mapeos hardcodeados de "pregunta X es frecuencia".
El agente IA lee el texto de cada pregunta y sus opciones para decidir.
"""

import json
import logging
from typing import Dict, Any, Optional

from sqlmodel import select

from database import get_database
from models.db.survey import SurveyVariable
from services.pipeline.silver import clean_label

logger = logging.getLogger(__name__)

# Clave de campo adicional en SurveyVariable para cachear la clasificación
_CACHE_FIELD = "clasificacion_bi"  # se almacena en nombre_variable como JSON enriquecido


def classify_variables(
    silver: Dict[str, Any],
    gold_variables: Dict[int, str],
    survey_id: int,
    ai_agent,
) -> Dict[int, Dict[str, Any]]:
    """
    Clasifica cada variable de la encuesta dinámicamente via IA.

    Args:
        silver    : salida de build_silver() — contiene texto de pregunta y opciones
        gold_variables: {q_num: "nombre_variable"} ya inferidos por IA (puede estar vacío)
        survey_id : para cachear en SQLite
        ai_agent  : instancia de AIAgent

    Returns:
        {
            q_num: {
                "variable":      str,
                "tipo":          str,   # nominal/ordinal/ordinal_likert/cuantitativa
                "conversiones":  dict | None,
                "unidad":        str | None,
                "interpretacion": str,
            }
        }
    """
    # Intentar cargar desde cache primero
    cached = _load_cache(survey_id)
    if cached:
        logger.info(f"[classify_variables] Cache hit: {len(cached)} variables para survey {survey_id}")
        return cached

    # Construir input para el agente: {q_num: {texto_pregunta, opciones}}
    questions_input: Dict[int, Dict] = {}
    for q_num, q_data in silver["questions"].items():
        df_freq = q_data["df_freq"]
        opciones = df_freq["label"].tolist()  # ya sin prefijos (silver limpia esto)
        questions_input[q_num] = {
            "texto_pregunta": q_data["texto_pregunta"],
            "opciones": opciones,
        }

    logger.info(f"[classify_variables] Llamando al agente IA para {len(questions_input)} variables...")
    classification = ai_agent.analyze_survey_variables(questions_input)

    # Fusionar nombres de variable del Gold (si existen) con la clasificación
    for q_num, cls in classification.items():
        if q_num in gold_variables and gold_variables[q_num]:
            cls["variable"] = gold_variables[q_num]

    # Guardar en cache
    _save_cache(survey_id, classification)
    logger.info(f"[classify_variables] Clasificación guardada para survey {survey_id}")

    return classification


def load_cached_classification(survey_id: int) -> Optional[Dict[int, Dict[str, Any]]]:
    """Carga la clasificación cacheada desde SQLite. Retorna None si no existe."""
    return _load_cache(survey_id)


# ── helpers de cache ──────────────────────────────────────────────────────────

def _load_cache(survey_id: int) -> Optional[Dict[int, Dict]]:
    """
    Lee la clasificación BI desde SurveyVariable.
    La clasificación se guarda serializada en el campo nombre_variable
    cuando empieza con el prefijo "__bi__:".
    """
    db = get_database()
    with db.get_session() as session:
        stmt = (
            select(SurveyVariable)
            .where(SurveyVariable.survey_id == survey_id)
            .where(SurveyVariable.nombre_variable.startswith("__bi__:"))
        )
        rows = session.exec(stmt).all()

    if not rows:
        return None

    result = {}
    for row in rows:
        try:
            payload = json.loads(row.nombre_variable.removeprefix("__bi__:"))
            result[row.pregunta_num] = payload
        except (json.JSONDecodeError, ValueError):
            continue
    return result if result else None


def _save_cache(survey_id: int, classification: Dict[int, Dict]) -> None:
    """
    Guarda la clasificación BI en SurveyVariable con prefijo "__bi__:".
    Elimina entradas anteriores antes de guardar.
    """
    db = get_database()
    with db.get_session() as session:
        # Eliminar cache anterior
        stmt = (
            select(SurveyVariable)
            .where(SurveyVariable.survey_id == survey_id)
            .where(SurveyVariable.nombre_variable.startswith("__bi__:"))
        )
        existing = session.exec(stmt).all()
        for row in existing:
            session.delete(row)
        session.commit()

        # Insertar nuevas entradas
        records = []
        for q_num, cls in classification.items():
            records.append(
                SurveyVariable(
                    survey_id=survey_id,
                    pregunta_num=q_num,
                    texto_pregunta=cls.get("interpretacion", f"Variable {q_num}"),
                    nombre_variable="__bi__:" + json.dumps(cls, ensure_ascii=False),
                )
            )
        session.add_all(records)
        session.commit()
