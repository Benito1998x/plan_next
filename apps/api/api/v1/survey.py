"""
Survey Endpoint — Pipeline Bronze → Silver → Gold → Word

POST /api/v1/process-survey        → sube Encuesta.xlsx, genera Word con 16 tablas
GET  /api/v1/download/survey/{id}/word → descarga el Word generado
"""

import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from models.schemas import APIResponse
from services.survey_service import run_pipeline

router = APIRouter(prefix="/api/v1", tags=["survey"])

_PLANTILLAS_DIR  = Path(__file__).parent.parent.parent.parent.parent / "plantillas"
WORD_TEMPLATE    = _PLANTILLAS_DIR / "word" / "fase 2" / "plan_15_generado.docx"
ENCUESTA_DEFAULT = _PLANTILLAS_DIR / "excel" / "fase 2" / "Encuesta.xlsx"


def _get_temp_dir() -> Path:
    temp_dir = Path(tempfile.gettempdir()) / "bpae"
    temp_dir.mkdir(exist_ok=True)
    return temp_dir


@router.post(
    "/process-survey",
    response_model=APIResponse,
    summary="Procesar encuesta y generar documento Word con tabulación",
    description=(
        "Recibe Encuesta.xlsx, ejecuta pipeline Bronze→Silver→Gold "
        "y genera un Word con 16 tablas de frecuencia."
    ),
)
async def process_survey(
    file: UploadFile = File(
        default=None,
        description="Encuesta.xlsx. Si se omite, usa la encuesta por defecto del proyecto.",
    ),
):
    try:
        temp_dir = _get_temp_dir()

        # Archivo de encuesta
        if file is not None:
            encuesta_path = temp_dir / (file.filename or "encuesta_upload.xlsx")
            encuesta_path.write_bytes(await file.read())
        else:
            if not ENCUESTA_DEFAULT.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"No hay encuesta subida ni en la ruta default: {ENCUESTA_DEFAULT}",
                )
            encuesta_path = ENCUESTA_DEFAULT

        if not WORD_TEMPLATE.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Template Word no encontrado: {WORD_TEMPLATE}",
            )

        # Archivo temporal para el pipeline (se renombra al SQLite ID después)
        tmp_path = temp_dir / f"tabulacion_tmp_{int(time.time())}.docx"

        result = run_pipeline(
            encuesta_path=encuesta_path,
            template_path=WORD_TEMPLATE,
            output_path=tmp_path,
        )

        # Usar el SQLite survey_id como identificador único del archivo descargable
        sqlite_id   = result["survey_id"]
        final_path  = temp_dir / f"tabulacion_{sqlite_id}.docx"
        tmp_path.rename(final_path)

        return APIResponse(
            message="Encuesta procesada exitosamente",
            data={
                "survey_id"       : sqlite_id,
                "bronze_rows"     : result["bronze_rows"],
                "silver_questions": result["silver_questions"],
                "variable_names"  : result["variable_names"],
                "word_url"        : f"/api/v1/download/survey/{sqlite_id}/word",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar encuesta: {e}")


@router.get(
    "/download/survey/{survey_id}/word",
    summary="Descargar Word con tabulación generado",
)
async def download_survey_word(survey_id: int):
    file_path = _get_temp_dir() / f"tabulacion_{survey_id}.docx"
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Archivo no encontrado. Ejecute primero /process-survey",
        )
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"tabulacion_encuesta_{survey_id}.docx",
    )
