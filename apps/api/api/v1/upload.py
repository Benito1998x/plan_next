"""
Upload Endpoint - Procesa datos del cliente y genera documentos de plan de negocio.

Flujo principal:
1. Cliente sube Excel con datos parciales (nombre, rubro, productos)
2. Agente IA extrae y completa los datos
3. Se rellena plantilla Excel con los datos completos
4. Se rellena plantilla Word con los datos completos
5. Se devuelven URLs de descarga

POST /api/v1/upload-excel         → sube Excel del cliente (legacy)
POST /api/v1/process-plan         → recibe JSON parcial del cliente (legacy)
GET  /api/v1/download/{plan_id}/{file_type}
GET  /api/v1/template/input1      → descarga plantilla vacía Input 1.xlsx (Sprint 1)
POST /api/v1/upload/plan          → pipeline híbrido LangChain completo (Sprint 1)
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import FileResponse

from models.schemas import APIResponse, ExtractedData
from services.excel_writer import ExcelWriter
from services.word_service import WordService
from services.ai_agent import get_ai_agent
from database import get_database
from core.exceptions import ValidationError, ProcessingError
from core.validators import FileValidator
from core import ErrorCodes

router = APIRouter(prefix="/api/v1", tags=["upload"])

validator = FileValidator()
writer = ExcelWriter()
word_service = WordService()

# Rutas a las plantillas maestras
_PLANTILLAS_DIR = Path(__file__).parent.parent.parent.parent.parent / "plantillas"
EXCEL_TEMPLATE = _PLANTILLAS_DIR / "excel" / "plantilla 1.xlsx"
WORD_TEMPLATE = _PLANTILLAS_DIR / "word" / "plantilla 1.docx"

# Sprint 1 — Input 1.xlsx pipeline paths
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
INPUT1_TEMPLATE = _PROJECT_ROOT / "data" / "sprint1" / "templates" / "input1_vacio.xlsx"
INPUT1_OUTPUTS_DIR = _PROJECT_ROOT / "data" / "sprint1" / "outputs"


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


# ─────────────────────────────────────────────────────────────────────────────
# SPRINT 1 — Input 1.xlsx Pipeline Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _save_plan_to_database(plan_data) -> int:
    """
    Persists a PlanData instance to all DB tables.

    Creates: Plan, ParametrosGlobales, Producto × N,
             DatosNegocio, BuyerPersona, ConfiguracionMetodologica.

    Returns the new plan.id.
    Raises sqlalchemy.exc.IntegrityError on constraint violation.
    """
    import json
    from models.db import (
        Plan,
        ParametrosGlobales,
        Producto,
        DatosNegocio,
        BuyerPersona,
        ConfiguracionMetodologica,
        EstadoPlan,
    )

    db = get_database()
    params = plan_data.parametros
    dn = plan_data.datos_negocio
    bp = plan_data.buyer_persona
    cm = plan_data.config_metodologica

    with db.get_session() as session:
        # ── Plan ──────────────────────────────────────────────────────────
        plan = Plan(
            nombre=params.nombre_proyecto or "Sin nombre",
            rubro=params.rubro_sector or "Sin rubro",
            ciudad=params.ciudad or "Sin ciudad",
            departamento=params.departamento or "Sin departamento",
            estado=EstadoPlan.BORRADOR,
        )
        session.add(plan)
        session.commit()
        session.refresh(plan)
        plan_id = plan.id

        # ── ParametrosGlobales ────────────────────────────────────────────
        pg = ParametrosGlobales(
            plan_id=plan_id,
            pais=params.pais or "Bolivia",
            moneda_codigo=params.moneda or "Bs",
            tipo_cambio_usd=float(params.tipo_cambio or 6.96),
            tasa_inflacion_anual=2.0,
            horizonte_anios=int(params.horizonte_anios or 5),
            anio_base=int(params.anio_base or 2025),
            anio_inicio_operaciones=int(params.anio_inicio_operaciones or 2026),
            impuesto_iue=25.0,
            impuesto_it=3.0,
        )
        session.add(pg)

        # ── Productos ──────────────────────────────────────────────────────
        for prod in plan_data.productos:
            session.add(
                Producto(
                    plan_id=plan_id,
                    numero=prod.numero,
                    nombre=prod.nombre,
                    unidad_medida=prod.unidad_medida or "Unidad",
                    peso_volumen=float(prod.precio_bs or 0.0),
                )
            )

        # ── DatosNegocio ───────────────────────────────────────────────────
        session.add(
            DatosNegocio(
                plan_id=plan_id,
                horario_atencion=dn.horario_atencion,
                dias_laborales_semana=dn.dias_laborales_semana,
                semanas_laborales_anio=dn.semanas_laborales_anio,
                horas_laborales_dia=dn.horas_laborales_dia,
                zona_direccion=dn.zona_direccion,
                canal_venta=dn.canal_venta,
                capacidad_diaria_unidades=dn.capacidad_diaria_unidades,
                num_socios_fundadores=dn.num_socios_fundadores,
            )
        )

        # ── BuyerPersona ───────────────────────────────────────────────────
        session.add(
            BuyerPersona(
                plan_id=plan_id,
                edad_objetivo=bp.edad_objetivo,
                genero_objetivo=bp.genero_objetivo,
                ocupacion_principal=bp.ocupacion_principal,
                zona_residencia_objetivo=bp.zona_residencia_objetivo,
                motivaciones_compra=bp.motivaciones_compra,
                canal_informacion_preferido=bp.canal_informacion_preferido,
                nivel_socioeconomico=bp.nivel_socioeconomico,
                problema_que_resuelve=bp.problema_que_resuelve,
            )
        )

        # ── ConfiguracionMetodologica ──────────────────────────────────────
        # All named fields are mapped directly; datos_adicionales stays NULL
        # at this stage (no overflow fields from PlanData schema).
        session.add(
            ConfiguracionMetodologica(
                plan_id=plan_id,
                precision_muestra=cm.precision_muestra,
                tipo_mercado=cm.tipo_mercado,
                metodo_proyeccion_ventas=cm.metodo_proyeccion_ventas,
                evolucion_precios=cm.evolucion_precios,
                metodo_depreciacion=cm.metodo_depreciacion,
                meses_capital_trabajo=cm.meses_capital_trabajo,
                necesita_financiamiento=cm.necesita_financiamiento,
                forma_pago=cm.forma_pago,
                frecuencia_pago=cm.frecuencia_pago,
                datos_adicionales=None,
            )
        )

        session.commit()
        return plan_id


# ─────────────────────────────────────────────────────────────────────────────
# SPRINT 1 — GET /template/input1
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/template/input1",
    summary="Descargar plantilla vacía Input 1.xlsx",
    description="Sirve la plantilla de Input 1.xlsx vacía para que el usuario la complete.",
    tags=["sprint1"],
)
async def get_input1_template():
    """
    Returns Input 1.xlsx as a file download attachment.

    - 200: xlsx file with correct Content-Type header
    - 404: template file not found on disk
    """
    if not INPUT1_TEMPLATE.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    return FileResponse(
        path=str(INPUT1_TEMPLATE),
        filename="Input_1_Plan_Negocio.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ─────────────────────────────────────────────────────────────────────────────
# SPRINT 1 — POST /upload/plan
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/upload/plan",
    summary="Subir Input 1.xlsx y generar plan completo (Sprint 1 pipeline)",
    description=(
        "Recibe Input 1.xlsx rellenado, corre el pipeline híbrido: "
        "validate → read → LangChain enrich → save DB → fill output xlsx → log tokens."
    ),
    tags=["sprint1"],
)
async def upload_plan(file: UploadFile = File(...)):
    """
    Full pipeline:
    1. Validate file (.xlsx only, size limit)
    2. Save to temp dir
    3. Input1Reader.read() → raw_dict
    4. Input1EnrichmentChain.enrich() → PlanData + token_info
    5. _save_plan_to_database() → plan_id
    6. ExcelWriter.fill_input1_template() → output xlsx
    7. LogProcesamiento insert (success or failure)
    8. Return 200 JSON with plan_id, sections_extracted, token data, excel_url
    """
    from services.input1_reader import Input1Reader
    from services.langchain_chain import Input1EnrichmentChain
    from models.db import LogProcesamiento

    start_time = datetime.utcnow()
    plan_id: Optional[int] = None

    # ── 1. Validate ────────────────────────────────────────────────────────
    try:
        await validator.validate_upload(file, {".xlsx"})
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ── 2. Save temp file ──────────────────────────────────────────────────
    temp_dir = _get_temp_dir()
    safe_name = Path(file.filename or "upload.xlsx").name
    temp_path = temp_dir / safe_name
    content = await file.read()
    temp_path.write_bytes(content)

    db = get_database()

    try:
        # ── 3. Read Excel ──────────────────────────────────────────────────
        reader = Input1Reader(temp_path)
        raw_dict = reader.read()

        # ── 4. LangChain enrichment ────────────────────────────────────────
        chain = Input1EnrichmentChain()
        plan_data, token_info = chain.enrich(raw_dict)

        # ── 5. Persist to DB ───────────────────────────────────────────────
        plan_id = _save_plan_to_database(plan_data)

        # ── 6. Fill output Excel ───────────────────────────────────────────
        INPUT1_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = INPUT1_OUTPUTS_DIR / f"{plan_id}_output.xlsx"
        writer.fill_input1_template(
            plan_id=plan_id,
            plan_data=plan_data,
            template_path=INPUT1_TEMPLATE,
            output_path=output_path,
        )

        # ── 7. Log success ─────────────────────────────────────────────────
        fin = datetime.utcnow()
        with db.get_session() as session:
            session.add(
                LogProcesamiento(
                    plan_id=plan_id,
                    archivo_entrada=file.filename or safe_name,
                    archivo_salida_excel=str(output_path),
                    estado="completado",
                    actividad="input1_enrichment",
                    tokens_prompt=token_info["tokens_prompt"],
                    tokens_completion=token_info["tokens_completion"],
                    costo_usd=token_info["costo_usd"],
                    inicio=start_time,
                    fin=fin,
                    duracion_segundos=(fin - start_time).total_seconds(),
                )
            )
            session.commit()

        # ── 8. Respond ─────────────────────────────────────────────────────
        sections_extracted = [
            "parametros_globales",
            "productos_servicios",
            "datos_negocio",
            "buyer_persona",
            "configuracion_metodologica",
        ]
        return {
            "plan_id": plan_id,
            "nombre": plan_data.parametros.nombre_proyecto,
            "sections_extracted": sections_extracted,
            "tokens_prompt": token_info["tokens_prompt"],
            "tokens_completion": token_info["tokens_completion"],
            "costo_usd": token_info["costo_usd"],
            "excel_url": f"/api/v1/download/plan/{plan_id}/excel",
            "word_url": None,
        }

    except HTTPException:
        raise

    except Exception as exc:
        # ── Error: log FAILED entry ────────────────────────────────────────
        fin = datetime.utcnow()
        try:
            with db.get_session() as session:
                session.add(
                    LogProcesamiento(
                        plan_id=plan_id,
                        archivo_entrada=file.filename or safe_name,
                        estado="error",
                        actividad="input1_enrichment",
                        mensaje_error=str(exc)[:500],
                        tokens_prompt=None,
                        tokens_completion=None,
                        costo_usd=None,
                        inicio=start_time,
                        fin=fin,
                        duracion_segundos=(fin - start_time).total_seconds(),
                    )
                )
                session.commit()
        except Exception:
            pass  # Don't mask original error with a logging failure

        raise HTTPException(
            status_code=500, detail=f"Processing error: {str(exc)}"
        )

    finally:
        # Clean up temp file
        try:
            if temp_path.exists():
                os.remove(temp_path)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# SPRINT 1 — Download output Excel
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/download/plan/{plan_id}/excel",
    summary="Descargar Excel de salida generado por Sprint 1 pipeline",
    tags=["sprint1"],
)
async def download_plan_excel(plan_id: int):
    """Returns the filled Input 1 Excel for the given plan_id."""
    output_path = INPUT1_OUTPUTS_DIR / f"{plan_id}_output.xlsx"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output file not found")
    return FileResponse(
        path=str(output_path),
        filename=f"Plan_{plan_id}_Input1.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
