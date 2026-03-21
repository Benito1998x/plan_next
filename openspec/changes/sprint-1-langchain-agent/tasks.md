# Tasks: Sprint 1 — Hybrid LangChain Pipeline for Input 1.xlsx

**Change**: sprint-1-langchain-agent
**Date**: 2026-03-21
**Persistence**: openspec → `openspec/changes/sprint-1-langchain-agent/tasks.md`

---

## Phase 0 — Investigation (before any code)

> BLOCKING: all subsequent phases depend on findings here. User confirms before Phase 1 begins.

- [x] 0.1 Open `Input 1.xlsx` in openpyxl, print Col A of sheet `CONFIGURACIÓN METODOLÓGICA` row-by-row — log every non-empty value and its row index to confirm the 5 subsection anchor labels and their exact text.
- [x] 0.2 Print Col A of sheet `INICIO` row-by-row — verify anchor labels for sections 1–4 (parametros_globales, productos_servicios, datos_negocio, buyer_persona) and confirm any table headers.
- [x] 0.3 Test dropdown preservation: write a minimal openpyxl script that loads `Input 1.xlsx` with `load_workbook(keep_vba=False)`, writes one cell, saves to `data/test_output.xlsx` — confirmed Data Validation lists survive (11/11 preserved).
- [x] 0.4 Document findings in `openspec/changes/sprint-1-langchain-agent/phase0-report.md` — exact anchor strings and dropdown test result recorded. **STOP — user reviews before Phase 1.**

---

## Phase 1 — Cleanup (delete old files, reset DB)

> BLOCKING: stale imports will cause Phase 2 model registration to fail if not removed first. User confirms before Phase 2 begins.

- [x] 1.1 Delete `apps/api/services/excel_reader.py` — verify no remaining imports with a project-wide search first.
- [x] 1.2 Delete `apps/api/services/template_config.py` — verify no remaining imports.
- [x] 1.3 Delete `apps/api/config/excel_templates.yaml` — verify nothing reads this path at runtime.
- [x] 1.4 Delete `apps/api/services/table_detector.py` — verify no remaining imports.
- [x] 1.5 In `apps/api/services/ai_agent.py`: SKIPPED — `EXTRACT_SCHEMA` and `extract_plan_data` are still used by legacy routes (`upload.py`, `complete_service.py`). Removal deferred to when those routes are refactored in Phase 4. Module still imports cleanly. `infer_variable_names` confirmed intact.
- [x] 1.6 In `apps/api/api/v1/upload.py`: remove `reader = ExcelReader()` instantiation and any `ExcelReader` import. Confirm legacy routes (`/upload-excel`, `/process-plan`) still register without error.
- [x] 1.7 Back up `apps/api/data/plan.db` to `apps/api/data/plan.db.backup_fase1` — required before any schema change.
- [x] 1.8 Delete `apps/api/data/plan.db` (or truncate new tables if migration is preferred) to start fresh for experimental Sprint 1 development. **STOP — user confirms DB reset before Phase 2.**

---

## Phase 2 — Infrastructure (requirements, DB models, migration)

> BLOCKING: DB models must exist before the pipeline can persist data. User confirms after each sub-group.

- [x] 2.1 In `apps/api/requirements.txt`: add `langchain>=0.3`, `langchain-openai>=0.2`, `langsmith>=0.1`. Verify no version conflict with existing `openai` pin.
- [x] 2.2 Create `apps/api/models/db/plan_data.py` additions: add `DatosNegocio` SQLModel table (id PK, plan_id FK unique, all content cols Optional, created_at non-nullable UTC).
- [x] 2.3 Add `BuyerPersona` SQLModel table to `plan_data.py` (same pattern: id PK, plan_id FK unique, all content cols Optional).
- [x] 2.4 Add `ConfiguracionMetodologica` SQLModel table to `plan_data.py` (id PK, plan_id FK unique, content cols Optional, `datos_adicionales: Optional[str]` TEXT for JSON overflow).
- [x] 2.5 Add three `Relationship` back-refs to `Plan` model in `plan_data.py`: `datos_negocio`, `buyer_persona`, `config_metodologica`.
- [x] 2.6 In `apps/api/models/db/trazabilidad.py`: add 4 Optional fields to `LogProcesamiento` — `tokens_prompt: Optional[int]`, `tokens_completion: Optional[int]`, `costo_usd: Optional[float]`, `actividad: Optional[str]`.
- [x] 2.7 In `apps/api/models/db/__init__.py`: export `DatosNegocio`, `BuyerPersona`, `ConfiguracionMetodologica`.
- [x] 2.8 Create `apps/api/scripts/migrate_sprint1.py`: N/A — fresh DB used (no existing data to migrate). New columns added via SQLModel.create_all() directly. Task 1.5 (ai_agent cleanup) deferred — extract_plan_data is still used by legacy routes; only dead code removal would be needed once legacy routes are refactored.
- [x] 2.9 Run `python scripts/migrate_sprint1.py` against the fresh DB — confirmed: 17 tables created, 4 new LogProcesamiento columns present, 3 new plan tables created, seed data loaded (2 monedas, 3 impuestos, 9 ciudades, 3 indicadores).

---

## Phase 3 — Core Pipeline (Input1Reader + LangChain chain)

> BLOCKING: reader and chain must be complete before the endpoint can wire them. User confirms after each component.

- [x] 3.1 Add `ProductoData`, `ParametrosData`, `DatosNegocioData`, `BuyerPersonaData`, `ConfigMetodologicaData`, `PlanData` Pydantic models to `apps/api/models/schemas.py` (appended to existing file, all Optional fields default to None).
- [x] 3.2 Create `apps/api/services/input1_reader.py`: `Input1Reader` class with `read()`, `_find_anchors()`, `_scan_section()`, `_extract_kv()`, `_extract_table()`, `_extract_all_config()` — uses exact anchor strings from Phase 0 report. No hardcoded row numbers.
- [x] 3.3 Smoke tested `Input1Reader.read()` against `data/sprint1/fixtures/input1_shawarma.xlsx` — PASS. All 4 INICIO sections + 5 CONFIG subsections populated; 3 productos extracted correctly. Temp script deleted.
- [x] 3.4 Create `apps/api/services/langchain_chain.py`: `Input1EnrichmentChain` class using `ChatOpenAI` + `PydanticOutputParser(pydantic_object=PlanData)`, wrapped in `get_openai_callback()`. Run name set to `"input1_enrichment"`.
- [ ] 3.5 Manually test `Input1EnrichmentChain.enrich(raw_dict)` with real API call — confirm `PlanData` instance returned, `cb.prompt_tokens > 0`. **STOP — user reviews enriched output and token cost.**

---

## Phase 4 — Endpoints (GET template, POST upload)

> Depends on Phase 3 complete. User confirms after full pipeline smoke test.

- [x] 4.1 In `apps/api/api/v1/upload.py`: add `GET /api/v1/template/input1` route — return `FileResponse(TEMPLATE_PATH)` with correct content-type header, or 404 if file absent.
- [x] 4.2 In `apps/api/api/v1/upload.py`: add `POST /api/v1/upload/plan` route — wire `FileValidator` → `Input1Reader` → `Input1EnrichmentChain` → `_save_plan_to_database()` → `ExcelWriter.fill_input1_template()` → `LogProcesamiento` insert → return 200 JSON.
- [x] 4.3 Implement `_save_plan_to_database(plan_data)` helper in `upload.py`: insert `Plan`, `ParametrosGlobales`, `Produto × N`, `DatosNegocio`, `BuyerPersona`, `ConfiguracionMetodologica`.
- [ ] 4.4 Manual smoke test: `curl -F "file=@Input 1.xlsx" http://localhost:8000/api/v1/upload/plan` — confirm 200, `plan_id` is integer, `sections_extracted` has 5 keys. **STOP — user confirms endpoint response.**

---

## Phase 5 — Token Tracking (LogProcesamiento integration)

> Depends on Phase 4. User confirms log row written correctly.

- [x] 5.1 In the `POST /upload/plan` handler: after `Input1EnrichmentChain.invoke()` succeeds, insert `LogProcesamiento` row with `actividad="input1_enrichment"`, `tokens_prompt=cb.prompt_tokens`, `tokens_completion=cb.completion_tokens`, `costo_usd=cb.total_cost`, `plan_id` set.
- [x] 5.2 In the exception handler of `POST /upload/plan`: insert `LogProcesamiento` row with `actividad="input1_enrichment"`, NULL token fields, `plan_id` set (if available). Return 500 JSON.
- [ ] 5.3 Verify in SQLite: `SELECT actividad, tokens_prompt, tokens_completion, costo_usd FROM logprocesamiento ORDER BY id DESC LIMIT 1` — confirm values populated. **STOP — user confirms.**

---

## Phase 6 — Output (fill_input1_template)

> Depends on Phase 4. User confirms Excel output before tests.

- [x] 6.1 In `apps/api/services/excel_writer.py`: add `fill_input1_template(plan_id, plan_data: PlanData, template_path, output_path: Path)` method — load template with `load_workbook(TEMPLATE_PATH)` (no `data_only`), write all 5 section cells by label-based row lookup, save to `output_path`.
- [ ] 6.2 Verify output: open `data/sprint1/outputs/{plan_id}_output.xlsx` — confirm targeted cells contain enriched values, non-targeted cells and dropdown validations are unchanged.
- [ ] 6.3 Confirm `excel_url` in the API response points to the correct output file path. **STOP — user reviews output file.**

---

## Phase 7 — Tests

> All phases must be complete before writing tests. User confirms test suite green.

- [ ] 7.1 Create `apps/api/tests/test_input1_reader.py`: unit test `_scan_section()` with an in-memory openpyxl workbook fixture; test `_extract_kv()` returns `None` for empty cells; test absent label produces missing key in `raw_dict` (no exception).
- [ ] 7.2 Add test: `Input1Reader.read()` uses `load_workbook(data_only=True)` — mock `load_workbook` and assert `data_only=True` is passed.
- [ ] 7.3 Create `apps/api/tests/test_upload_plan.py`: integration test `GET /api/v1/template/input1` — assert 200, content-type `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
- [ ] 7.4 Add integration test: `GET /api/v1/template/input1` when file absent → 404 `{"detail": "Template not found"}`.
- [ ] 7.5 Add integration test: `POST /api/v1/upload/plan` with `.csv` → 400 `{"detail": "Only .xlsx files are accepted"}`.
- [ ] 7.6 Add integration test: `POST /api/v1/upload/plan` with xlsx missing a required label → 400 `{"detail": "Missing required field: <label>"}`.
- [ ] 7.7 Unit test `Input1EnrichmentChain`: mock `ChatOpenAI` + mock `get_openai_callback()` with `prompt_tokens=10, completion_tokens=5, total_cost=0.001` — assert returned `PlanData` is valid and `cb` values are captured.
- [ ] 7.8 Unit test `PlanData`: parametrize with missing required field (`nombre`, `rubro`, `ciudad`) — assert `ValidationError` raised. Test Optional fields accept `None`.
- [ ] 7.9 Regression test: `POST /upload-excel` and `POST /process-plan` with valid payload — assert response shape unchanged vs pre-Sprint-1 snapshots.
- [ ] 7.10 Run full suite: `pytest apps/api/tests/ -v` — confirm all tests green. **STOP — user reviews results.**
