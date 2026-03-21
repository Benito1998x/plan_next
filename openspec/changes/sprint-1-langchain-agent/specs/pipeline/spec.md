# Pipeline Specification — Sprint 1 LangChain Agent

## Purpose

Defines behavior for the hybrid read/enrich/write pipeline:
`Input1Reader` (openpyxl label-scan), `Input1EnrichmentChain` (LangChain),
`ExcelWriter.fill_input1_template()`, and token tracking via `LogProcesamiento`.

---

## Requirements

### Requirement: Input1Reader — Label-Based Scanning

`Input1Reader` MUST scan Col A of both sheets (`INICIO`, `CONFIGURACIÓN METODOLÓGICA`)
to locate section anchors. It MUST NOT use hardcoded row indices.

All 9 sections across both sheets MUST be read. The reader MUST return a `raw_dict`
keyed by normalized field names regardless of the order labels appear in the file.

#### Scenario: All labels present — INICIO sheet

- GIVEN an `Input 1.xlsx` with all required Col A labels in the `INICIO` sheet
- WHEN `Input1Reader.scan_sheet("INICIO")` runs
- THEN `raw_dict` contains keys for sections 1–4 with non-None values for filled cells
- AND empty cells produce `None` values (not empty strings)

#### Scenario: All labels present — CONFIGURACIÓN METODOLÓGICA sheet

- GIVEN an `Input 1.xlsx` with all 5 subsections in the `CONFIGURACIÓN METODOLÓGICA` sheet
- WHEN `Input1Reader.scan_sheet("CONFIGURACIÓN METODOLÓGICA")` runs
- THEN `raw_dict` contains keys for all 5 subsections
- AND tabular subsections produce a list of dicts (one per data row)

#### Scenario: Label not found in sheet

- GIVEN a required label is absent from Col A in both sheets
- WHEN `Input1Reader` completes the full scan
- THEN the missing label's key is absent from `raw_dict`
- AND no exception is raised during scan (downstream validation raises the error)

#### Scenario: openpyxl load mode — read vs write

- GIVEN the same `Input 1.xlsx` file loaded for reading
- WHEN `load_workbook()` is called with `data_only=True`
- THEN formula cells resolve to their cached values
- AND the workbook MUST NOT be saved after reading (read-only semantics)

---

### Requirement: Input1EnrichmentChain — Normalize and Validate

`Input1EnrichmentChain` MUST accept `raw_dict` and return `enriched_dict` with:
- Ambiguous values normalized (e.g., "B2C" → "B2C", "business to consumer" → "B2C")
- Missing optional fields inferred where the LLM can do so with high confidence
- Fields that cannot be inferred left as `None`

The chain MUST be invoked within a `get_openai_callback()` context manager to capture token counts.

#### Scenario: Successful enrichment with token capture

- GIVEN a `raw_dict` with some ambiguous values and some None fields
- WHEN `Input1EnrichmentChain.invoke(raw_dict)` is called inside `get_openai_callback()`
- THEN `enriched_dict` is returned with normalized values
- AND `cb.prompt_tokens > 0` and `cb.completion_tokens > 0`
- AND `cb.total_cost >= 0`

#### Scenario: Enrichment with completely empty optional field

- GIVEN `raw_dict["motivaciones"]` is `None` and cannot be inferred from context
- WHEN the chain runs
- THEN `enriched_dict["motivaciones"]` is `None`
- AND no hallucinated value is substituted

#### Scenario: LangChain chain invocation is traced

- GIVEN `LANGCHAIN_TRACING_V2=true` and a valid `LANGCHAIN_API_KEY` in the environment
- WHEN `Input1EnrichmentChain.invoke()` runs
- THEN a trace appears in LangSmith under the configured project with run name `"input1_enrichment"`

---

### Requirement: Token Tracking in LogProcesamiento

Every call to `Input1EnrichmentChain` MUST produce exactly one `LogProcesamiento` row
with `actividad="input1_enrichment"` and the token/cost values from `get_openai_callback()`.

The row MUST be written regardless of whether the enrichment succeeds or fails.

#### Scenario: Successful enrichment — log written

- GIVEN `Input1EnrichmentChain.invoke()` completes without error
- WHEN the pipeline saves the log entry
- THEN a `LogProcesamiento` row exists with:
  - `tokens_prompt` = `cb.prompt_tokens`
  - `tokens_completion` = `cb.completion_tokens`
  - `costo_usd` = `cb.total_cost`
  - `actividad` = `"input1_enrichment"`
  - `plan_id` = the newly created plan's id

#### Scenario: Failed enrichment — log written with nulls

- GIVEN `Input1EnrichmentChain.invoke()` raises an exception
- WHEN the exception is caught by the pipeline error handler
- THEN a `LogProcesamiento` row is still written with `actividad="input1_enrichment"`
- AND `tokens_prompt`, `tokens_completion`, `costo_usd` are NULL

---

### Requirement: ExcelWriter.fill_input1_template()

`ExcelWriter.fill_input1_template()` MUST write all 5 sections of `enriched_dict`
back into a copy of `Input 1.xlsx` without altering cells outside the designated
write ranges (fonts, fills, dropdowns in non-written cells MUST be preserved).

#### Scenario: Output Excel preserves formatting

- GIVEN `enriched_dict` with all 5 sections populated
- WHEN `fill_input1_template(enriched_dict)` is called
- THEN the output `.xlsx` contains the enriched values in the correct label rows
- AND cells not targeted by the writer retain their original formatting

#### Scenario: Output file written to temp path and returned

- GIVEN a successful enrichment
- WHEN `fill_input1_template()` completes
- THEN the output file is saved to a deterministic temp path keyed by `plan_id`
- AND the path is accessible via `GET /api/v1/download/{plan_id}/excel`

#### Scenario: Read workbook and write workbook are separate loads

- GIVEN the same `Input 1.xlsx` source file
- WHEN the pipeline reads (via `Input1Reader`) and then writes (via `fill_input1_template`)
- THEN two separate `load_workbook()` calls are made: one with `data_only=True` (read) and one without (write)
- AND the read workbook is never saved

---

### Requirement: Code Deletion — Position-Based Reader

`ExcelReader`, `TemplateConfig`, and `excel_templates.yaml` MUST be removed.
`extraer_datos_plan` and `EXTRACT_SCHEMA` in `ai_agent.py` MUST be removed.
`infer_variable_names` in `ai_agent.py` MUST be retained.

#### Scenario: Deleted modules are not importable after Sprint 1

- GIVEN Sprint 1 code is merged
- WHEN any module attempts `from services.excel_reader import ExcelReader`
- THEN an `ImportError` is raised (module does not exist)
