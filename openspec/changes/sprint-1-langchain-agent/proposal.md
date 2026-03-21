# Proposal: Sprint 1 — Hybrid LangChain Pipeline for Input 1.xlsx

**Date**: 2026-03-21
**Change**: sprint-1-langchain-agent
**Status**: Ready for Spec

---

## Intent

Replace the current position-based Excel reading and raw-OpenAI extraction with a hybrid pipeline:
openpyxl scans all sections of Input 1.xlsx by **label** (Col A), then a LangChain chain
normalizes/validates/infers ambiguous values. Additionally, the DB schema must be brought to
a correct state before Sprint 1 runs against it: 3 new tables, 4 new columns on
`LogProcesamiento`, and a controlled migration of the ~47 existing test plans.

The current code reads only 2 of 9 sections in Input 1.xlsx (sections 3–9 are ignored),
uses hardcoded row positions that will break on any layout change, has no token tracking,
and is missing `DatosNegocio`, `BuyerPersona`, and `ConfiguracionMetodologica` tables entirely.

---

## Scope

### In Scope

- **Input 1 reader**: new `Input1Reader` service — label-based scan of ALL sections across
  both sheets (INICIO: 4 sections, CONFIGURACION METODOLOGICA: 5 subsections)
- **LangChain enrichment chain**: `Input1EnrichmentChain` — 1 LLM call post-read to
  normalize + infer + validate the extracted dict
- **Token tracking**: extend `LogProcesamiento` with `tokens_prompt`, `tokens_completion`,
  `costo_usd`, `actividad`; use `get_openai_callback()` in the chain call
- **3 new DB tables**: `DatosNegocio`, `BuyerPersona`, `ConfiguracionMetodologica`
- **DB migration**: script to add new columns to `LogProcesamiento`; new tables are additive
- **Output**: `fill_input1_template()` in `ExcelWriter` — writes all sections back into
  Input 1 format preserving formatting
- **Endpoints**: `GET /api/v1/template/input1` + `POST /api/v1/upload/plan`
- **Dependencies**: add `langchain>=0.3`, `langchain-openai>=0.2`, `langsmith>=0.1`
- **Deletion**: remove `ExcelReader` (position-based), `TemplateConfig`, `excel_templates.yaml`,
  and the `extraer_datos_plan` function from `ai_agent.py` (keep `infer_variable_names`)

### Out of Scope

- Full LangChain AgentExecutor / ReAct loop for structural discovery (deferred — not needed)
- Alembic setup (manual migration script is sufficient at this stage)
- Word output update for new sections (Sprint 3 concern)
- Any changes to Survey (Sprint 2) or Tabulation (Sprint 3) modules
- ParametrosGlobales `metadata` JSON column (premature — no concrete use case yet)

---

## Architecture: Hybrid Pipeline

```
POST /api/v1/upload/plan
        │
        ▼
┌─────────────────────┐
│ FileValidator       │  validate extension + size
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Input1Reader        │  openpyxl label-scan (deterministic)
│  - scan_sheet()     │  ← scans Col A per sheet for section anchors
│  - read_kv()        │  ← label → Col B value
│  - read_table()     │  ← header row detection + N data rows
└────────┬────────────┘
         │ raw_dict (may have None / ambiguous values)
         ▼
┌─────────────────────────────┐
│ Input1EnrichmentChain       │  LangChain (1 LLM call)
│  with get_openai_callback() │  normalize + infer + validate
└────────┬────────────────────┘
         │ enriched_dict + token counts
         ▼
┌────────────────────┐
│ DB save            │  Plan + ParametrosGlobales + Producto
│                    │  + DatosNegocio + BuyerPersona
│                    │  + ConfiguracionMetodologica
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ ExcelWriter        │  fill_input1_template()
│ fill_input1_template│  writes all sections back into Input 1 copy
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ LogProcesamiento   │  tokens_prompt, tokens_completion, costo_usd, actividad
└────────────────────┘
```

---

## Database: Current State and Required Changes

### Problem with Existing plan.db (~47 plans)

The existing records are valid test data under the current schema. Migration strategy:
1. New tables (`DatosNegocio`, `BuyerPersona`, `ConfiguracionMetodologica`) are purely
   additive — SQLModel `create_all()` creates them without touching existing tables.
2. `LogProcesamiento` needs 4 new columns. SQLite supports `ALTER TABLE ADD COLUMN`
   for nullable columns with defaults — no DROP/RECREATE required.
3. Existing 47 plans keep all their data. New columns default to NULL.
4. No Alembic needed: a `scripts/migrate_sprint1.py` runs the 4 ALTER TABLE statements.

### Table: LogProcesamiento — Columns to ADD

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `tokens_prompt` | INTEGER | YES | NULL | from `get_openai_callback()` |
| `tokens_completion` | INTEGER | YES | NULL | from `get_openai_callback()` |
| `costo_usd` | FLOAT | YES | NULL | calculated: total_tokens × rate |
| `actividad` | VARCHAR | YES | NULL | e.g. "input1_enrichment" |

SQL (run via migrate_sprint1.py):
```sql
ALTER TABLE logprocesamiento ADD COLUMN tokens_prompt INTEGER;
ALTER TABLE logprocesamiento ADD COLUMN tokens_completion INTEGER;
ALTER TABLE logprocesamiento ADD COLUMN costo_usd REAL;
ALTER TABLE logprocesamiento ADD COLUMN actividad TEXT;
```

### New Table: DatosNegocio

| Column | Type | Nullable | FK | Notes |
|--------|------|----------|----|-------|
| `id` | INTEGER PK | NO | — | |
| `plan_id` | INTEGER | NO | `plan.id` unique | 1:1 with Plan |
| `descripcion_negocio` | TEXT | YES | — | |
| `mision` | TEXT | YES | — | |
| `vision` | TEXT | YES | — | |
| `propuesta_valor` | TEXT | YES | — | |
| `ventaja_competitiva` | TEXT | YES | — | |
| `problema_que_resuelve` | TEXT | YES | — | |
| `modelo_negocio` | VARCHAR(100) | YES | — | |
| `etapa_negocio` | VARCHAR(50) | YES | — | borrador/operando/etc |
| `created_at` | DATETIME | NO | — | utcnow |
| `updated_at` | DATETIME | YES | — | |

### New Table: BuyerPersona

| Column | Type | Nullable | FK | Notes |
|--------|------|----------|----|-------|
| `id` | INTEGER PK | NO | — | |
| `plan_id` | INTEGER | NO | `plan.id` unique | 1:1 with Plan |
| `nombre_persona` | VARCHAR(100) | YES | — | |
| `edad_rango` | VARCHAR(50) | YES | — | "25-35" |
| `genero` | VARCHAR(50) | YES | — | |
| `ocupacion` | VARCHAR(100) | YES | — | |
| `nivel_ingresos` | VARCHAR(100) | YES | — | |
| `ubicacion` | VARCHAR(100) | YES | — | |
| `motivaciones` | TEXT | YES | — | |
| `frustraciones` | TEXT | YES | — | |
| `created_at` | DATETIME | NO | — | utcnow |

### New Table: ConfiguracionMetodologica

| Column | Type | Nullable | FK | Notes |
|--------|------|----------|----|-------|
| `id` | INTEGER PK | NO | — | |
| `plan_id` | INTEGER | NO | `plan.id` unique | 1:1 with Plan |
| `metodologia_proyeccion` | VARCHAR(100) | YES | — | |
| `tipo_mercado` | VARCHAR(100) | YES | — | |
| `segmento_objetivo` | TEXT | YES | — | |
| `canal_distribucion` | VARCHAR(100) | YES | — | |
| `estrategia_precio` | VARCHAR(100) | YES | — | |
| `datos_adicionales` | TEXT | YES | — | JSON blob for flexible fields |
| `created_at` | DATETIME | NO | — | utcnow |

> `datos_adicionales` (JSON text) handles the 5-subsection variability of
> CONFIGURACIÓN METODOLÓGICA without over-normalizing at this stage.

### ParametrosGlobales — No Changes

The current 13 fields match Input 1 sections 1 & 2. No changes needed.
`metadata` JSON column is deferred (no confirmed use case).

---

## Endpoints

### GET /api/v1/template/input1

Returns the Input 1.xlsx file as a download so clients can get a fresh template.

```
Response: FileResponse
  Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
  Content-Disposition: attachment; filename="Input 1.xlsx"
  Status: 200 OK | 404 if template file not found
```

### POST /api/v1/upload/plan

Uploads a filled Input 1.xlsx, runs the hybrid pipeline, returns plan_id + download URLs.

```
Request: multipart/form-data
  file: UploadFile  (required, .xlsx only)

Response 200:
{
  "plan_id": int,
  "nombre": str,
  "sections_extracted": ["parametros_globales", "productos_servicios",
                          "datos_negocio", "buyer_persona",
                          "configuracion_metodologica"],
  "tokens_prompt": int,
  "tokens_completion": int,
  "costo_usd": float,
  "excel_url": "/api/v1/download/{plan_id}/excel",
  "word_url": "/api/v1/download/{plan_id}/word"
}

Response 400: ValidationError (bad file, missing required fields)
Response 500: ProcessingError (read/write/LLM failure)
```

---

## Token Tracking Integration

`Input1EnrichmentChain` wraps the LLM call with `get_openai_callback()`:

```python
from langchain_community.callbacks import get_openai_callback

with get_openai_callback() as cb:
    result = chain.invoke(raw_dict)

log.tokens_prompt = cb.prompt_tokens
log.tokens_completion = cb.completion_tokens
log.costo_usd = cb.total_cost
log.actividad = "input1_enrichment"
```

LangSmith tracing is automatic via `LANGCHAIN_TRACING_V2=true` in `.env`.

---

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/api/services/input1_reader.py` | **New** | Replaces ExcelReader for Input 1 format |
| `apps/api/services/input1_enrichment_chain.py` | **New** | LangChain enrichment chain |
| `apps/api/services/excel_reader.py` | **Delete** | Position-based reader — removed |
| `apps/api/services/template_config.py` | **Delete** | No longer needed |
| `apps/api/config/excel_templates.yaml` | **Delete** | Replaced by label-scan approach |
| `apps/api/services/ai_agent.py` | **Modified** | Remove `extract_plan_data` + `EXTRACT_SCHEMA`; keep `infer_variable_names` |
| `apps/api/services/excel_writer.py` | **Modified** | Add `fill_input1_template()` for all sections |
| `apps/api/models/db/plan_data.py` | **Modified** | Add `DatosNegocio`, `BuyerPersona`, `ConfiguracionMetodologica` |
| `apps/api/models/db/trazabilidad.py` | **Modified** | Add 4 columns to `LogProcesamiento` |
| `apps/api/models/db/__init__.py` | **Modified** | Export 3 new models |
| `apps/api/api/v1/upload.py` | **Modified** | Add `GET /template/input1`, `POST /upload/plan`; keep legacy endpoints |
| `apps/api/scripts/migrate_sprint1.py` | **New** | ALTER TABLE migration for LogProcesamiento |
| `apps/api/requirements.txt` | **Modified** | Add langchain, langchain-openai, langsmith |

---

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| CONFIGURACIÓN METODOLÓGICA subsection format unknown until file is read | High | Read actual Input 1.xlsx before implementing `Input1Reader`; use `datos_adicionales` JSON as escape hatch |
| `fill_input1_template()` cell addresses for sections 3-4 unknown | High | Inspect Input 1.xlsx row positions before mapping `_DATOS_NEGOCIO_CELLS` / `_BUYER_PERSONA_CELLS` |
| LangChain 0.3 API breaking changes vs project team expectations | Med | Pin exact versions in requirements; document import paths in code comments |
| openpyxl `load_workbook()` + `save()` corrupts dropdowns in Input 1 | Med | Test `keep_vba=False, data_only=True` for READ; use separate load (no `data_only`) for WRITE |
| SQLite ALTER TABLE on columns with FK constraint | Low | New columns are all nullable with no FK — ALTER TABLE ADD COLUMN is safe |
| Existing 47 test plans have incomplete data for new sections | Low | New tables have all columns nullable; no backfill required |

---

## Files to DELETE (from old Sprint 1)

| File | Reason |
|------|--------|
| `apps/api/services/excel_reader.py` | Position-based, replaced by `input1_reader.py` |
| `apps/api/services/template_config.py` | YAML-driven config no longer needed |
| `apps/api/config/excel_templates.yaml` | Config file for deleted service |

> `table_detector.py` can be kept as reference or deleted — it's not called by new endpoints.

---

## Rollback Plan

1. **Git**: All changes are on feature branch. Rollback = `git checkout master`.
2. **DB**: New tables are additive. To undo: `DROP TABLE IF EXISTS datosnegocio; DROP TABLE IF EXISTS buyerpersona; DROP TABLE IF EXISTS configuracionmetodologica;`
3. **LogProcesamiento columns**: SQLite has no `DROP COLUMN` before 3.35. Workaround: create a backup of plan.db before running `migrate_sprint1.py`. Restore from backup if needed.
4. **Endpoints**: Legacy `/upload-excel` and `/process-plan` are kept intact. If new endpoints fail, clients fall back to legacy.
5. **Dependencies**: `pip uninstall langchain langchain-openai langsmith` restores previous state.

---

## Dependencies

- `Input 1.xlsx` must be physically inspected to confirm row positions for sections 3-4
  and subsection layout of CONFIGURACIÓN METODOLÓGICA sheet (Task 0 in implementation)
- LangSmith project configured in `.env` (`LANGCHAIN_PROJECT`, `LANGCHAIN_API_KEY`)
- `OPENAI_API_KEY` present (already in use by `ai_agent.py`)

---

## Success Criteria

- [ ] `POST /api/v1/upload/plan` accepts Input 1.xlsx and returns `plan_id` with all 5
      sections populated in DB
- [ ] `GET /api/v1/template/input1` returns downloadable Input 1.xlsx
- [ ] `LogProcesamiento` records include `tokens_prompt`, `tokens_completion`, `costo_usd`
      after each upload
- [ ] Output Excel preserves Input 1 formatting (fonts, fills, dropdowns untouched in
      non-written cells)
- [ ] All 3 new DB tables exist with correct schema after `migrate_sprint1.py` runs
- [ ] Existing 47 plans in plan.db remain accessible and unmodified
- [ ] Legacy `/upload-excel` and `/process-plan` still respond correctly
- [ ] LangSmith shows traces for `input1_enrichment` activity
