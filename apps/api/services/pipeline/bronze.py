"""
CAPA BRONZE — Ingesta de datos brutos

Responsabilidades:
- Leer Encuesta.xlsx con pandas (sin transformar nada)
- Almacenar cada respuesta en SQLite (Survey + SurveyResponse)
- Exponer funciones para cargar los datos brutos desde SQLite como DataFrame

Regla de oro: Bronze NUNCA modifica los datos. Lo que entra, sale igual.
"""

import re
import sys
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
from sqlmodel import Session, select

# Asegurar que el proyecto esté en el path cuando se ejecuta desde el notebook
_API_ROOT = Path(__file__).parent.parent.parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from database import get_database
from models.db.survey import Survey, SurveyResponse


def ingest_excel(file_path: Path, survey_name: str = None) -> Tuple[int, pd.DataFrame]:
    """
    Lee Encuesta.xlsx, almacena datos brutos en SQLite, retorna (survey_id, DataFrame).

    El DataFrame retornado tiene las columnas originales del Excel:
        ['Marca temporal', '1. ¿Qué edad tiene?', '2. ¿Cuál es su género?', ...]

    Args:
        file_path: ruta al archivo Encuesta.xlsx
        survey_name: nombre descriptivo. Si None, usa el nombre del archivo.

    Returns:
        (survey_id, df_raw) — survey_id para referenciar en SQLite, df_raw para el pipeline
    """
    survey_name = survey_name or Path(file_path).stem

    # Leer Excel sin transformar (engine openpyxl para .xlsx)
    df_raw = pd.read_excel(file_path, engine="openpyxl")

    # Filtrar filas completamente vacías
    df_raw = df_raw.dropna(how="all").reset_index(drop=True)

    total = len(df_raw)

    db = get_database()
    with db.get_session() as session:
        survey = Survey(
            nombre=survey_name,
            archivo_origen=str(file_path),
            total_respondentes=total,
        )
        session.add(survey)
        session.commit()
        session.refresh(survey)
        survey_id = survey.id

        # Almacenar respuesta por pregunta (columnas numeradas)
        q_cols = _find_question_columns(df_raw)
        records = []
        for row_idx, row in df_raw.iterrows():
            for q_num, col_name in q_cols.items():
                valor = row[col_name]
                if pd.notna(valor) and str(valor).strip():
                    records.append(
                        SurveyResponse(
                            survey_id=survey_id,
                            respondente_num=int(row_idx) + 1,
                            pregunta_num=q_num,
                            valor_raw=str(valor).strip(),
                        )
                    )

        session.add_all(records)
        session.commit()

    return survey_id, df_raw


def load_bronze_df(survey_id: int) -> pd.DataFrame:
    """
    Carga los datos brutos de SQLite como DataFrame pivotado.

    Retorna: DataFrame con columnas p1, p2, ..., pN (una por pregunta)
    e índice = respondente_num.

    Útil para re-procesar sin releer el Excel original.
    """
    db = get_database()
    with db.get_session() as session:
        stmt = select(SurveyResponse).where(SurveyResponse.survey_id == survey_id)
        responses = session.exec(stmt).all()

    if not responses:
        return pd.DataFrame()

    data: Dict = {}
    for resp in responses:
        if resp.respondente_num not in data:
            data[resp.respondente_num] = {}
        data[resp.respondente_num][f"p{resp.pregunta_num}"] = resp.valor_raw

    df = pd.DataFrame.from_dict(data, orient="index")
    df.index.name = "respondente_num"
    return df.sort_index()


def load_bronze_df_named(survey_id: int) -> pd.DataFrame:
    """
    Carga los datos brutos de SQLite como DataFrame con columnas "N. texto_pregunta".

    A diferencia de load_bronze_df() (que usa columnas "p1..pN"),
    esta función reconstruye los nombres de columna desde SurveyVariable,
    retornando un DataFrame compatible con build_silver().

    Retorna DataFrame con columnas "1. ¿Qué edad tiene?", "2. ¿Cuál es su género?", ...
    """
    from models.db.survey import SurveyVariable

    db = get_database()
    with db.get_session() as session:
        resp_stmt = select(SurveyResponse).where(SurveyResponse.survey_id == survey_id)
        responses = session.exec(resp_stmt).all()

        var_stmt = select(SurveyVariable).where(SurveyVariable.survey_id == survey_id)
        variables = session.exec(var_stmt).all()

    if not responses:
        return pd.DataFrame()

    # Mapeo q_num → "N. texto_pregunta" (excluir entradas __bi__:)
    col_map: Dict[int, str] = {
        v.pregunta_num: f"{v.pregunta_num}. {v.texto_pregunta}"
        for v in variables
        if not v.nombre_variable.startswith("__bi__:")
    }

    data: Dict = {}
    for resp in responses:
        if resp.respondente_num not in data:
            data[resp.respondente_num] = {}
        col_name = col_map.get(resp.pregunta_num, f"{resp.pregunta_num}. Pregunta {resp.pregunta_num}")
        data[resp.respondente_num][col_name] = resp.valor_raw

    df = pd.DataFrame.from_dict(data, orient="index")
    df.index.name = "respondente_num"
    return df.sort_index()


def extract_question_texts(df_raw: pd.DataFrame) -> Dict[int, str]:
    """
    Extrae el texto de las preguntas desde los headers del DataFrame.

    "1. ¿Qué edad tiene?" → {1: "¿Qué edad tiene?"}

    Args:
        df_raw: DataFrame tal como lo retorna ingest_excel()

    Returns:
        dict {pregunta_num: texto_pregunta}
    """
    texts: Dict[int, str] = {}
    for col in df_raw.columns:
        m = re.match(r"^(\d+)\.\s+(.+)$", str(col).strip())
        if m:
            texts[int(m.group(1))] = m.group(2).strip()
    return texts


# ── helpers ────────────────────────────────────────────────────────────────

def _find_question_columns(df: pd.DataFrame) -> Dict[int, str]:
    """Retorna {q_num: col_name} para las columnas de preguntas numeradas."""
    result: Dict[int, str] = {}
    for col in df.columns:
        m = re.match(r"^(\d+)\.\s+", str(col))
        if m:
            result[int(m.group(1))] = col
    return result
