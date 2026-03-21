# Design: Sprint 1 — Hybrid LangChain Pipeline for Input 1.xlsx

**Change**: sprint-1-langchain-agent
**Date**: 2026-03-21
**Based on**: proposal.md

---

## Technical Approach

Label-based openpyxl scan (deterministic, no LLM tokens) feeds a raw dict into a single
LangChain chain with structured Pydantic output, which then persists to SQLite via
SQLModel and fills back a copy of Input 1.xlsx. The existing endpoint scaffolding in
`upload.py` (router, `FileValidator`, `FileResponse`, `_get_temp_dir`) is reused;
legacy routes remain intact.

---

## Architecture Decisions

| Decision | Choice | Alternatives Rejected | Rationale |
|----------|--------|-----------------------|-----------|
| Excel scan strategy | Label scan (col A) per sheet | Position-based (current), LangChain cell detection | Deterministic; zero LLM cost for structural parsing; resilient to row insertion |
| LLM integration layer | LangChain `ChatOpenAI` + `PydanticOutputParser` | Raw OpenAI SDK (current `ai_agent.py`) | `get_openai_callback()` only works in LangChain context; LangSmith tracing is automatic |
| Structured output | Pydantic model (`PlanData`) | JSON string + manual parse | Validation is free; type-safe handoff to DB layer |
| One chain vs multiple | Single `Input1EnrichmentChain` call | Separate chain per section | 9 sections → 9 calls is 9× cost; normalization context is holistic |
| DB migration tool | Manual `scripts/migrate_sprint1.py` | Alembic | No existing Alembic setup; 4 nullable ALTER TABLE ADD COLUMN calls are trivially safe on SQLite |
| New table persistence | SQLModel `create_all()` (additive) | DROP/RECREATE | 47 existing test plans must survive; new tables are purely additive |
| Excel write strategy | Separate `load_workbook()` for read vs write | Single load with `data_only=False` | `data_only=True` needed to read formula results; write pass must NOT strip dropdowns |
| Token tracking | `get_openai_callback()` context manager | Manual token counting | Officially supported LangChain pattern; captures prompt + completion + cost atomically |

---

## Data Flow

```
POST /api/v1/upload/plan
        │
        ▼
FileValidator.validate_upload()   ← .xlsx only, size limit
        │ bytes saved to /tmp/bpae/
        ▼
Input1Reader.read(path)
  ├─ load_workbook(data_only=True)
  ├─ INICIO sheet: scan_section() × 4  → kv + table dicts
  └─ CONFIG METOD. sheet: scan_section() × 5 → kv dicts
        │ raw_dict: {sección: {label: value}}  — may have None/ambiguous
        ▼
Input1EnrichmentChain.invoke(raw_dict)
  └─ with get_openai_callback() as cb:
       ChatOpenAI → PydanticOutputParser → PlanData
        │ enriched: PlanData  +  cb.{prompt_tokens, completion_tokens, total_cost}
        ▼
_save_to_database(session, plan_data)
  ├─ Plan (insert)
  ├─ ParametrosGlobales (insert)
  ├─ Producto × N (insert)
  ├─ DatosNegocio (insert)
  ├─ BuyerPersona (insert)
  └─ ConfiguracionMetodologica (insert)
        │ plan_id
        ▼
ExcelWriter.fill_input1_template(plan_id, plan_data)
  └─ load_workbook(INPUT1_TEMPLATE)  ← no data_only — preserves dropdowns
     write all sections → save to /tmp/bpae/input1_{plan_id}.xlsx
        │
        ▼
LogProcesamiento (insert)
  └─ tokens_prompt, tokens_completion, costo_usd, actividad="input1_enrichment"
        │
        ▼
Response 200: {plan_id, sections_extracted, tokens_*, costo_usd, excel_url, word_url}
```

---

## Sequence Diagram: POST /api/v1/upload/plan

```
Client          upload.py          Input1Reader    EnrichChain      DB Session     ExcelWriter
  │                │                    │               │                │               │
  │─POST /upload/plan──►               │               │                │               │
  │                │─validate()─────►  │               │                │               │
  │                │─read(tmp_path)──► │               │                │               │
  │                │◄── raw_dict ──────│               │                │               │
  │                │─invoke(raw_dict)──────────────►   │                │               │
  │                │◄── PlanData + cb ─────────────────│                │               │
  │                │─save(plan_data)───────────────────────────────►    │               │
  │                │◄── plan_id ───────────────────────────────────────│               │
  │                │─fill_template(plan_id, plan_data)─────────────────────────────►   │
  │                │◄── output_path ────────────────────────────────────────────────────│
  │                │─log(plan_id, cb, "input1_enrichment")─────────►   │               │
  │◄─ 200 JSON ────│               │               │                │               │
```

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `apps/api/services/input1_reader.py` | Create | Label-based scanner for INICIO + CONFIG METODOLÓGICA sheets |
| `apps/api/services/input1_enrichment_chain.py` | Create | LangChain chain: raw dict → `PlanData` Pydantic model + token callback |
| `apps/api/models/pydantic/plan_data_schema.py` | Create | `PlanData` Pydantic model used as chain output and DB input |
| `apps/api/scripts/migrate_sprint1.py` | Create | 4× ALTER TABLE ADD COLUMN on `logprocesamiento` |
| `apps/api/services/excel_reader.py` | Delete | Position-based reader — fully replaced |
| `apps/api/services/template_config.py` | Delete | YAML-driven config no longer needed |
| `apps/api/config/excel_templates.yaml` | Delete | Config file for deleted service |
| `apps/api/services/ai_agent.py` | Modify | Remove `extract_plan_data` + `EXTRACT_SCHEMA`; keep `infer_variable_names` |
| `apps/api/services/excel_writer.py` | Modify | Add `fill_input1_template(plan_id, plan_data, output_path)` method |
| `apps/api/models/db/plan_data.py` | Modify | Add `DatosNegocio`, `BuyerPersona`, `ConfiguracionMetodologica` SQLModel tables; add `Relationship` back-refs on `Plan` |
| `apps/api/models/db/trazabilidad.py` | Modify | Add 4 fields to `LogProcesamiento`: `tokens_prompt`, `tokens_completion`, `costo_usd`, `actividad` |
| `apps/api/models/db/__init__.py` | Modify | Export 3 new models |
| `apps/api/api/v1/upload.py` | Modify | Add `GET /template/input1` + `POST /upload/plan`; remove `reader = ExcelReader()` instantiation; keep legacy routes |
| `apps/api/requirements.txt` | Modify | Add `langchain>=0.3`, `langchain-openai>=0.2`, `langsmith>=0.1` |

---

## Interfaces / Contracts

### PlanData (Pydantic — chain output + DB input)

```python
class PlanData(BaseModel):
    # Plan core
    nombre: str
    rubro: str
    ciudad: str
    departamento: str
    estado: str = "borrador"
    # ParametrosGlobales
    pais: str = "Bolivia"
    moneda_codigo: str = "Bs"
    tipo_cambio_usd: float = 6.96
    tasa_inflacion_anual: float = 2.0
    horizonte_anios: int = 5
    anio_base: int = 2025
    anio_inicio_operaciones: int = 2026
    impuesto_iue: float = 25.0
    impuesto_it: float = 3.0
    # Productos
    productos: list[ProductoData]
    # DatosNegocio
    descripcion_negocio: Optional[str]
    mision: Optional[str]
    vision: Optional[str]
    propuesta_valor: Optional[str]
    ventaja_competitiva: Optional[str]
    problema_que_resuelve: Optional[str]
    modelo_negocio: Optional[str]
    etapa_negocio: Optional[str]
    # BuyerPersona
    nombre_persona: Optional[str]
    edad_rango: Optional[str]
    genero: Optional[str]
    ocupacion: Optional[str]
    nivel_ingresos: Optional[str]
    ubicacion: Optional[str]
    motivaciones: Optional[str]
    frustraciones: Optional[str]
    # ConfiguracionMetodologica
    metodologia_proyeccion: Optional[str]
    tipo_mercado: Optional[str]
    segmento_objetivo: Optional[str]
    canal_distribucion: Optional[str]
    estrategia_precio: Optional[str]
    datos_adicionales: Optional[str]  # JSON blob
```

### Input1Reader public API

```python
class Input1Reader:
    def read(self, path: Path) -> dict:
        """Returns raw_dict keyed by section slug."""

    def _scan_section(self, ws: Worksheet, section_title: str) -> int:
        """Returns row index of the header row below section_title anchor in col A."""

    def _extract_kv(self, ws: Worksheet, header_row: int) -> dict:
        """Returns {label: value} from col A + B until next empty col A."""

    def _extract_table(self, ws: Worksheet, header_row: int) -> list[dict]:
        """Returns list of row dicts using col A header labels."""
```

### New DB columns on LogProcesamiento

```python
tokens_prompt: Optional[int] = Field(default=None)
tokens_completion: Optional[int] = Field(default=None)
costo_usd: Optional[float] = Field(default=None)
actividad: Optional[str] = Field(default=None)
```

### New endpoints (added to existing router in upload.py)

```
GET  /api/v1/template/input1
     → FileResponse (Input 1.xlsx) | 404

POST /api/v1/upload/plan
     body: multipart/form-data  file: UploadFile (.xlsx)
     → 200 {plan_id, nombre, sections_extracted, tokens_prompt,
             tokens_completion, costo_usd, excel_url, word_url}
     → 400 ValidationError
     → 500 ProcessingError
```

---

## DB Schema: New Tables

All three tables follow the existing `plan_data.py` pattern: SQLModel, `table=True`,
`plan_id` as `foreign_key="plan.id"` with `unique=True` (1:1 with Plan).

`Plan` model gains three new `Relationship` fields:
```python
datos_negocio: Optional["DatosNegocio"] = Relationship(back_populates="plan")
buyer_persona: Optional["BuyerPersona"] = Relationship(back_populates="plan")
config_metodologica: Optional["ConfiguracionMetodologica"] = Relationship(back_populates="plan")
```

`ConfiguracionMetodologica.datos_adicionales` is a `TEXT` column storing JSON for
flexible subsection fields — avoids over-normalizing 5 subsections at experimentation stage.

---

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `Input1Reader._scan_section()`, `_extract_kv()`, `_extract_table()` | pytest + openpyxl in-memory workbook fixture |
| Unit | `Input1EnrichmentChain` token capture | Mock `get_openai_callback()` + mock LLM response |
| Unit | `PlanData` Pydantic validation (required fields, type coercion) | pytest parametrize |
| Integration | `POST /api/v1/upload/plan` happy path | FastAPI `TestClient` + real Input 1.xlsx fixture |
| Integration | `GET /api/v1/template/input1` returns file | `TestClient` + assert content-type |
| Integration | Legacy `/upload-excel` still works post-refactor | Existing tests must still pass |

Test files: `apps/api/tests/test_input1_reader.py`, `apps/api/tests/test_upload_plan.py`

---

## Migration / Rollout

1. Run `scripts/migrate_sprint1.py` ONCE before first request to new endpoints.
   Script executes 4 `ALTER TABLE logprocesamiento ADD COLUMN` statements via SQLite raw
   connection — safe on nullable columns, idempotent if wrapped in `IF NOT EXISTS` check.
2. New SQLModel tables (`DatosNegocio`, `BuyerPersona`, `ConfiguracionMetodologica`) are
   created by the existing `SQLModel.metadata.create_all(engine)` call at app startup —
   no extra step needed.
3. Backup `apps/api/data/plan.db` before running migration (rollback path per proposal).
4. Legacy endpoints remain; no client-side changes required.

---

## Open Questions

- [ ] Confirm exact row layout of `CONFIGURACIÓN METODOLÓGICA` sheet in Input 1.xlsx before
      implementing `_scan_section()` — 5 subsections may not all use col A anchors uniformly.
- [ ] Verify `openpyxl` dropdown preservation: test `keep_vba=False` write pass against a
      sheet that has Data Validation lists before committing `fill_input1_template()`.
- [ ] Decide whether `table_detector.py` should be deleted or kept as dead code reference.
