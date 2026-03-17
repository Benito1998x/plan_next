"""
Upload Endpoint - Procesa datos del cliente y genera documentos de plan de negocio.

Flujo principal:
1. Cliente sube Excel con datos parciales (nombre, rubro, productos)
2. Agente IA extrae y completa los datos
3. Se rellena plantilla Excel con los datos completos
4. Se rellena plantilla Word con los datos completos
5. Se devuelven URLs de descarga

POST /api/v1/upload-excel   → sube Excel del cliente (legacy)
POST /api/v1/process-plan   → recibe JSON parcial del cliente (nuevo)
GET  /api/v1/download/{plan_id}/{file_type}
"""

import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import FileResponse

from models.schemas import APIResponse, ExtractedData
from services.excel_reader import ExcelReader
from services.excel_writer import ExcelWriter
from services.word_service import WordService
from services.table_detector import TableDetector
from services.ai_agent import get_ai_agent
from database import get_database
from core.exceptions import ValidationError, ProcessingError
from core.validators import FileValidator
from core import ErrorCodes

router = APIRouter(prefix="/api/v1", tags=["upload"])

validator = FileValidator()
reader = ExcelReader()
writer = ExcelWriter()
word_service = WordService()
detector = TableDetector()

# Rutas a las plantillas maestras
_PLANTILLAS_DIR = Path(__file__).parent.parent.parent.parent.parent / "plantillas"
EXCEL_TEMPLATE = _PLANTILLAS_DIR / "excel" / "plantilla 1.xlsx"
WORD_TEMPLATE = _PLANTILLAS_DIR / "word" / "plantilla 1.docx"


def _get_temp_dir() -> Path:
    temp_dir = Path(tempfile.gettempdir()) / "bpae"
    temp_dir.mkdir(exist_ok=True)
    return temp_dir


def _save_to_database(db, parametros: dict, productos: list) -> int:
    from models.db import Plan, ParametrosGlobales, Producto, EstadoPlan

    with db.get_session() as session:
        plan = Plan(
            nombre=parametros.get("nombre", "Sin nombre"),
            rubro=parametros.get("rubro", "Sin rubro"),
            ciudad=parametros.get("ciudad", "Sin ciudad"),
            departamento=parametros.get("departamento", "Sin departamento"),
            estado=EstadoPlan.BORRADOR,
        )
        session.add(plan)
        session.commit()
        session.refresh(plan)

        params_bd = ParametrosGlobales(
            plan_id=plan.id,
            pais=parametros.get("pais", "Bolivia"),
            moneda_codigo=parametros.get("moneda", "Bs"),
            tipo_cambio_usd=parametros.get("tipo_cambio", 6.96),
            tasa_inflacion_anual=parametros.get("inflacion", 0.02),
            horizonte_anios=parametros.get("horizonte", 5),
            anio_base=parametros.get("anio_base", 2025),
            anio_inicio_operaciones=parametros.get("anio_inicio", 2026),
            impuesto_iue=parametros.get("impuesto_iue", 0.25),
            impuesto_it=parametros.get("impuesto_it", 0.03),
        )
        session.add(params_bd)

        for prod_data in productos:
            producto = Producto(
                plan_id=plan.id,
                numero=prod_data.get("numero", 1),
                nombre=prod_data.get("nombre", "Sin nombre"),
                unidad_medida=prod_data.get("unidad_medida", "Unidad"),
                peso_volumen=prod_data.get("peso_volumen", 1.0),
            )
            session.add(producto)

        session.commit()
        return plan.id


def _generate_documents(plan_id: int, parametros: dict, productos: list) -> dict:
    """Genera Excel y Word rellenando las plantillas. Devuelve los paths."""
    temp_dir = _get_temp_dir()

    output_excel = temp_dir / f"plan_{plan_id}.xlsx"
    output_word = temp_dir / f"plan_{plan_id}.docx"

    # Excel: rellenar plantilla existente
    writer.fill_template(
        template_path=EXCEL_TEMPLATE,
        output_path=output_excel,
        parametros=parametros,
        productos=productos,
    )

    # Word: rellenar plantilla existente
    word_service.merge_from_template(
        template_path=WORD_TEMPLATE,
        parametros=parametros,
        productos=productos,
        output_path=output_word,
    )

    return {"excel": str(output_excel), "word": str(output_word)}


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT PRINCIPAL: JSON parcial del cliente + Agente IA
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/process-plan",
    response_model=APIResponse,
    summary="Procesar datos del cliente con agente IA",
    description=(
        "Recibe datos parciales del cliente (nombre, rubro, productos o num_productos), "
        "el agente IA completa los datos faltantes y genera los documentos."
    ),
)
async def process_plan(
    client_data: dict = Body(
        ...,
        example={
            "nombre": "Shawarma Cruz",
            "rubro": "Gastronomía",
            "num_productos": 2,
        },
    ),
):
    """
    Flujo:
    1. Agente IA interpreta los datos parciales del cliente
    2. Completa parámetros con defaults bolivianos
    3. Guarda en BD
    4. Rellena plantilla Excel (plantilla 1.xlsx)
    5. Rellena plantilla Word (plantilla 1.docx)
    6. Retorna plan_id + rutas de descarga
    """
    try:
        agent = get_ai_agent()
        plan_data = agent.extract_plan_data(client_data)

        parametros = plan_data["parametros_globales"]
        productos = plan_data["productos"]

        db = get_database()
        plan_id = _save_to_database(db, parametros, productos)

        docs = _generate_documents(plan_id, parametros, productos)

        return APIResponse(
            message="Plan generado exitosamente",
            data={
                "plan_id": plan_id,
                "nombre": parametros.get("nombre"),
                "rubro": parametros.get("rubro"),
                "parametros": parametros,
                "productos": productos,
                "excel_url": f"/api/v1/download/{plan_id}/excel",
                "word_url": f"/api/v1/download/{plan_id}/word",
                "excel_path": docs["excel"],
                "word_path": docs["word"],
                "_agent_error": plan_data.get("_agent_error"),
            },
        )

    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT LEGACY: Subida de Excel del cliente
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/upload-excel",
    response_model=APIResponse,
    summary="Subir Excel del cliente y procesar",
    description="Lee el Excel del cliente, extrae datos con agente IA y genera documentos.",
)
async def upload_excel(
    file: UploadFile = File(..., description="Archivo Excel del cliente"),
    version: str = "v1",
):
    """
    Flujo:
    1. Validar y guardar Excel temporalmente
    2. Detectar y leer secciones del Excel
    3. Agente IA completa los datos faltantes
    4. Guardar en BD
    5. Rellenar plantilla Excel y Word
    6. Retornar URLs de descarga
    """
    try:
        await validator.validate_upload(file, {".xlsx", ".xls"})

        temp_dir = _get_temp_dir()
        temp_path = temp_dir / file.filename
        content = await file.read()
        temp_path.write_bytes(content)

        from openpyxl import load_workbook

        wb = load_workbook(temp_path, data_only=True)
        ws = wb.active

        sections = detector.detect_all_sections(ws)
        extracted = _read_with_detection(ws, sections, version)
        wb.close()
        os.remove(temp_path)

        errors = _validate_required_fields(extracted)
        if errors:
            return APIResponse(
                error="VALIDATION_ERROR",
                message="Faltan campos obligatorios",
                data={"errors": errors},
            )

        # Agente IA completa los datos
        agent = get_ai_agent()
        client_input = {**extracted.parametros_globales, "productos": extracted.productos}
        plan_data = agent.extract_plan_data(client_input)

        parametros = plan_data["parametros_globales"]
        productos = plan_data["productos"]

        db = get_database()
        plan_id = _save_to_database(db, parametros, productos)
        docs = _generate_documents(plan_id, parametros, productos)

        return APIResponse(
            message="Archivo procesado exitosamente",
            data={
                "plan_id": plan_id,
                "nombre": parametros.get("nombre"),
                "parametros": parametros,
                "productos": productos,
                "sections_found": extracted.sections_found,
                "excel_url": f"/api/v1/download/{plan_id}/excel",
                "word_url": f"/api/v1/download/{plan_id}/word",
            },
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# DESCARGA
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/download/{plan_id}/{file_type}", summary="Descargar archivo generado")
async def download_file(plan_id: int, file_type: str):
    temp_dir = _get_temp_dir()

    if file_type == "excel":
        file_path = temp_dir / f"plan_{plan_id}.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif file_type == "word":
        file_path = temp_dir / f"plan_{plan_id}.docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(status_code=400, detail="Tipo inválido. Usar 'excel' o 'word'")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return FileResponse(path=file_path, media_type=media_type, filename=file_path.name)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS (detección de secciones del Excel del cliente)
# ─────────────────────────────────────────────────────────────────────────────


def _read_with_detection(ws, sections: dict, version: str) -> ExtractedData:
    extracted = ExtractedData()
    extracted.sections_found = list(sections.keys())

    if "parametros_globales" in sections:
        info = sections["parametros_globales"]
        if info["type"] == "key_value":
            for row in range(info.get("row_start", 4), info.get("row_end", 16) + 1):
                label = ws[f"A{row}"].value
                value = ws[f"B{row}"].value
                if label and value is not None:
                    field = _map_param_label(str(label).strip().upper())
                    if field:
                        extracted.parametros_globales[field] = _convert_value(value)

    if "productos_servicios" in sections:
        info = sections["productos_servicios"]
        if info["type"] == "table":
            start = info.get("data_start", 20)
            end = info.get("data_end", 29)
            col_b = info.get("col_start", 1) + 1
            col_c = col_b + 1
            col_d = col_b + 2
            for row in range(start, end + 1):
                nombre = ws.cell(row=row, column=col_b).value
                if nombre:
                    extracted.productos.append({
                        "numero": row - start + 1,
                        "nombre": str(nombre).strip(),
                        "unidad_medida": str(ws.cell(row=row, column=col_c).value or "Unidad"),
                        "peso_volumen": float(ws.cell(row=row, column=col_d).value or 1.0),
                    })

    extracted.detection_info = {
        "parametros_globales": sections.get("parametros_globales", {}),
        "productos_servicios": sections.get("productos_servicios", {}),
    }
    return extracted


def _map_param_label(label: str) -> Optional[str]:
    mappings = {
        "NOMBRE DEL PROYECTO": "nombre",
        "NOMBRE": "nombre",
        "RUBRO / SECTOR": "rubro",
        "RUBRO": "rubro",
        "SECTOR": "rubro",
        "CIUDAD": "ciudad",
        "DEPARTAMENTO": "departamento",
        "PAÍS": "pais",
        "PAIS": "pais",
        "MONEDA": "moneda",
        "TIPO DE CAMBIO": "tipo_cambio",
        "TASA DE INFLACIÓN ANUAL": "inflacion",
        "INFLACIÓN": "inflacion",
        "INFLACION": "inflacion",
        "HORIZONTE DE PROYECCIÓN": "horizonte",
        "HORIZONTE": "horizonte",
        "AÑO BASE": "anio_base",
        "AÑO INICIO OPERACIONES": "anio_inicio",
        "AÑO INICIO": "anio_inicio",
        "IMPUESTO IUE (%)": "impuesto_iue",
        "IMPUESTO IUE": "impuesto_iue",
        "IUE": "impuesto_iue",
        "IMPUESTO IT (%)": "impuesto_it",
        "IMPUESTO IT": "impuesto_it",
        "IT": "impuesto_it",
    }
    for pattern, field in mappings.items():
        if pattern in label or label in pattern:
            return field
    return None


def _convert_value(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (ValueError, TypeError):
        return str(value).strip()


def _validate_required_fields(data: ExtractedData) -> list:
    errors = []
    for field in ["nombre", "rubro", "ciudad"]:
        if field not in data.parametros_globales or not data.parametros_globales[field]:
            errors.append(f"Campo obligatorio faltante: {field}")
    if not data.productos:
        errors.append("No se encontraron productos")
    return errors
