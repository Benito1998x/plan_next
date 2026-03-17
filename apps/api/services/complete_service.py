"""
Complete Service — Sprint 2.1: Pipeline unificado Sprint 1 + Sprint 2

Flujo:
  1. AI Agent extrae datos del cliente (nombre, rubro, productos)
  2. Sprint 1 → rellena plantilla Excel + genera Word con datos del plan
  3. Sprint 2 → Bronze→Silver→Gold desde Encuesta.xlsx
  4. Sprint 2.1 → el Word del plan se usa como base, se le agregan las 16 tablas

Output: un Excel (plan) + un Word unificado (plan + tabulación)
"""

import tempfile
from pathlib import Path
from typing import Dict, Optional

from database import get_database
from services.ai_agent import get_ai_agent
from services.excel_writer import ExcelWriter
from services.word_service import WordService
from services.pipeline.bronze import ingest_excel, extract_question_texts
from services.pipeline.silver import build_silver
from services.pipeline.gold import build_gold, load_gold_variables
from services.pipeline.writer import write_survey_to_word


def run_complete_pipeline(
    client_input: Dict,
    encuesta_path: Path,
    excel_template_path: Path,
    word_template_path: Path,
    output_dir: Path,
) -> Dict:
    """
    Pipeline unificado Sprint 1 + Sprint 2.

    Args:
        client_input      : datos del cliente (nombre, rubro, productos, etc.)
        encuesta_path     : ruta al Encuesta.xlsx
        excel_template_path: plantilla 1.xlsx (Sprint 1)
        word_template_path : plantilla 1.docx (Sprint 1 base Word)
        output_dir        : carpeta donde guardar los archivos generados

    Returns:
        {
            "plan_id"        : int (ID en SQLite del survey),
            "excel_path"     : str,
            "word_path"      : str (unificado plan + tabulación),
            "bronze_rows"    : int,
            "variable_names" : {1: "Edad", ...},
        }
    """
    get_database().create_tables()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── SPRINT 1: datos del plan ──────────────────────────────────────────────
    agent = get_ai_agent()
    plan_data  = agent.extract_plan_data(client_input)
    parametros = plan_data["parametros_globales"]
    productos  = plan_data["productos"]

    nombre_slug = parametros.get("nombre", "plan").replace(" ", "_").lower()

    # Sprint 1 — Excel
    excel_writer = ExcelWriter()
    excel_path   = output_dir / f"{nombre_slug}_plan.xlsx"
    excel_writer.fill_template(excel_template_path, excel_path, parametros, productos)

    # Sprint 1 — Word (intermediario: se usará como base para agregar las tablas)
    word_service     = WordService()
    word_sprint1_tmp = output_dir / f"{nombre_slug}_plan_solo.docx"
    word_service.generate_from_excel_data(parametros, productos, word_sprint1_tmp)

    # ── SPRINT 2: pipeline de encuesta ────────────────────────────────────────
    survey_id, df_raw = ingest_excel(encuesta_path, survey_name=nombre_slug)

    # Variables IA (con cache SQLite)
    variable_names = load_gold_variables(survey_id)
    if not variable_names:
        question_texts = extract_question_texts(df_raw)
        variable_names = agent.infer_variable_names(question_texts)

    silver = build_silver(df_raw)
    gold   = build_gold(silver, variable_names, survey_id=survey_id)

    # ── SPRINT 2.1: Word unificado ────────────────────────────────────────────
    # Usa el Word del Sprint 1 como base y agrega la sección de tabulación
    word_unified_path = output_dir / f"{nombre_slug}_completo.docx"
    write_survey_to_word(word_sprint1_tmp, gold, word_unified_path)

    # Limpiar Word intermedio
    word_sprint1_tmp.unlink(missing_ok=True)

    # Guardar índice plan_id → rutas (para que el endpoint de descarga encuentre los archivos)
    import json as _json
    index_path = output_dir / "index.json"
    index = _json.loads(index_path.read_text()) if index_path.exists() else {}
    index[str(survey_id)] = {
        "excel": str(excel_path),
        "word" : str(word_unified_path),
    }
    index_path.write_text(_json.dumps(index, indent=2))

    return {
        "plan_id"       : survey_id,
        "excel_path"    : str(excel_path),
        "word_path"     : str(word_unified_path),
        "bronze_rows"   : len(df_raw),
        "variable_names": variable_names,
        "parametros"    : parametros,
        "n_productos"   : len(productos),
    }
