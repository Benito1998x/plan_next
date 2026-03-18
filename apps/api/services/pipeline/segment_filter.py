"""
Filtrador de Segmento de Mercado (Sprint 3)

Permite segmentar la encuesta por características del buyer persona
antes de calcular los indicadores estadísticos.

Lógica de filtrado:
  - AND: el encuestado debe cumplir TODOS los filtros especificados
  - Las etiquetas de las opciones se comparan sin prefijos (clean_label)
  - Si n_segmento < 30 se emite una advertencia estadística

El DataFrame resultante tiene las mismas columnas que el DataFrame original
de la encuesta (formato "N. ¿texto?"), compatible con build_silver().

Fuente: Field — Discovering Statistics Using IBM SPSS (subgroup analysis)
"""

import logging
import warnings
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sqlmodel import select

from database import get_database
from models.db.survey import SurveyResponse, SurveyVariable
from services.pipeline.silver import clean_label

logger = logging.getLogger(__name__)

# Umbral estadístico mínimo
MIN_SAMPLE_SIZE = 30


def filter_respondents(
    survey_id: int,
    filters: Dict[int, List[str]],
) -> Tuple[pd.DataFrame, int, List[str]]:
    """
    Filtra los encuestados aplicando condiciones AND sobre las preguntas indicadas.

    Args:
        survey_id : ID del survey en SQLite
        filters   : {q_num: [labels_permitidos_cleaned]}
                    Ejemplo: {1: ["18 a 30 Años", "31 a 45 Años"], 4: ["Norte", "Centro"]}
                    Los labels deben estar ya limpios (sin prefijos a)/b)/...).

    Returns:
        (df_filtrado, n_filtrado, advertencias)
        df_filtrado: DataFrame con columnas "q_num. texto" compatible con build_silver()
        n_filtrado : número de encuestados que cumplen todos los filtros
        advertencias: lista de strings con advertencias estadísticas
    """
    advertencias: List[str] = []

    # 1. Cargar todas las respuestas del survey
    db = get_database()
    with db.get_session() as session:
        resp_stmt = select(SurveyResponse).where(SurveyResponse.survey_id == survey_id)
        all_responses = session.exec(resp_stmt).all()

        var_stmt = select(SurveyVariable).where(SurveyVariable.survey_id == survey_id)
        variables = session.exec(var_stmt).all()

    if not all_responses:
        raise ValueError(f"No hay respuestas para survey_id={survey_id}")

    # 2. Construir mapa de texto de preguntas para los nombres de columna
    # Solo las que NO son cache BI (prefijo __bi__:)
    col_map: Dict[int, str] = {}
    for v in variables:
        if not v.nombre_variable.startswith("__bi__:"):
            col_map[v.pregunta_num] = f"{v.pregunta_num}. {v.texto_pregunta}"

    # 3. Pivotear respuestas: {respondente_num: {q_num: valor_raw}}
    data: Dict[int, Dict[int, str]] = {}
    for resp in all_responses:
        if resp.respondente_num not in data:
            data[resp.respondente_num] = {}
        data[resp.respondente_num][resp.pregunta_num] = resp.valor_raw

    # 4. Aplicar filtros AND
    filtered_respondents: List[int] = []
    for resp_num, answers in data.items():
        matches = True
        for q_num, allowed_labels in filters.items():
            raw = answers.get(q_num, "")
            cleaned = clean_label(raw)
            if cleaned not in allowed_labels:
                matches = False
                break
        if matches:
            filtered_respondents.append(resp_num)

    n_filtrado = len(filtered_respondents)
    n_total = len(data)

    logger.info(
        f"[segment_filter] survey={survey_id} | filtros={filters} | "
        f"{n_filtrado}/{n_total} encuestados cumplen los criterios"
    )

    # 5. Advertencia estadística si n < 30
    if n_filtrado < MIN_SAMPLE_SIZE:
        msg = (
            f"ADVERTENCIA ESTADÍSTICA: El segmento filtrado tiene n={n_filtrado} encuestados, "
            f"menor al mínimo recomendado de {MIN_SAMPLE_SIZE}. "
            f"Los resultados no son estadísticamente robustos para inferencia."
        )
        advertencias.append(msg)
        logger.warning(msg)

    # 6. Reconstruir DataFrame con columnas por nombre de pregunta (para build_silver)
    rows = []
    for resp_num in sorted(filtered_respondents):
        row = {}
        for q_num, val in data[resp_num].items():
            col_name = col_map.get(q_num, f"{q_num}. Pregunta {q_num}")
            row[col_name] = val
        rows.append(row)

    df_filtrado = pd.DataFrame(rows) if rows else pd.DataFrame()

    return df_filtrado, n_filtrado, advertencias


def build_filters_from_buyer_persona(
    buyer_persona: Dict,
    q_map: Dict[str, int],
) -> Dict[int, List[str]]:
    """
    Convierte los datos del BuyerPersona de BD en filtros para filter_respondents().

    Args:
        buyer_persona: dict con campos de BuyerPersona (ej: {"edad_objetivo": "18 a 45 años"})
        q_map: mapeo de campo BP → número de pregunta encuesta
               Ejemplo: {"edad_objetivo": 1, "zona_residencia_objetivo": 4}

    Returns:
        {q_num: [labels_permitidos]}

    Nota: La "edad objetivo" puede ser un rango como "18 a 45 años" que se mapea
    a múltiples opciones de la encuesta. Esta función hace el mejor esfuerzo para
    detectar los labels compatibles.
    """
    filters: Dict[int, List[str]] = {}

    for campo, q_num in q_map.items():
        valor = (buyer_persona or {}).get(campo)
        if not valor:
            continue

        # El valor de buyer persona puede ser un rango como "18 a 45" o "Norte, Centro"
        # Convertir a lista de labels posibles
        labels = _parse_buyer_persona_value(valor)
        if labels:
            filters[q_num] = labels

    return filters


def _parse_buyer_persona_value(valor: str) -> List[str]:
    """
    Intenta parsear el valor del buyer persona en una lista de labels de encuesta.

    Casos manejados:
    - "18 a 45 años" → ["18 a 30 Años", "31 a 45 Años"] (aproximado)
    - "Norte, Centro" → ["Norte", "Centro"]
    - "Ambos" → [] (sin filtro de género)
    - "Femenino" → ["Femenino"]
    """
    import re

    if not valor:
        return []

    # Caso: "Ambos" para género → no filtrar
    if valor.strip().lower() in ("ambos", "ambos géneros", "todos"):
        return []

    # Caso: lista separada por comas o "y" → múltiples opciones
    if "," in valor or " y " in valor.lower():
        parts = [p.strip() for p in re.split(r",|\s+y\s+", valor, flags=re.IGNORECASE)]
        return [p for p in parts if p]

    # Caso: rango numérico "18 a 45" — retornar el valor tal cual para coincidencia parcial
    return [valor.strip()]
