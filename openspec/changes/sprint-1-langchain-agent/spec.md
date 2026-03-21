# Spec: Sprint 1 — Hybrid LangChain Pipeline for Input 1.xlsx

**Change**: sprint-1-langchain-agent
**Date**: 2026-03-21
**Status**: Ready for Design

---

## Domain: API (`apps/api/api/v1/`)

### Requirement: Template Download Endpoint

The system MUST expose `GET /api/v1/template/input1` returning `Input 1.xlsx` as an attachment.

#### Scenario: Template file exists
- GIVEN `Input 1.xlsx` is present in the templates directory
- WHEN `GET /api/v1/template/input1` is requested
- THEN status 200 with `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- AND `Content-Disposition: attachment; filename="Input 1.xlsx"`

#### Scenario: Template file missing
- GIVEN the template file is absent
- WHEN `GET /api/v1/template/input1` is requested
- THEN status 404 with `{"detail": "Template not found"}`

---

### Requirement: Plan Upload — Success

The system MUST expose `POST /api/v1/upload/plan` accepting `multipart/form-data` (`file: UploadFile`, `.xlsx` only).
On success the response MUST include `plan_id`, `sections_extracted` (5 keys), `tokens_prompt`, `tokens_completion`, `costo_usd`, `excel_url`, `word_url`.

#### Scenario: Valid xlsx uploaded
- GIVEN a well-formed `Input 1.xlsx` with all required Col A labels
- WHEN `POST /api/v1/upload/plan` receives the file
- THEN status 200 and `sections_extracted` = `["parametros_globales","productos_servicios","datos_negocio","buyer_persona","configuracion_metodologica"]`
- AND `plan_id` is a positive integer for the newly created `Plan` row

---

### Requirement: Plan Upload — Validation Errors

The endpoint MUST return HTTP 400 for: non-xlsx file, file exceeding max size, missing required label.

#### Scenario: Non-xlsx submitted
- GIVEN a `.csv` file
- WHEN uploaded to `POST /api/v1/upload/plan`
- THEN status 400 with `{"detail": "Only .xlsx files are accepted"}`

#### Scenario: Required label missing
- GIVEN an xlsx missing a required Col A label
- WHEN `Input1Reader` finishes scanning
- THEN status 400 with `{"detail": "Missing required field: <label_name>"}`

---

### Requirement: Plan Upload — Server Errors

The endpoint MUST return HTTP 500 on unrecoverable pipeline failure and MUST write a `LogProcesamiento` row even on failure.

#### Scenario: LLM call fails
- GIVEN the OpenAI API returns an error
- WHEN `Input1EnrichmentChain.invoke()` raises
- THEN status 500 with `{"detail": "Processing error: <message>"}`
- AND a `LogProcesamiento` row is written with `actividad="input1_enrichment"` and NULL token fields

---

### Requirement: Legacy Endpoint Preservation

`POST /upload-excel` and `POST /process-plan` MUST remain operational and return unchanged response shapes.

#### Scenario: Legacy endpoint after Sprint 1
- GIVEN Sprint 1 deployed
- WHEN `POST /upload-excel` is called with a valid payload
- THEN response is identical to pre-Sprint-1 behavior

---

## Domain: Pipeline (`apps/api/services/`)

### Requirement: Input1Reader — Label-Based Scanning

`Input1Reader` MUST scan Col A of both sheets by label, covering all 9 sections. Row indices MUST NOT be hardcoded. Missing labels produce absent keys in `raw_dict` (no exception during scan).

#### Scenario: All labels present — INICIO sheet
- GIVEN all required Col A labels in `INICIO`
- WHEN `Input1Reader.scan_sheet("INICIO")` runs
- THEN `raw_dict` has keys for sections 1–4 with non-None values for filled cells
- AND empty cells produce `None` (not empty strings)

#### Scenario: Label absent
- GIVEN a required label is missing from both sheets
- WHEN the full scan completes
- THEN the label's key is absent from `raw_dict` and no exception is raised

#### Scenario: Read workbook uses data_only=True
- GIVEN `Input 1.xlsx` is loaded for reading
- WHEN `load_workbook(data_only=True)` is called
- THEN formula cells resolve to cached values and the workbook is never saved

---

### Requirement: Input1EnrichmentChain — Normalize and Validate

`Input1EnrichmentChain` MUST accept `raw_dict`, return `enriched_dict` with ambiguous values normalized and unresolvable fields left as `None`. The call MUST be wrapped in `get_openai_callback()`.

#### Scenario: Successful enrichment with token capture
- GIVEN `raw_dict` with ambiguous values
- WHEN `invoke(raw_dict)` runs inside `get_openai_callback()`
- THEN `enriched_dict` is returned with normalized values
- AND `cb.prompt_tokens > 0`, `cb.completion_tokens > 0`, `cb.total_cost >= 0`

#### Scenario: Unresolvable optional field
- GIVEN `raw_dict["motivaciones"]` is `None` with no inferrable context
- WHEN the chain runs
- THEN `enriched_dict["motivaciones"]` is `None` (no hallucinated value)

#### Scenario: LangSmith tracing active
- GIVEN `LANGCHAIN_TRACING_V2=true` and valid `LANGCHAIN_API_KEY`
- WHEN `invoke()` runs
- THEN a trace appears in LangSmith with run name `"input1_enrichment"`

---

### Requirement: Token Tracking in LogProcesamiento

Every `Input1EnrichmentChain` call MUST produce exactly one `LogProcesamiento` row with `actividad="input1_enrichment"`. The row MUST be written on both success and failure.

#### Scenario: Successful enrichment — log written
- GIVEN `invoke()` completes without error
- WHEN the pipeline saves the log
- THEN a `LogProcesamiento` row has `tokens_prompt=cb.prompt_tokens`, `tokens_completion=cb.completion_tokens`, `costo_usd=cb.total_cost`, `actividad="input1_enrichment"`, `plan_id` set

#### Scenario: Failed enrichment — log written with nulls
- GIVEN `invoke()` raises
- WHEN the error handler runs
- THEN a `LogProcesamiento` row is written with `actividad="input1_enrichment"` and NULL token fields

---

### Requirement: ExcelWriter.fill_input1_template()

`fill_input1_template()` MUST write all 5 sections into a copy of `Input 1.xlsx` without altering cells outside write ranges. Read and write MUST use separate `load_workbook()` calls.

#### Scenario: Output preserves formatting
- GIVEN `enriched_dict` with all 5 sections
- WHEN `fill_input1_template(enriched_dict)` runs
- THEN targeted cells contain enriched values and non-targeted cells retain original formatting

#### Scenario: Separate load for read vs write
- GIVEN the same source file
- WHEN the pipeline reads then writes
- THEN read uses `load_workbook(data_only=True)` and write uses a separate `load_workbook()` without `data_only`

---

### Requirement: Code Deletion

`ExcelReader`, `TemplateConfig`, `excel_templates.yaml`, `extraer_datos_plan`, and `EXTRACT_SCHEMA` MUST be removed. `infer_variable_names` MUST be retained.

#### Scenario: Deleted modules not importable
- GIVEN Sprint 1 merged
- WHEN `from services.excel_reader import ExcelReader` is attempted
- THEN `ImportError` is raised

---

## Domain: Database (`apps/api/models/db/`)

### Requirement: New Table — DatosNegocio

MUST be created with 1:1 FK to `Plan` (unique `plan_id`). All content columns nullable. `created_at` non-nullable, set to UTC now.

#### Scenario: Table created additively
- GIVEN `DatosNegocio` registered in `__init__.py`
- WHEN `SQLModel.metadata.create_all(engine)` runs
- THEN table is created and no existing tables are modified

#### Scenario: Duplicate plan_id rejected
- GIVEN a `DatosNegocio` row for `plan_id=5` exists
- WHEN a second insert with `plan_id=5` is attempted
- THEN an integrity error is raised (UNIQUE constraint)

---

### Requirement: New Table — BuyerPersona

MUST be created with 1:1 FK to `Plan`. All content columns nullable.

#### Scenario: Empty section inserts null-content row
- GIVEN no data in buyer persona section of uploaded file
- WHEN pipeline saves `BuyerPersona`
- THEN a row is inserted with `plan_id` set and all content columns NULL without error

---

### Requirement: New Table — ConfiguracionMetodologica

MUST be created with 1:1 FK to `Plan`. `datos_adicionales` (TEXT) MUST store overflow subsection fields as JSON.

#### Scenario: Overflow fields go to datos_adicionales
- GIVEN all 5 subsections with extra fields beyond defined columns
- WHEN pipeline saves `ConfiguracionMetodologica`
- THEN overflow fields are serialized to `datos_adicionales` as JSON string

#### Scenario: datos_adicionales NULL when no overflow
- GIVEN all subsection data maps to defined columns
- WHEN pipeline saves
- THEN `datos_adicionales` is NULL

---

### Requirement: Migration Script — LogProcesamiento

`scripts/migrate_sprint1.py` MUST add `tokens_prompt` (INTEGER), `tokens_completion` (INTEGER), `costo_usd` (REAL), `actividad` (TEXT) to `LogProcesamiento` via `ALTER TABLE ADD COLUMN`. Script MUST be idempotent.

#### Scenario: Migration on existing plan.db
- GIVEN ~47 existing rows without the 4 new columns
- WHEN `migrate_sprint1.py` runs
- THEN all 4 columns added, existing rows have NULL in new columns, no existing data changes

#### Scenario: Idempotent re-run
- GIVEN columns already exist
- WHEN `migrate_sprint1.py` runs again
- THEN no error raised and no duplicate columns created

#### Scenario: Existing plans intact after migration
- GIVEN `plan.db` post-migration
- WHEN `SELECT * FROM plan` is executed
- THEN all 47 rows returned with original data unchanged

---

### Requirement: Model Exports

`models/db/__init__.py` MUST export `DatosNegocio`, `BuyerPersona`, `ConfiguracionMetodologica`.

#### Scenario: New models importable from package root
- GIVEN Sprint 1 in place
- WHEN `from models.db import DatosNegocio, BuyerPersona, ConfiguracionMetodologica`
- THEN no `ImportError` is raised
