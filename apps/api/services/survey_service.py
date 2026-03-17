"""
Survey Service — Orquesta el pipeline Bronze → Silver → Gold → Word

Punto de entrada único para el endpoint de encuestas.
Cada capa es independiente; este módulo las conecta.
"""

from pathlib import Path
from typing import Dict, Optional

from database import get_database
from services.pipeline.bronze import ingest_excel, extract_question_texts
from services.pipeline.silver import build_silver
from services.pipeline.gold import build_gold, load_gold_variables
from services.pipeline.writer import write_survey_to_word
from services.ai_agent import get_ai_agent


def run_pipeline(
    encuesta_path: Path,
    template_path: Path,
    output_path: Path,
    survey_name: Optional[str] = None,
) -> Dict:
    """
    Pipeline completo: Encuesta.xlsx → documento Word con 16 tablas de frecuencia.

    Flujo:
    1. Bronze : lee Excel, almacena raw en SQLite
    2. AI     : infiere nombres de variables (o reutiliza cache SQLite)
    3. Silver : limpia prefijos, calcula frecuencias con pandas groupby
    4. Gold   : enriquece con variables IA, formatea para el writer
    5. Writer : appenda seccion al Word template, guarda output

    Returns:
        {
            "survey_id"       : int,
            "bronze_rows"     : int,
            "silver_questions": int,
            "variable_names"  : {1: "Edad", ...},
            "word_path"       : str,
        }
    """
    # Garantizar tablas (idempotente — FastAPI lo hace en lifespan, scripts no)
    get_database().create_tables()

    # 1. BRONZE
    survey_id, df_raw = ingest_excel(encuesta_path, survey_name)

    # 2. AGENTE IA — nombres de variables (con cache SQLite)
    variable_names = load_gold_variables(survey_id)
    if not variable_names:
        question_texts = extract_question_texts(df_raw)
        agent = get_ai_agent()
        variable_names = agent.infer_variable_names(question_texts)

    # 3. SILVER
    silver = build_silver(df_raw)

    # 4. GOLD
    gold = build_gold(silver, variable_names, survey_id=survey_id)

    # 5. WRITER
    write_survey_to_word(template_path, gold, output_path)

    return {
        "survey_id"       : survey_id,
        "bronze_rows"     : len(df_raw),
        "silver_questions": len(silver["questions"]),
        "variable_names"  : variable_names,
        "word_path"       : str(output_path),
    }
