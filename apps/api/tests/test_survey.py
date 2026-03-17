"""
Test manual del pipeline de encuesta.

Prueba el flujo completo:
  POST /api/v1/process-survey  ->  genera tabulacion.xlsx con KPIs
  GET  /api/v1/download/survey/{id}/excel

Ejecutar desde apps/api/:
  ../../venv/Scripts/python tests/test_survey.py
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Carpetas de plantillas
_PLANTILLAS = Path(__file__).parent.parent.parent.parent / "plantillas"
ENCUESTA_PATH   = _PLANTILLAS / "excel" / "fase 2" / "Encuesta.xlsx"
TEMPLATE2_PATH  = _PLANTILLAS / "excel" / "fase 2" / "plantilla 2.xlsx"
OUTPUT_DIR      = _PLANTILLAS / "excel" / "fase 2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def sep(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────

def test_health():
    sep("1. Health Check")
    r = client.get("/health")
    print(f"  Status: {r.status_code}  Body: {r.json()}")
    assert r.status_code == 200
    print("  OK")


def test_process_survey_default():
    """Usa la Encuesta.xlsx que ya existe en plantillas/excel/ (sin subir archivo)."""
    sep("2. POST /process-survey — encuesta por defecto")

    if not ENCUESTA_PATH.exists():
        print(f"  No existe {ENCUESTA_PATH}, skipping")
        return None

    r = client.post("/api/v1/process-survey")
    print(f"  Status: {r.status_code}")

    if r.status_code != 200:
        print(f"  Error: {r.text[:300]}")
        return None

    data = r.json()["data"]
    print(f"  survey_id:          {data['survey_id']}")
    print(f"  bronze_rows:        {data['bronze_rows']}")
    print(f"  silver_questions:   {data['silver_questions']}")
    print(f"  excel_url:          {data['excel_url']}")

    variable_names = data.get("variable_names", {})
    print(f"\n  -- Variables inferidas por IA ({len(variable_names)}) --")
    for num, var in sorted(variable_names.items(), key=lambda x: int(x[0])):
        print(f"  P{str(num):>2}: {var}")

    assert data["bronze_rows"] > 0,      "No se cargaron filas del Excel"
    assert data["silver_questions"] > 0, "No se procesaron preguntas"
    print("\n  OK - pipeline ejecutado")
    return data["survey_id"]


def test_process_survey_upload():
    """Sube Encuesta.xlsx explicitamente como archivo."""
    sep("3. POST /process-survey — subiendo archivo")

    if not ENCUESTA_PATH.exists():
        print(f"  No existe {ENCUESTA_PATH}, skipping")
        return None

    with open(ENCUESTA_PATH, "rb") as f:
        r = client.post(
            "/api/v1/process-survey",
            files={"file": ("Encuesta.xlsx", f,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )

    print(f"  Status: {r.status_code}")
    assert r.status_code == 200, f"Error: {r.text[:300]}"
    data = r.json()["data"]
    print(f"  survey_id:        {data['survey_id']}")
    print(f"  bronze_rows:      {data['bronze_rows']}")
    assert data["bronze_rows"] > 0
    print("  OK - upload funciona")
    return data["survey_id"]


def test_download_survey(survey_id: int):
    """Descarga el Excel generado y verifica su estructura."""
    sep(f"4. GET /download/survey/{survey_id}/excel")

    r = client.get(f"/api/v1/download/survey/{survey_id}/excel")
    print(f"  Status: {r.status_code}")
    assert r.status_code == 200, f"Error: {r.text}"
    assert "spreadsheetml" in r.headers["content-type"]

    out_path = OUTPUT_DIR / f"tabulacion_{survey_id}.xlsx"
    out_path.write_bytes(r.content)
    print(f"  Guardado en: {out_path}")

    # Verificar estructura del archivo
    from openpyxl import load_workbook
    wb = load_workbook(out_path, data_only=True)

    print(f"  Hojas: {wb.sheetnames}")
    assert "Tabulación" in wb.sheetnames, "Falta hoja Tabulacion"
    # KPIs se agregan en Sprint 4

    ws = wb["Tabulación"]
    print(f"  Tabulacion: {ws.max_row} filas x {ws.max_column} columnas")

    # Primera celda con datos deberia ser Cuadro 1
    first_cell = ws.cell(4, 2).value
    print(f"  Primera celda (B4): {first_cell}")
    assert first_cell is not None, "La hoja Tabulacion esta vacia"

    print(f"  Hojas disponibles: {wb.sheetnames}")

    wb.close()
    print("  OK - estructura correcta")


def test_silver_direct():
    """Prueba directa del pipeline Silver (sin HTTP) para ver datos calculados."""
    sep("5. Test directo — Bronze + Silver")

    if not ENCUESTA_PATH.exists():
        print(f"  No existe {ENCUESTA_PATH}, skipping")
        return

    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services.survey_service import load_bronze, build_silver

    bronze = load_bronze(ENCUESTA_PATH)
    print(f"  Bronze: {len(bronze)} filas")
    if bronze:
        print(f"  Columnas: {list(bronze[0].keys())[:5]}...")

    silver = build_silver(bronze)
    print(f"  Silver: {len(silver['questions'])} preguntas procesadas")

    for q_num, q_data in list(silver["questions"].items())[:3]:
        print(f"\n  P{q_num}: {q_data['variable']}")
        print(f"    valid_n: {q_data['valid_n']}")
        for opt in q_data["options"][:4]:
            print(f"    {opt['label'][:30]:30s} | {opt['freq']:4d} | {opt['pct']*100:5.1f}%")
        if len(q_data["options"]) > 4:
            print(f"    ... ({len(q_data['options'])} opciones total)")

    assert silver["total_responses"] > 0
    print("\n  OK")


if __name__ == "__main__":
    print("\n=== Test Survey Pipeline BPAE ===")
    print(f"  Encuesta:  {ENCUESTA_PATH}")
    print(f"  Plantilla: {TEMPLATE2_PATH}")

    try:
        test_health()
        test_silver_direct()
        survey_id = test_process_survey_default()
        if survey_id:
            test_download_survey(survey_id)
        test_process_survey_upload()

        sep("RESULTADO FINAL")
        print("  Todos los tests pasaron")
        print(f"  Archivos generados en: {OUTPUT_DIR}")

    except AssertionError as e:
        print(f"\n  FALLO: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n  ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
