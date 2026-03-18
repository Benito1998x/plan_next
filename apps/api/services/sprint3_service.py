"""
Sprint 3 Service — Indicadores de Mercado

Orquesta el pipeline completo de Sprint 3:
  1. Carga datos Gold de un survey (Silver → Gold)
  2. Carga datos del plan (BuyerPersona, DatosNegocio) desde SQLite
  3. Calcula indicadores de mercado con indicators.py
  4. Genera Excel con hoja de indicadores
  5. Genera Word con sección "Indicadores de Mercado"

Output: un Excel + un Word con los KPIs derivados de la encuesta.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from sqlmodel import select

from database import get_database
from models.db.survey import Survey
from models.db.plan_data import Plan, DatosNegocio, BuyerPersona
from services.pipeline.bronze import ingest_excel, load_bronze_df
from services.pipeline.silver import build_silver
from services.pipeline.gold import build_gold, load_gold_variables
from services.pipeline.indicators import build_indicators, build_indicators_summary


# ─── Colores Excel ────────────────────────────────────────────────────────────
_HEADER_FILL  = PatternFill(fill_type="solid", fgColor="FF1C246A")   # azul oscuro
_HEADER_FONT  = Font(bold=True, color="FFFFFFFF", size=10)
_TOTAL_FILL   = PatternFill(fill_type="solid", fgColor="FFD5D8DC")   # gris
_LABEL_FONT   = Font(bold=True, size=10)
_DATA_FONT    = Font(size=10)
_THIN_BORDER  = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"),  bottom=Side(style="thin"),
)

# ─── Colores Word ─────────────────────────────────────────────────────────────
_W_HEADER_BG = "1C246A"
_W_HEADER_FG = RGBColor(0xFF, 0xFF, 0xFF)
_W_ALT_BG    = "EBF1F9"


def run_sprint3(
    survey_id: int,
    plan_id: Optional[int],
    output_dir: Path,
) -> Dict[str, Any]:
    """
    Pipeline Sprint 3 completo.

    Args:
        survey_id  : ID del Survey en SQLite (tabla survey)
        plan_id    : ID del Plan en SQLite (opcional, para contexto buyer persona)
        output_dir : carpeta donde guardar los archivos generados

    Returns:
        {
            "survey_id"    : int,
            "plan_id"      : int | None,
            "n_indicadores": int,
            "summary"      : {...},
            "indicadores"  : [...],
            "excel_path"   : str,
            "word_path"    : str,
        }
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Cargar datos Gold ──────────────────────────────────────────────────
    df_raw = load_bronze_df(survey_id)
    silver = build_silver(df_raw)
    variable_names = load_gold_variables(survey_id)
    gold = build_gold(silver, variable_names, survey_id=survey_id)

    # ── 2. Calcular indicadores ───────────────────────────────────────────────
    indicadores = build_indicators(gold)
    summary     = build_indicators_summary(indicadores)

    # ── 3. Cargar contexto del plan (opcional) ────────────────────────────────
    plan_nombre = "Plan de Negocio"
    buyer_persona_ctx: Dict[str, Any] = {}
    datos_negocio_ctx: Dict[str, Any] = {}

    if plan_id is not None:
        db = get_database()
        with db.get_session() as session:
            plan = session.get(Plan, plan_id)
            if plan:
                plan_nombre = plan.nombre
            dn = session.exec(select(DatosNegocio).where(DatosNegocio.plan_id == plan_id)).first()
            if dn:
                datos_negocio_ctx = {
                    "horario_atencion": dn.horario_atencion,
                    "zona_direccion":   dn.zona_direccion,
                    "canal_venta":      dn.canal_venta,
                    "capacidad_diaria": dn.capacidad_diaria,
                }
            bp = session.exec(select(BuyerPersona).where(BuyerPersona.plan_id == plan_id)).first()
            if bp:
                buyer_persona_ctx = {
                    "edad_objetivo":            bp.edad_objetivo,
                    "genero_objetivo":          bp.genero_objetivo,
                    "ocupacion_principal":      bp.ocupacion_principal,
                    "zona_residencia_objetivo": bp.zona_residencia_objetivo,
                    "motivaciones_compra":      bp.motivaciones_compra,
                    "canal_informacion":        bp.canal_informacion,
                    "nivel_socioeconomico":     bp.nivel_socioeconomico,
                }

    # ── 4. Generar Excel ──────────────────────────────────────────────────────
    slug = plan_nombre.replace(" ", "_").lower()
    excel_path = output_dir / f"{slug}_indicadores_sprint3.xlsx"
    _generate_excel(indicadores, summary, plan_nombre, excel_path)

    # ── 5. Generar Word ───────────────────────────────────────────────────────
    word_path = output_dir / f"{slug}_indicadores_sprint3.docx"
    _generate_word(
        indicadores, summary, plan_nombre,
        buyer_persona_ctx, datos_negocio_ctx,
        word_path,
    )

    # ── 6. Guardar índice ─────────────────────────────────────────────────────
    index_path = output_dir / "index_sprint3.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    index[str(survey_id)] = {"excel": str(excel_path), "word": str(word_path)}
    index_path.write_text(json.dumps(index, indent=2))

    return {
        "survey_id":     survey_id,
        "plan_id":       plan_id,
        "n_indicadores": len(indicadores),
        "summary":       summary,
        "indicadores":   indicadores,
        "excel_path":    str(excel_path),
        "word_path":     str(word_path),
    }


# ─── Generación Excel ──────────────────────────────────────────────────────────

def _generate_excel(
    indicadores: List[Dict],
    summary: Dict,
    plan_nombre: str,
    output_path: Path,
) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "INDICADORES"

    # Título
    ws["A1"] = f"INDICADORES DE MERCADO — {plan_nombre.upper()}"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A1"].alignment = Alignment(horizontal="center")
    ws.merge_cells("A1:E1")
    ws.row_dimensions[1].height = 22

    ws["A2"] = f"Total de encuestados: {_get_total(indicadores)}"
    ws["A2"].font = Font(italic=True, size=10)
    ws.merge_cells("A2:E2")

    # Encabezados de tabla
    headers = ["N°", "Indicador", "Valor / Moda", "Detalle", "Método de Cálculo"]
    col_widths = [5, 35, 22, 28, 30]
    for col_i, (hdr, width) in enumerate(zip(headers, col_widths), start=1):
        cell = ws.cell(row=4, column=col_i, value=hdr)
        cell.font   = _HEADER_FONT
        cell.fill   = _HEADER_FILL
        cell.border = _THIN_BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[cell.column_letter].width = width

    ws.row_dimensions[4].height = 20

    # Filas de datos
    for i, ind in enumerate(indicadores, start=1):
        row = 4 + i
        fill = PatternFill(fill_type="solid", fgColor="FFEBF1F9") if i % 2 == 0 else None
        values = [i, ind["indicador"], ind["valor"], ind["detalle"], ind["calculo"]]
        for col_i, val in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col_i, value=val)
            cell.font   = _DATA_FONT
            cell.border = _THIN_BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            if fill:
                cell.fill = fill
        ws.row_dimensions[row].height = 18

    ws.freeze_panes = "A5"
    wb.save(output_path)


def _get_total(indicadores: List[Dict]) -> int:
    for ind in indicadores:
        detalle = ind.get("detalle", "")
        if " de " in detalle:
            try:
                return int(detalle.split(" de ")[1].split(" ")[0])
            except (ValueError, IndexError):
                pass
    return 0


# ─── Generación Word ───────────────────────────────────────────────────────────

def _generate_word(
    indicadores: List[Dict],
    summary: Dict,
    plan_nombre: str,
    buyer_persona: Dict,
    datos_negocio: Dict,
    output_path: Path,
) -> None:
    doc = Document()

    # Título
    title = doc.add_heading(f"INDICADORES DE MERCADO", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph(f"Plan: {plan_nombre}")
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.runs[0].italic = True

    doc.add_paragraph()

    # ── Resumen ejecutivo ────────────────────────────────────────────────────
    doc.add_heading("Resumen Ejecutivo", level=1)
    summary_fields = [
        ("Total de Indicadores",          str(summary.get("total_indicadores", len(indicadores)))),
        ("Tasa de Aceptación",            summary.get("tasa_aceptacion", "—")),
        ("Segmento Etario Principal",     summary.get("segmento_etario_principal", "—")),
        ("Canal de Venta Preferido",      summary.get("canal_preferido", "—")),
        ("Precio Aceptable (top)",        summary.get("precio_aceptable", "—")),
        ("Medio de Comunicación Top",     summary.get("medio_comunicacion", "—")),
    ]
    tbl = doc.add_table(rows=len(summary_fields), cols=2)
    tbl.style = "Normal Table"
    _add_borders_word(tbl)
    for i, (label, val) in enumerate(summary_fields):
        tbl.rows[i].cells[0].text = label
        tbl.rows[i].cells[0].paragraphs[0].runs[0].bold = True
        _set_cell_bg_word(tbl.rows[i].cells[0], "D9E2F3")
        tbl.rows[i].cells[1].text = val
    tbl.columns[0].width = Inches(2.8)
    tbl.columns[1].width = Inches(3.2)

    doc.add_paragraph()

    # ── Tabla de indicadores ─────────────────────────────────────────────────
    doc.add_heading("Indicadores Detallados", level=1)
    n_rows = 1 + len(indicadores)
    tbl2 = doc.add_table(rows=n_rows, cols=4)
    tbl2.style = "Normal Table"
    _add_borders_word(tbl2)

    headers = ["Indicador", "Valor / Moda", "Detalle", "Método"]
    widths  = [Inches(2.2), Inches(1.4), Inches(1.6), Inches(1.3)]
    hrow = tbl2.rows[0]
    for col_i, (hdr, w) in enumerate(zip(headers, widths)):
        cell = hrow.cells[col_i]
        cell.width = w
        _set_cell_bg_word(cell, _W_HEADER_BG)
        para = cell.paragraphs[0]
        para.clear()
        run = para.add_run(hdr)
        run.bold = True
        run.font.size = Pt(9)
        run.font.color.rgb = _W_HEADER_FG
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for i, ind in enumerate(indicadores):
        row = tbl2.rows[i + 1]
        bg = _W_ALT_BG if i % 2 == 0 else None
        vals = [ind["indicador"], ind["valor"], ind["detalle"], ind["calculo"]]
        for col_i, (val, w) in enumerate(zip(vals, widths)):
            cell = row.cells[col_i]
            cell.width = w
            if bg:
                _set_cell_bg_word(cell, bg)
            para = cell.paragraphs[0]
            para.clear()
            run = para.add_run(str(val))
            run.font.size = Pt(9)

    doc.add_paragraph()

    # ── Contexto: Buyer Persona (si hay datos) ───────────────────────────────
    bp_items = {k: v for k, v in buyer_persona.items() if v}
    if bp_items:
        doc.add_heading("Contexto: Buyer Persona", level=1)
        bp_labels = {
            "edad_objetivo":            "Edad Objetivo",
            "genero_objetivo":          "Género Objetivo",
            "ocupacion_principal":      "Ocupación Principal",
            "zona_residencia_objetivo": "Zona de Residencia Objetivo",
            "motivaciones_compra":      "Motivaciones de Compra",
            "canal_informacion":        "Canal de Información",
            "nivel_socioeconomico":     "Nivel Socioeconómico",
        }
        tbl3 = doc.add_table(rows=len(bp_items), cols=2)
        tbl3.style = "Normal Table"
        _add_borders_word(tbl3)
        for i, (key, val) in enumerate(bp_items.items()):
            tbl3.rows[i].cells[0].text = bp_labels.get(key, key)
            tbl3.rows[i].cells[0].paragraphs[0].runs[0].bold = True
            _set_cell_bg_word(tbl3.rows[i].cells[0], "E2EFDA")
            tbl3.rows[i].cells[1].text = str(val)
        tbl3.columns[0].width = Inches(2.8)
        tbl3.columns[1].width = Inches(3.2)

    # Fuente
    doc.add_paragraph()
    fuente = doc.add_paragraph()
    run = fuente.add_run("Fuente: Encuesta de Google Form — procesada con pipeline Silver/Gold")
    run.italic = True
    run.font.size = Pt(9)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)


# ─── Helpers Word ──────────────────────────────────────────────────────────────

def _add_borders_word(table) -> None:
    tbl  = table._tbl
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)
    for existing in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(existing)
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"),   "single")
        el.set(qn("w:sz"),    "6")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "000000")
        borders.append(el)
    tblPr.append(borders)


def _set_cell_bg_word(cell, color_hex: str) -> None:
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  color_hex)
    for existing in tcPr.findall(qn("w:shd")):
        tcPr.remove(existing)
    tcPr.append(shd)
