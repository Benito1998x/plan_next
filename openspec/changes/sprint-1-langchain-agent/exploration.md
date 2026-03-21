# Exploration: sprint-1-langchain-agent

**Date**: 2026-03-21
**Change**: Rewrite Sprint 1 to use a LangChain agent that reads Input 1.xlsx dynamically (by text label, not cell position), saves data to DB, and generates a filled output Excel.

---

## Current State

### What exists today

The current Sprint 1 implementation uses two approaches simultaneously — and neither fully satisfies the new requirement:

1. **`excel_reader.py` + `template_config.py` + `excel_templates.yaml`**
   - Reads by **cell position** (row numbers from YAML config), not by text label.
   - `ExcelReader._read_key_value()` uses `start_row` + field index to get `B{row}` — completely position-based.
   - `ExcelReader._read_table()` uses fixed `data_start_row` / `data_end_row` integers from YAML.
   - Config (`excel_templates.yaml`) only covers 2 sections: `parametros_globales` (13 fields, rows 4–16) and `productos_servicios` (table, rows 20–29).
   - Does NOT cover sections 3 (Datos del Negocio), 4 (Buyer Persona), or CONFIGURACIÓN METODOLÓGICA.

2. **`table_detector.py`** (used in `upload-excel` endpoint)
   - Detects sections by scanning Col A for known title strings — this IS label-based scanning.
   - Only knows 2 sections (`parametros_globales`, `productos_servicios`).
   - Returns row ranges; actual cell reading still done by column position thereafter.

3. **`ai_agent.py`** (current direct OpenAI approach)
   - Uses raw OpenAI SDK with function calling (`extraer_datos_plan` schema).
   - Only extracts 4 fields: `nombre`, `rubro`, `ciudad`, `productos`.
   - No token tracking. No LangSmith integration.
   - No LangChain whatsoever — no chains, no tools, no agent framework.

4. **`excel_writer.py`** — has TWO modes:
   - `write_file()`: Creates a NEW workbook from scratch using TemplateConfig structure — DOES NOT preserve Input 1 format/styling.
   - `fill_template()`: Opens an EXISTING xlsx, writes to hardcoded cells (`_PARAM_CELLS` dict, `_PRODUCTOS_FILA_INICIO`) — position-based, only handles 13 params + products, NO new sections.

5. **DB models (current)**
   - `Plan`, `ParametrosGlobales`, `Producto`, `VersionPlan` — covers sections 1 & 2 of Input 1 only.
   - `LogProcesamiento` — has `archivo_entrada`, `estado`, `inicio`, `fin`, `duracion_segundos`. **Missing**: `tokens_prompt`, `tokens_completion`, `costo_usd`, `actividad`.
   - NO `DatosNegocio`, `BuyerPersona`, or `ConfiguracionMetodologica` tables.

6. **Endpoints (current)**
   - `POST /api/v1/process-plan` — accepts JSON body, calls `AIAgent.extract_plan_data()`.
   - `POST /api/v1/upload-excel` — accepts xlsx upload, uses `TableDetector` + `ExcelReader`.
   - No `GET /template/input1` endpoint exists.
   - No `POST /upload/plan` endpoint exists (proposed new endpoint).

7. **requirements.txt** — `langchain` and `langsmith` are NOT in requirements. Only `openai>=1.50.0`. LangSmith env var may already exist in `.env` but the library isn't installed.

---

## Affected Areas

- `apps/api/services/excel_reader.py` — replace with LangChain agent approach
- `apps/api/services/ai_agent.py` — replace with LangChain agent
- `apps/api/services/excel_writer.py` — keep `fill_template()`, extend to write new sections (DatosNegocio, BuyerPersona, ConfigMetodologica)
- `apps/api/services/template_config.py` — may be simplified or sidelined; TemplateConfig only covers v1/2/3 formats, not Input 1 full structure
- `apps/api/config/excel_templates.yaml` — extend with new sections OR deprecate in favor of agent-driven schema
- `apps/api/models/db/trazabilidad.py` — extend `LogProcesamiento` with 4 new columns
- `apps/api/models/db/plan_data.py` — add 3 new tables: `DatosNegocio`, `BuyerPersona`, `ConfiguracionMetodologica`
- `apps/api/models/db/__init__.py` — export new models
- `apps/api/api/v1/upload.py` — add `GET /template/input1` + `POST /upload/plan`, deprecate or keep legacy endpoints
- `apps/api/main.py` — register new router if separate
- `apps/api/requirements.txt` — add `langchain`, `langchain-openai`, `langsmith`
- `data/Input 1.xlsx` — potentially add `_SCHEMA` helper sheet

---

## Specific Question Answers

### Q1: Can `excel_writer.py` generate output in the same Input 1 format?

**No, not as-is.** The `fill_template()` method DOES open and modify the existing Input 1 file structure, which is the right approach — it preserves all original formatting, dropdowns, and styling. BUT it only handles the 13 `ParametrosGlobales` fields (hardcoded in `_PARAM_CELLS`) and the products table. It does NOT write to:
- Section 3 (Datos del Negocio — 8 fields)
- Section 4 (Buyer Persona — 8 fields)
- Sheet 2: CONFIGURACIÓN METODOLÓGICA (5 subsections)

**Solution**: Extend `fill_template()` (or create `fill_input1_template()`) to accept a fuller data dict and write the additional sections. The method is well-structured for this extension — just add more `_CELL_MAP` entries for the new sections once we know their actual row positions from Input 1.xlsx.

### Q2: What's the fastest way to add the `_SCHEMA` sheet without breaking existing Input 1 structure?

`openpyxl.load_workbook()` then `wb.create_sheet("_SCHEMA")` is non-destructive — it appends a new sheet without touching existing sheets. The `_SCHEMA` sheet would contain a compact text representation of section anchors (e.g., "INICIO!A3=Parámetros Globales", "INICIO!A17=Datos del Negocio") that the LangChain agent reads FIRST to locate sections before scanning the main data sheets.

**Risk**: The `_SCHEMA` sheet must be hidden (`ws.sheet_state = 'hidden'`) to avoid confusing end users who open Input 1 in Excel.

### Q3: How should LangChain tools handle Products table (multiple rows) vs key-value sections?

These are fundamentally different data shapes:
- **Key-value sections** (Params, Datos Negocio, Buyer Persona): Scan Col A for label text → read Col B for value. The LangChain `extract_field(section_anchor, label_text)` tool works perfectly — it searches downward from the anchor row until it finds the label.
- **Products table**: Has a header row (`N°`, `Nombre del Producto`, `Unidad de Medida`, `Peso/Vol`) and N data rows below. A separate `extract_table(section_anchor, expected_headers)` tool should detect the header row, identify column positions dynamically, then read all non-empty rows.

The critical design decision: tools should return **structured dicts**, not raw cell strings. The agent's job is to call the right tool per section type, not to parse raw text.

**For CONFIGURACIÓN METODOLÓGICA**: This sheet has 5 subsections, each potentially being a mix of key-value and nested structures. The agent needs a `list_subsections(sheet_name)` tool to enumerate what's there before extracting.

### Q4: What validation rules in `validators.py` can be reused?

`validators.py` is a `FileValidator` class — it handles file-level validation only:
- `validate_extension()` — reuse as-is for the upload endpoint
- `validate_size()` — reuse as-is
- `validate_upload()` — reuse as-is for `POST /upload/plan`

**Not relevant for the LangChain agent**: validators.py does NOT validate field values (no business rules). The new approach should add a data-level validator step AFTER agent extraction (e.g., `nombre` required, numeric fields within valid ranges). This can live in a new `services/input1_validator.py` or inline in the service layer.

The `ExcelReader.validate_required_fields()` method can be adapted for the new sections.

---

## Approaches

### Approach 1: Full LangChain Agent with Tool Calling (Recommended)

Build a `LangChain AgentExecutor` with 5 custom tools:
- `read_sheet_names(wb_path)` → list sheets
- `find_section(sheet, anchor_label)` → returns start row of section
- `extract_field(sheet, start_row, label_text)` → scans Col A downward, returns Col B value
- `extract_table(sheet, start_row)` → detects header row + reads all data rows
- `list_subsections(sheet)` → for CONFIGURACIÓN METODOLÓGICA, finds subsection headers

The agent receives a prompt like: "Extract all fields from Input 1.xlsx. Start with the _SCHEMA sheet to locate section anchors, then extract each section." It calls tools iteratively, tracks what it found, and returns a structured JSON.

Token tracking via `get_openai_callback()` context manager in LangChain.

**Pros**: True label-based reading; robust to row-position changes; LangSmith tracing works natively; `get_openai_callback()` gives exact token counts
**Cons**: More tokens per extraction (LLM loop overhead); requires `langchain`, `langchain-openai` deps; slower than pure openpyxl read; potential for agent to get confused on complex CONFIGURACIÓN METODOLÓGICA subsections
**Effort**: High

### Approach 2: Hybrid — openpyxl Label Scan + LangChain for Enrichment

Keep the `TableDetector` pattern (label scanning with openpyxl, no LLM for structural discovery), but add a LangChain chain (not an agent) for:
1. Interpreting ambiguous or partially-filled fields
2. Inferring missing values from context
3. Normalizing text (e.g., city name variations)

The Excel reading stays deterministic (scan Col A for label → read Col B), structured as a pure Python service. LangChain is used post-read for enrichment/normalization only.

**Pros**: Faster and cheaper (fewer LLM calls); deterministic extraction; simpler to debug; still gets LangSmith tracing + token counting for the enrichment step
**Cons**: Still somewhat coupled to label text patterns (though more robust than position-based); doesn't use the agent loop for structural discovery
**Effort**: Medium

### Approach 3: Extend Existing ExcelReader with Label-Based Mode

Add a `read_by_label()` method to `ExcelReader` that, instead of using `start_row + field_index`, scans Col A for the label text from YAML config. No LangChain at all — pure openpyxl.

Extend `excel_templates.yaml` with the 3 new sections. Add new DB tables. Keep `AIAgent` as-is for enrichment.

**Pros**: Minimal new dependencies; fastest execution; no LLM cost for extraction
**Cons**: Doesn't satisfy the "LangChain agent" requirement; no token tracking on extraction; brittle if Input 1 labels change; YAML config grows large for all 5 sections × 2 sheets
**Effort**: Low

---

## Recommendation

**Approach 2 (Hybrid)** is the pragmatic choice. Here's the reasoning:

1. **The structural discovery problem is already SOLVED** by `TableDetector`. Extending it to cover all 5 sections of Input 1 (including CONFIGURACIÓN METODOLÓGICA) is straightforward openpyxl work — scan Col A per sheet for section header text, then read downward.

2. **LangChain's value in this context is enrichment, not extraction**. Using a full ReAct agent to loop through tool calls just to find "Nombre del Negocio" in Col A when `openpyxl` can do it in microseconds is expensive and fragile. The "reads by label not cell position" requirement is PURELY a structural concern, not a semantic one.

3. **Token tracking still works** via `get_openai_callback()` wrapping the enrichment chain call. LangSmith tracing still applies.

4. **Migration path is clear**: Replace `excel_reader.py`'s position-based logic with a label-scanner; add a `LangChainEnrichmentChain` in `ai_agent.py` or a new `langchain_agent.py`; keep the rest of the pipeline.

5. **Dependency footprint**: Add `langchain>=0.3`, `langchain-openai>=0.2`, `langsmith>=0.1` — that's it.

**If the requirement is specifically "a LangChain AgentExecutor with tool calling for structural extraction"**, then Approach 1 is correct, but the proposal should explicitly flag the token cost tradeoff and the need for a fallback when the agent hallucinates section locations on unusual Input 1 layouts.

---

## Risks

1. **LangChain version fragility**: LangChain 0.3+ has a different API from 0.1/0.2 (LangChain Expression Language, new `ChatOpenAI` imports). The current codebase has no LangChain at all — the team will need to settle on a version and stick to it.

2. **`_SCHEMA` sheet + openpyxl dropdowns**: Input 1.xlsx has dropdown validations. `load_workbook()` + `wb.create_sheet()` + `wb.save()` can corrupt dropdown validation if not handled carefully. Test with `data_only=True` for reading and a separate load for the schema write.

3. **CONFIGURACIÓN METODOLÓGICA complexity**: The 5 subsections on sheet 2 are unknown without reading the actual file. The agent/scanner needs to handle potentially nested or mixed formats. This is the highest-risk section.

4. **DB migration**: SQLite doesn't support `ALTER TABLE ADD COLUMN` with all constraints. The 3 new tables are additive (new `SQLModel` classes = new `CREATE TABLE` calls), which is safe. But `LogProcesamiento` column additions require either a migration tool (Alembic) or a `DROP + RECREATE` (acceptable in dev, not prod). The project currently has no Alembic setup.

5. **`fill_template()` cell mapping for new sections**: We don't know the exact row positions of Datos del Negocio and Buyer Persona in Input 1.xlsx without reading the file. The `_PARAM_CELLS` dict will need to be extended with correct addresses — this requires inspecting the actual xlsx.

6. **Token cost for Approach 1**: A full ReAct agent loop extracting ~35+ fields from a 2-sheet xlsx could consume 2,000–5,000 tokens per request. At gpt-4o-mini rates that's negligible, but it's worth tracking via `LogProcesamiento`.

7. **No LangChain in `requirements.txt`**: First-time setup will require `pip install langchain langchain-openai langsmith` — should be added to requirements immediately to avoid env drift.

---

## Ready for Proposal

**Yes.** The exploration reveals a clear architecture:

- The core design decision (full agent vs. hybrid) needs to be settled in the proposal. The recommendation is Hybrid (Approach 2) unless the explicit product requirement is a ReAct agent for structural discovery.
- The proposal should include the specific new endpoints (`GET /template/input1`, `POST /upload/plan`), the exact 3 new DB tables with field names, the `LogProcesamiento` extension, and the LangChain dependency additions.
- A spec for the `_SCHEMA` sheet format should be included so Input 1.xlsx modifications are well-defined before implementation.
