"""
Sprint 3 API — Indicadores de Mercado

Endpoints:
  POST /api/v1/sprint3/process
      Procesa datos Gold de un survey y genera indicadores de mercado.
      Body: { "survey_id": int, "plan_id": int (opcional) }

  GET /api/v1/sprint3/download/{survey_id}/excel
      Descarga el Excel de indicadores generado.

  GET /api/v1/sprint3/download/{survey_id}/word
      Descarga el Word de indicadores generado.
"""

import json
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services.sprint3_service import run_sprint3

router = APIRouter(prefix="/api/v1/sprint3", tags=["sprint3"])

# Directorio de salida compartido (mismo que otros sprints)
_OUTPUT_DIR = Path(tempfile.gettempdir()) / "bpae_sprint3"
_INDEX_PATH = _OUTPUT_DIR / "index_sprint3.json"


class Sprint3Request(BaseModel):
    survey_id: int
    plan_id:   Optional[int] = None


@router.post("/process")
async def process_sprint3(request: Sprint3Request):
    """
    Genera indicadores de mercado desde los datos Gold de un survey.

    - Carga Bronze → Silver → Gold desde el survey_id
    - Calcula KPIs (aceptación, segmento etario, canal preferido, etc.)
    - Genera Excel + Word con los resultados
    - Retorna el JSON completo de indicadores
    """
    try:
        result = run_sprint3(
            survey_id=request.survey_id,
            plan_id=request.plan_id,
            output_dir=_OUTPUT_DIR,
        )
        return {
            "status":        "ok",
            "survey_id":     result["survey_id"],
            "plan_id":       result["plan_id"],
            "n_indicadores": result["n_indicadores"],
            "summary":       result["summary"],
            "indicadores":   result["indicadores"],
            "downloads": {
                "excel": f"/api/v1/sprint3/download/{request.survey_id}/excel",
                "word":  f"/api/v1/sprint3/download/{request.survey_id}/word",
            },
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Survey {request.survey_id} no encontrado en BD: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/download/{survey_id}/excel")
async def download_excel(survey_id: int):
    """Descarga el Excel de indicadores de mercado."""
    path = _get_file(survey_id, "excel")
    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=Path(path).name,
    )


@router.get("/download/{survey_id}/word")
async def download_word(survey_id: int):
    """Descarga el Word de indicadores de mercado."""
    path = _get_file(survey_id, "word")
    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=Path(path).name,
    )


def _get_file(survey_id: int, file_type: str) -> str:
    if not _INDEX_PATH.exists():
        raise HTTPException(status_code=404, detail="No se han generado archivos Sprint 3 aún")
    index = json.loads(_INDEX_PATH.read_text())
    entry = index.get(str(survey_id))
    if not entry:
        raise HTTPException(
            status_code=404,
            detail=f"No hay archivos generados para survey_id={survey_id}. Ejecute POST /process primero.",
        )
    file_path = entry.get(file_type)
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail=f"Archivo {file_type} no encontrado en disco")
    return file_path
