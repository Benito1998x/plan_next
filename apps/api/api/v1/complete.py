"""
Complete Endpoint — Sprint 2.1: Plan de negocio + Tabulación de encuesta

POST /api/v1/process-complete
    Body (form):
        - data (JSON string): datos del cliente {nombre, rubro, productos, ...}
        - file (UploadFile): Encuesta.xlsx

GET /api/v1/download/complete/{plan_id}/excel  → descarga Excel del plan
GET /api/v1/download/complete/{plan_id}/word   → descarga Word unificado
"""

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from models.schemas import APIResponse
from services.complete_service import run_complete_pipeline

router = APIRouter(prefix="/api/v1", tags=["complete"])

_PLANTILLAS_DIR    = Path(__file__).parent.parent.parent.parent.parent / "plantillas"
EXCEL_TEMPLATE     = _PLANTILLAS_DIR / "excel" / "fase 1" / "plantilla 1.xlsx"
WORD_TEMPLATE      = _PLANTILLAS_DIR / "word"  / "fase 1" / "plantilla 1.docx"
ENCUESTA_DEFAULT   = _PLANTILLAS_DIR / "excel" / "fase 2" / "Encuesta.xlsx"


def _get_output_dir() -> Path:
    d = Path(tempfile.gettempdir()) / "bpae" / "complete"
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.post(
    "/process-complete",
    response_model=APIResponse,
    summary="Sprint 2.1 — Plan de negocio + Tabulación de encuesta",
    description=(
        "Recibe datos del cliente (JSON) y Encuesta.xlsx. "
        "Genera un Excel con el plan de negocio y un Word unificado "
        "con datos del plan + 16 tablas de frecuencia de la encuesta."
    ),
)
async def process_complete(
    data: str = Form(
        ...,
        description=(
            'JSON con datos del cliente. Ejemplo: '
            '{"nombre":"Mi Negocio","rubro":"Gastronomía","num_productos":3}'
        ),
    ),
    file: UploadFile = File(
        default=None,
        description="Encuesta.xlsx. Si se omite, usa la encuesta por defecto.",
    ),
):
    try:
        # Parsear JSON del cliente
        try:
            client_input = json.loads(data)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=422, detail=f"JSON inválido en 'data': {e}")

        # Validar templates
        for path, name in [(EXCEL_TEMPLATE, "plantilla 1.xlsx"), (WORD_TEMPLATE, "plantilla 1.docx")]:
            if not path.exists():
                raise HTTPException(status_code=500, detail=f"Template no encontrado: {name} → {path}")

        # Archivo de encuesta
        output_dir = _get_output_dir()
        if file is not None:
            encuesta_path = output_dir / (file.filename or "encuesta.xlsx")
            encuesta_path.write_bytes(await file.read())
        else:
            if not ENCUESTA_DEFAULT.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"No se subió encuesta y no existe la default: {ENCUESTA_DEFAULT}",
                )
            encuesta_path = ENCUESTA_DEFAULT

        # Ejecutar pipeline completo
        result = run_complete_pipeline(
            client_input=client_input,
            encuesta_path=encuesta_path,
            excel_template_path=EXCEL_TEMPLATE,
            word_template_path=WORD_TEMPLATE,
            output_dir=output_dir,
        )

        plan_id = result["plan_id"]

        return APIResponse(
            message="Plan completo generado exitosamente",
            data={
                "plan_id"        : plan_id,
                "nombre"         : result["parametros"].get("nombre"),
                "rubro"          : result["parametros"].get("rubro"),
                "n_productos"    : result["n_productos"],
                "bronze_rows"    : result["bronze_rows"],
                "variable_names" : result["variable_names"],
                "excel_url"      : f"/api/v1/download/complete/{plan_id}/excel",
                "word_url"       : f"/api/v1/download/complete/{plan_id}/word",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en pipeline completo: {e}")


@router.get("/download/complete/{plan_id}/excel", summary="Descargar Excel del plan")
async def download_complete_excel(plan_id: int):
    # Buscar el archivo Excel generado para este plan_id
    output_dir = _get_output_dir()
    matches = list(output_dir.glob(f"*_plan.xlsx"))
    # El nombre del archivo es {nombre_slug}_plan.xlsx — buscar el más reciente
    # correspondiente a este plan_id (almacenado como survey_id en SQLite)
    file_path = _find_file_by_plan_id(output_dir, plan_id, "_plan.xlsx")
    if file_path is None:
        raise HTTPException(status_code=404, detail="Excel no encontrado. Ejecute /process-complete primero.")
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"plan_{plan_id}.xlsx",
    )


@router.get("/download/complete/{plan_id}/word", summary="Descargar Word unificado (plan + tabulación)")
async def download_complete_word(plan_id: int):
    file_path = _find_file_by_plan_id(_get_output_dir(), plan_id, "_completo.docx")
    if file_path is None:
        raise HTTPException(status_code=404, detail="Word no encontrado. Ejecute /process-complete primero.")
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"plan_completo_{plan_id}.docx",
    )


# ── helper ────────────────────────────────────────────────────────────────────

def _find_file_by_plan_id(output_dir: Path, plan_id: int, suffix: str) -> Path | None:
    """
    Recupera el archivo generado para un plan_id.
    Guarda metadata en un índice JSON simple para asociar plan_id → filename.
    """
    index_path = output_dir / "index.json"
    if not index_path.exists():
        return None
    import json as _json
    index = _json.loads(index_path.read_text())
    entry = index.get(str(plan_id))
    if not entry:
        return None
    path = Path(entry.get("excel" if suffix.endswith(".xlsx") else "word", ""))
    return path if path.exists() else None
