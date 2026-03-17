"""
CAPA SILVER — Limpieza y tabulación con pandas

Responsabilidades:
- Eliminar prefijos de opción ("a) ", "b) ", "c) ", etc.)
- Normalizar texto (strip, NaN → None)
- Calcular frecuencia absoluta por pregunta (groupby + size)

La capa Silver NO infiere nombres de variables — eso es responsabilidad del agente IA.
La capa Silver devuelve los datos estructurados listos para Gold.
"""

import re
from typing import Dict, Any

import pandas as pd


# Regex para prefijos tipo "a) ", "b). ", "A) ", etc.
_OPTION_PREFIX = re.compile(r"^[a-zA-Z]\)\s*")


def clean_label(raw: str) -> str:
    """
    Elimina el prefijo de opción de una respuesta.

    "a) 18 a 30 Años"  → "18 a 30 Años"
    "b) Masculino"     → "Masculino"
    "c) Estudiante"    → "Estudiante"
    """
    if not raw or pd.isna(raw):
        return ""
    raw = str(raw).strip()
    return _OPTION_PREFIX.sub("", raw).strip()


def build_silver(df_raw: pd.DataFrame) -> Dict[str, Any]:
    """
    Transforma el DataFrame bruto en tablas de frecuencia por pregunta.

    Proceso:
    1. Detecta columnas de preguntas (formato "N. ¿texto?")
    2. Para cada pregunta:
       a. Elimina NaN y respuestas vacías
       b. Limpia prefijos de opción con clean_label()
       c. groupby + size → frecuencia absoluta
       d. Calcula frecuencia relativa (porcentaje)
       e. Preserva el orden original de las opciones (como aparecen en el Excel)

    Args:
        df_raw: DataFrame tal como lo retorna bronze.ingest_excel()

    Returns:
        {
            "total_responses": 320,
            "questions": {
                1: {
                    "col_name": "1. ¿Qué edad tiene?",
                    "texto_pregunta": "¿Qué edad tiene?",
                    "df_freq": DataFrame(label, frecuencia, porcentaje),
                    "total_valid": 320,
                },
                ...
            }
        }
    """
    import re as _re

    # Detectar columnas de preguntas
    q_cols: Dict[int, str] = {}
    for col in df_raw.columns:
        m = _re.match(r"^(\d+)\.\s+(.+)$", str(col).strip())
        if m:
            q_cols[int(m.group(1))] = col

    total_responses = len(df_raw)
    questions: Dict[int, Any] = {}

    for q_num in sorted(q_cols.keys()):
        col_name = q_cols[q_num]
        texto = _re.match(r"^\d+\.\s+(.+)$", col_name).group(1).strip()

        # Serie bruta sin NaN
        raw_series = df_raw[col_name].dropna().astype(str).str.strip()
        raw_series = raw_series[raw_series != ""]

        total_valid = len(raw_series)

        # Limpiar prefijos
        clean_series = raw_series.apply(clean_label)

        # Preservar orden de primera aparición usando value_counts(sort=False)
        # luego reordenamos por la letra de opción original (a, b, c...)
        freq = (
            raw_series
            .apply(clean_label)
            .value_counts(sort=False)
            .reset_index()
        )
        freq.columns = ["label", "frecuencia"]

        # Ordenar por primera letra de la respuesta original en el Excel
        # (preserva el orden a, b, c que viene del Google Form)
        order_map = {clean_label(v): i for i, v in enumerate(raw_series.unique())}
        freq["_order"] = freq["label"].map(lambda x: order_map.get(x, 999))
        freq = freq.sort_values("_order").drop(columns="_order").reset_index(drop=True)

        # Frecuencia relativa
        freq["porcentaje"] = freq["frecuencia"] / total_valid if total_valid > 0 else 0.0

        questions[q_num] = {
            "col_name": col_name,
            "texto_pregunta": texto,
            "df_freq": freq,
            "total_valid": total_valid,
        }

    return {
        "total_responses": total_responses,
        "questions": questions,
    }
