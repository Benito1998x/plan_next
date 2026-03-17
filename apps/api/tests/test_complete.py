"""
Test Sprint 2.1 — Pipeline unificado Plan de negocio + Tabulación

Valida:
  1. Service directo : run_complete_pipeline() genera Excel + Word unificado
  2. API             : POST /process-complete retorna excel_url + word_url
  3. Descargas       : ambos archivos descargables y válidos
  4. Integridad Word : contiene secciones de Sprint 1 (datos globales) y Sprint 2 (cuadros)

Ejecutar desde apps/api/:
  ../../venv/Scripts/python -X utf8 tests/test_complete.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

_PLANTILLAS       = Path(__file__).parent.parent.parent.parent / "plantillas"
EXCEL_TEMPLATE    = _PLANTILLAS / "excel" / "fase 1" / "plantilla 1.xlsx"
WORD_TEMPLATE     = _PLANTILLAS / "word"  / "fase 1" / "plantilla 1.docx"
ENCUESTA_PATH     = _PLANTILLAS / "excel" / "fase 2" / "Encuesta.xlsx"
OUTPUT_WORD       = _PLANTILLAS / "word"  / "fase 2"

CLIENT_INPUT = {
    "nombre"      : "Shawarma Cruz Test",
    "rubro"       : "Gastronomía",
    "descripcion" : "Restaurante de shawarma en Santa Cruz de la Sierra",
    "num_productos": 3,
}


def sep(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


def ok(msg=""):
    print(f"  OK {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Service directo
# ─────────────────────────────────────────────────────────────────────────────

def test_service_direct():
    sep("1. SERVICE — run_complete_pipeline() directo")

    for path, name in [(EXCEL_TEMPLATE, "plantilla 1.xlsx"), (WORD_TEMPLATE, "plantilla 1.docx"), (ENCUESTA_PATH, "Encuesta.xlsx")]:
        assert path.exists(), f"Falta: {name} → {path}"

    from services.complete_service import run_complete_pipeline
    import tempfile

    output_dir = Path(tempfile.gettempdir()) / "bpae" / "test_complete"
    result = run_complete_pipeline(
        client_input=CLIENT_INPUT,
        encuesta_path=ENCUESTA_PATH,
        excel_template_path=EXCEL_TEMPLATE,
        word_template_path=WORD_TEMPLATE,
        output_dir=output_dir,
    )

    print(f"  plan_id        : {result['plan_id']}")
    print(f"  nombre         : {result['parametros'].get('nombre')}")
    print(f"  n_productos    : {result['n_productos']}")
    print(f"  bronze_rows    : {result['bronze_rows']}")
    print(f"  excel_path     : {Path(result['excel_path']).name}")
    print(f"  word_path      : {Path(result['word_path']).name}")

    # Archivos generados
    excel_path = Path(result["excel_path"])
    word_path  = Path(result["word_path"])
    assert excel_path.exists(), "Excel no generado"
    assert word_path.exists(),  "Word no generado"
    assert excel_path.stat().st_size > 5000,  "Excel parece vacío"
    assert word_path.stat().st_size  > 5000,  "Word parece vacío"
    print(f"  Excel: {excel_path.stat().st_size/1024:.1f} KB")
    print(f"  Word : {word_path.stat().st_size/1024:.1f} KB")

    # Verificar Word unificado: tiene tablas de Sprint 1 Y Sprint 2
    from docx import Document
    doc = Document(word_path)

    n_tables = len(doc.tables)
    print(f"\n  Tablas en Word unificado: {n_tables}")
    # Sprint 1 genera 2 tablas (datos globales + productos) + 16 de encuesta = 18
    assert n_tables >= 16, f"Esperaba al menos 16 tablas, hay {n_tables}"

    # Verificar títulos de Cuadros (Sprint 2)
    cuadros = [p.text for p in doc.paragraphs if p.text.startswith("Cuadro ")]
    print(f"  Cuadros de encuesta     : {len(cuadros)}")
    assert len(cuadros) == 16, f"Esperaba 16 cuadros, hay {len(cuadros)}"
    print(f"  Primer cuadro: {cuadros[0]}")
    print(f"  Ultimo cuadro: {cuadros[-1]}")

    # Verificar sección de tabulación
    heading_texts = [p.text for p in doc.paragraphs if "Tabulación" in p.text]
    assert len(heading_texts) > 0, "Falta el encabezado '3. Tabulación de la Encuesta'"
    print(f"  Heading Sprint 2: '{heading_texts[0]}'")

    # Copiar Word a carpeta fase 2 para inspección visual
    import shutil
    dest = OUTPUT_WORD / f"completo_test_{result['plan_id']}.docx"
    shutil.copy2(word_path, dest)
    print(f"\n  Word copiado a: {dest}")

    ok(f"— plan_id={result['plan_id']}, {n_tables} tablas, {len(cuadros)} cuadros")
    return result["plan_id"]


# ─────────────────────────────────────────────────────────────────────────────
# 2. API — POST /process-complete
# ─────────────────────────────────────────────────────────────────────────────

def test_api_process_complete():
    sep("2. API — POST /process-complete")

    with open(ENCUESTA_PATH, "rb") as f:
        r = client.post(
            "/api/v1/process-complete",
            data={"data": json.dumps(CLIENT_INPUT)},
            files={"file": (
                "Encuesta.xlsx", f,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )},
        )

    print(f"  Status         : {r.status_code}")
    if r.status_code != 200:
        print(f"  Error          : {r.text[:500]}")
    assert r.status_code == 200

    data = r.json()["data"]
    print(f"  plan_id        : {data['plan_id']}")
    print(f"  nombre         : {data['nombre']}")
    print(f"  n_productos    : {data['n_productos']}")
    print(f"  bronze_rows    : {data['bronze_rows']}")
    print(f"  excel_url      : {data['excel_url']}")
    print(f"  word_url       : {data['word_url']}")

    assert data["bronze_rows"] == 320
    assert "excel_url" in data
    assert "word_url"  in data
    assert data["plan_id"] is not None

    ok(f"— plan_id={data['plan_id']}, ambas URLs presentes")
    return data["plan_id"]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Descargas
# ─────────────────────────────────────────────────────────────────────────────

def test_api_downloads(plan_id: int):
    sep(f"3. DESCARGAS — plan_id={plan_id}")

    # Excel
    r_excel = client.get(f"/api/v1/download/complete/{plan_id}/excel")
    print(f"  Excel status   : {r_excel.status_code}")
    assert r_excel.status_code == 200, f"Excel 404: {r_excel.text}"
    assert "spreadsheetml" in r_excel.headers.get("content-type", "")
    print(f"  Excel tamaño   : {len(r_excel.content)/1024:.1f} KB")

    # Word
    r_word = client.get(f"/api/v1/download/complete/{plan_id}/word")
    print(f"  Word status    : {r_word.status_code}")
    assert r_word.status_code == 200, f"Word 404: {r_word.text}"
    assert "wordprocessingml" in r_word.headers.get("content-type", "")
    print(f"  Word tamaño    : {len(r_word.content)/1024:.1f} KB")

    ok("— Excel y Word descargados")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  TEST SPRINT 2.1 — Pipeline unificado Plan + Encuesta")
    print("="*60)
    print(f"  Excel template : {EXCEL_TEMPLATE}")
    print(f"  Word template  : {WORD_TEMPLATE}")
    print(f"  Encuesta       : {ENCUESTA_PATH}")
    print(f"  Output Word    : {OUTPUT_WORD}")

    failed = []
    try:
        test_service_direct()
        plan_id = test_api_process_complete()
        test_api_downloads(plan_id)
    except AssertionError as e:
        failed.append(str(e))
        print(f"\n  ASSERTION FALLIDA: {e}")
        import traceback; traceback.print_exc()
    except Exception as e:
        failed.append(str(e))
        print(f"\n  ERROR: {e}")
        import traceback; traceback.print_exc()

    sep("RESULTADO FINAL")
    if failed:
        print(f"  FALLARON {len(failed)} test(s):")
        for f in failed:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("  Todos los tests pasaron correctamente")
        print(f"  Word unificado en: {OUTPUT_WORD}")
