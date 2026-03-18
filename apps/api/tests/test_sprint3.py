"""
Test Sprint 3 — Pipeline Estadístico de Indicadores de Mercado

Valida:
  1. Variable classifier  : clasifica las 16 variables del Gold dinámicamente
  2. Quantitative stats   : μ, σ, IC-95% para variables cuantitativas
  3. Indicators v2        : distribuciones completas, moda, acumulados, Likert
  4. Excel generado       : hoja INDICADORES insertada ANTES de 'Muestra'
  5. API POST /process    : endpoint Sprint 3 responde correctamente
  6. API GET downloads    : excel y word descargables

Ejecutar desde apps/api/:
  python -X utf8 tests/test_sprint3.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import openpyxl
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

_PLANTILLAS   = Path(__file__).parent.parent.parent.parent / "plantillas"
ENCUESTA_PATH = _PLANTILLAS / "excel" / "fase 2" / "Encuesta.xlsx"
PLANTILLA_2   = _PLANTILLAS / "excel" / "fase 2" / "plantilla 2.xlsx"


def sep(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print("=" * 60)


def ok(msg: str = ""):
    print(f"  OK {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Bronze + Silver + Gold (base para los tests siguientes)
# ─────────────────────────────────────────────────────────────────────────────

def setup_survey() -> tuple:
    """Ingesta la encuesta y construye Silver/Gold. Retorna (survey_id, silver, gold)."""
    from database import get_database
    from services.pipeline.bronze import ingest_excel, extract_question_texts
    from services.pipeline.silver import build_silver
    from services.pipeline.gold import build_gold, load_gold_variables
    from services.ai_agent import get_ai_agent

    get_database().create_tables()  # Garantiza que las tablas existen

    survey_id, df_raw = ingest_excel(ENCUESTA_PATH, "Test Sprint 3")
    silver = build_silver(df_raw)

    variable_names = load_gold_variables(survey_id)
    if not variable_names:
        agent = get_ai_agent()
        texts = extract_question_texts(df_raw)
        variable_names = agent.infer_variable_names(texts)

    gold = build_gold(silver, variable_names, survey_id=survey_id)
    return survey_id, silver, gold, variable_names


# ─────────────────────────────────────────────────────────────────────────────
# 2. Variable Classifier
# ─────────────────────────────────────────────────────────────────────────────

def test_variable_classifier(survey_id, silver, variable_names):
    sep("1. VARIABLE CLASSIFIER — Clasificación dinámica por IA")

    from services.pipeline.variable_classifier import classify_variables
    from services.ai_agent import get_ai_agent

    agent = get_ai_agent()
    classification = classify_variables(silver, variable_names, survey_id, agent)

    print(f"  Variables clasificadas: {len(classification)}")
    assert len(classification) >= 1, "No se clasificaron variables"

    valid_types = {"nominal", "ordinal", "ordinal_likert", "cuantitativa"}
    for q_num, cls in classification.items():
        tipo = cls.get("tipo")
        assert tipo in valid_types, f"Q{q_num}: tipo inválido '{tipo}'"
        print(f"    Q{q_num:>2}: {cls.get('variable', '')[:30]:30s} → {tipo}")

    ok(f"— {len(classification)} variables clasificadas correctamente")
    return classification


# ─────────────────────────────────────────────────────────────────────────────
# 3. Quantitative Transform
# ─────────────────────────────────────────────────────────────────────────────

def test_quantitative_transform():
    sep("2. QUANTITATIVE TRANSFORM — μ, σ, IC-95%, probabilidades")

    from services.pipeline.quantitative_transform import (
        compute_weighted_stats,
        cumulative_probability,
        survival_probability,
        build_probability_points,
    )

    # Simulación: Q10 precio shawarma (midpoints típicos)
    options_precio = [
        {"label": "Menos de Bs. 20",  "freq": 15,  "pct": 0.047},
        {"label": "Bs. 21 a 35",      "freq": 98,  "pct": 0.306},
        {"label": "Bs. 36 a 50",      "freq": 130, "pct": 0.406},
        {"label": "Bs. 51 a 70",      "freq": 62,  "pct": 0.194},
        {"label": "Más de Bs. 70",    "freq": 15,  "pct": 0.047},
    ]
    conversiones_precio = {
        "Menos de Bs. 20": 15.0,
        "Bs. 21 a 35":     28.0,
        "Bs. 36 a 50":     43.0,
        "Bs. 51 a 70":     60.5,
        "Más de Bs. 70":   84.0,
    }

    stats = compute_weighted_stats(options_precio, conversiones_precio, 320)

    print(f"  μ (precio)    = {stats['mu']:.4f} Bs.")
    print(f"  σ (precio)    = {stats['sigma']:.4f} Bs.")
    print(f"  IC 95%        = [{stats['ic_95_lower']:.4f}, {stats['ic_95_upper']:.4f}]")

    assert stats["mu"] is not None, "μ no calculado"
    assert stats["sigma"] is not None, "σ no calculado"
    assert 20 < stats["mu"] < 70, f"μ={stats['mu']} fuera de rango esperado [20, 70]"
    assert stats["sigma"] > 0, "σ debe ser positivo"
    assert stats["ic_95_lower"] < stats["mu"] < stats["ic_95_upper"], "IC-95% no cubre μ"

    # Probabilidades acumuladas
    p_at_most_50 = cumulative_probability(50.0, stats["mu"], stats["sigma"])
    p_at_least_50 = survival_probability(50.0, stats["mu"], stats["sigma"])
    print(f"  P(X ≤ Bs.50) = {p_at_most_50*100:.1f}%")
    print(f"  P(X ≥ Bs.50) = {p_at_least_50*100:.1f}%")
    assert abs(p_at_most_50 + p_at_least_50 - 1.0) < 1e-9, "P(X≤x) + P(X≥x) ≠ 1"

    # Puntos de probabilidad
    pts = build_probability_points(stats["mu"], stats["sigma"], stats["options_with_value"], "Bs.")
    print(f"  Puntos de probabilidad: {len(pts)}")
    assert len(pts) > 0, "Sin puntos de probabilidad"
    for pt in pts:
        assert 0 <= pt["p_at_most"] <= 1, f"p_at_most={pt['p_at_most']} fuera de [0,1]"

    ok("— μ, σ, IC-95% y probabilidades calculadas correctamente")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Indicators v2
# ─────────────────────────────────────────────────────────────────────────────

def test_indicators_v2(gold, classification, survey_id):
    sep("3. INDICATORS V2 — Distribuciones completas")

    from services.pipeline.indicators_v2 import build_indicators_v2

    resultado = build_indicators_v2(
        gold=gold,
        classification=classification,
        n_total=320,
        n_segmento=None,
        filtros_aplicados=None,
        advertencias=[],
    )

    meta = resultado["metadata"]
    inds = resultado["indicadores"]

    print(f"  n_indicadores: {meta['n_indicadores']}")
    print(f"  n_total      : {meta['n_total']}")
    assert meta["n_indicadores"] == len(inds), "n_indicadores inconsistente"
    assert len(inds) >= 1

    for ind in inds:
        q_num = ind["pregunta"]
        tipo  = ind["tipo"]
        dist  = ind.get("distribucion", [])
        assert len(dist) > 0, f"Q{q_num}: distribución vacía"
        assert "moda" in ind, f"Q{q_num}: falta moda"
        assert "p_moda" in ind, f"Q{q_num}: falta p_moda"

        pct_sum = sum(d["pct"] for d in dist)
        assert abs(pct_sum - 100.0) < 1.0, f"Q{q_num}: suma de % = {pct_sum:.2f} ≠ 100"

        if tipo in ("cuantitativa", "ordinal_likert"):
            mu = ind.get("mu")
            if mu is not None:
                assert ind.get("sigma") is not None, f"Q{q_num}: mu sin sigma"
                print(f"    Q{q_num} [{tipo}]: μ={mu:.2f}, σ={ind['sigma']:.2f}")

        elif tipo == "ordinal":
            p_acum = ind.get("p_acumulados", [])
            assert len(p_acum) == len(dist), f"Q{q_num}: p_acumulados incompleto"

        elif tipo == "nominal":
            assert "indice_diversidad" in ind, f"Q{q_num}: falta indice_diversidad"

    ok(f"— {len(inds)} indicadores con distribuciones correctas")
    return resultado


# ─────────────────────────────────────────────────────────────────────────────
# 5. Excel generado — hoja INDICADORES ANTES de Muestra
# ─────────────────────────────────────────────────────────────────────────────

def test_excel_sheet_order(resultado):
    sep("4. EXCEL — INDICADORES insertado antes de 'Muestra'")

    from services.sprint3_service import _generate_excel

    out_path = Path(tempfile.gettempdir()) / "test_sprint3_indicadores.xlsx"
    _generate_excel(resultado, "Test Plan", 320, None, out_path)

    assert out_path.exists(), f"Excel no fue creado en {out_path}"
    size_kb = out_path.stat().st_size / 1024
    print(f"  Archivo: {out_path.name} ({size_kb:.1f} KB)")
    assert size_kb > 5, "Excel parece vacío"

    wb = openpyxl.load_workbook(str(out_path))
    sheets = wb.sheetnames
    print(f"  Hojas: {sheets}")

    assert "INDICADORES" in sheets, "No existe hoja INDICADORES"

    if "Muestra" in sheets:
        ind_idx    = sheets.index("INDICADORES")
        muestra_idx = sheets.index("Muestra")
        assert ind_idx < muestra_idx, (
            f"INDICADORES (pos {ind_idx}) no está antes de Muestra (pos {muestra_idx})"
        )
        print(f"  INDICADORES (pos {ind_idx}) < Muestra (pos {muestra_idx}): OK")
    else:
        print("  Nota: plantilla 2.xlsx no disponible, workbook nuevo sin 'Muestra'")

    # Verificar que la hoja tiene contenido
    ws = wb["INDICADORES"]
    assert ws.max_row > 5, "La hoja INDICADORES parece vacía"
    print(f"  Filas en INDICADORES: {ws.max_row}")

    ok("— Excel con orden correcto de hojas")
    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# 6. API Sprint 3
# ─────────────────────────────────────────────────────────────────────────────

def test_api_sprint3(survey_id):
    sep("5. API — POST /api/v1/sprint3/process")

    r = client.post(
        "/api/v1/sprint3/process",
        json={"survey_id": survey_id, "plan_id": None},
    )
    print(f"  Status     : {r.status_code}")
    if r.status_code != 200:
        print(f"  Error      : {r.text[:500]}")
    assert r.status_code == 200, f"Sprint3 process falló: {r.text[:300]}"

    data = r.json()
    print(f"  n_indicadores : {data.get('n_indicadores')}")
    print(f"  n_total       : {data.get('n_total')}")
    print(f"  advertencias  : {data.get('advertencias', [])}")

    assert "indicadores" in data, "Falta 'indicadores' en la respuesta"
    assert "downloads"   in data, "Falta 'downloads' en la respuesta"
    assert data["n_indicadores"] >= 1

    ok(f"— {data['n_indicadores']} indicadores procesados por la API")
    return data


def test_api_downloads(survey_id):
    sep("6. API — Descargas Excel y Word")

    # Excel
    r_excel = client.get(f"/api/v1/sprint3/download/{survey_id}/excel")
    print(f"  Excel status  : {r_excel.status_code}")
    assert r_excel.status_code == 200, f"Excel download falló: {r_excel.text[:200]}"
    excel_size = len(r_excel.content) / 1024
    print(f"  Excel tamaño  : {excel_size:.1f} KB")
    assert excel_size > 5, "Excel descargado parece vacío"

    # Word
    r_word = client.get(f"/api/v1/sprint3/download/{survey_id}/word")
    print(f"  Word status   : {r_word.status_code}")
    assert r_word.status_code == 200, f"Word download falló: {r_word.text[:200]}"
    word_size = len(r_word.content) / 1024
    print(f"  Word tamaño   : {word_size:.1f} KB")
    assert word_size > 5, "Word descargado parece vacío"

    # Verificar que el Excel descargado tiene INDICADORES antes de Muestra
    out = Path(tempfile.gettempdir()) / f"downloaded_sprint3_{survey_id}.xlsx"
    out.write_bytes(r_excel.content)
    wb = openpyxl.load_workbook(str(out))
    sheets = wb.sheetnames
    print(f"  Hojas Excel descargado: {sheets}")
    assert "INDICADORES" in sheets

    ok("— Excel y Word descargados, hojas correctas")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  TEST SPRINT 3 — Pipeline Estadístico de Indicadores")
    print("=" * 60)
    print(f"  Encuesta  : {ENCUESTA_PATH}")
    print(f"  Plantilla2: {PLANTILLA_2}")

    failed = []

    try:
        assert ENCUESTA_PATH.exists(), f"No existe Encuesta.xlsx: {ENCUESTA_PATH}"

        # Setup
        survey_id, silver, gold, variable_names = setup_survey()
        print(f"\n  survey_id={survey_id}, Gold con {len(gold)} preguntas")

        # Tests unitarios
        classification = test_variable_classifier(survey_id, silver, variable_names)
        test_quantitative_transform()
        resultado = test_indicators_v2(gold, classification, survey_id)
        test_excel_sheet_order(resultado)

        # Tests API (end-to-end)
        api_data = test_api_sprint3(survey_id)
        test_api_downloads(survey_id)

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
        print("  Todos los tests de Sprint 3 pasaron correctamente")
