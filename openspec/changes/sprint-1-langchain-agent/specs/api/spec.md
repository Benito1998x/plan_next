# API Specification — Sprint 1 LangChain Agent

## Purpose

Defines behavior for the two new HTTP endpoints added in Sprint 1:
`GET /api/v1/template/input1` and `POST /api/v1/upload/plan`.

---

## Requirements

### Requirement: Template Download Endpoint

The system MUST expose `GET /api/v1/template/input1` that returns the unmodified
`Input 1.xlsx` file as an attachment download.

#### Scenario: Template file exists

- GIVEN the file `Input 1.xlsx` is present in the configured templates directory
- WHEN a client sends `GET /api/v1/template/input1`
- THEN the response status is 200
- AND `Content-Type` is `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- AND `Content-Disposition` is `attachment; filename="Input 1.xlsx"`

#### Scenario: Template file missing

- GIVEN the file `Input 1.xlsx` is absent from the templates directory
- WHEN a client sends `GET /api/v1/template/input1`
- THEN the response status is 404
- AND the body contains `{"detail": "Template not found"}`

---

### Requirement: Plan Upload Endpoint — Happy Path

The system MUST expose `POST /api/v1/upload/plan` accepting `multipart/form-data`
with a single field `file` of type `.xlsx`.

On success, the response MUST include `plan_id`, `sections_extracted` (list of 5 keys),
`tokens_prompt`, `tokens_completion`, `costo_usd`, `excel_url`, and `word_url`.

#### Scenario: Valid Input 1.xlsx uploaded

- GIVEN a well-formed `Input 1.xlsx` with all required labels present in Col A
- WHEN a client sends `POST /api/v1/upload/plan` with the file attached
- THEN the response status is 200
- AND `sections_extracted` contains exactly `["parametros_globales", "productos_servicios", "datos_negocio", "buyer_persona", "configuracion_metodologica"]`
- AND `plan_id` is a positive integer matching a newly created row in `Plan`
- AND `excel_url` is `/api/v1/download/{plan_id}/excel`

---

### Requirement: Plan Upload Endpoint — Validation Errors

The endpoint MUST reject non-Excel uploads and files exceeding size limits with HTTP 400.

#### Scenario: Non-xlsx file submitted

- GIVEN a client uploads a `.csv` file to `POST /api/v1/upload/plan`
- WHEN the request is processed
- THEN the response status is 400
- AND the body contains `{"detail": "Only .xlsx files are accepted"}`

#### Scenario: File too large

- GIVEN a client uploads an `.xlsx` file exceeding the configured max size
- WHEN the request is processed
- THEN the response status is 400
- AND the body contains `{"detail": "File exceeds maximum allowed size"}`

#### Scenario: Required label missing from Excel

- GIVEN an `.xlsx` file missing a required Col A label (e.g., "Nombre del Negocio")
- WHEN `Input1Reader` finishes scanning
- THEN the response status is 400
- AND the body contains `{"detail": "Missing required field: <label_name>"}`

---

### Requirement: Plan Upload Endpoint — Server Errors

The endpoint MUST return HTTP 500 on unrecoverable pipeline failures and MUST
NOT leave orphaned DB records without a corresponding `LogProcesamiento` entry.

#### Scenario: LLM call fails

- GIVEN the OpenAI API returns an error during the enrichment chain call
- WHEN `Input1EnrichmentChain.invoke()` raises an exception
- THEN the response status is 500
- AND the body contains `{"detail": "Processing error: <message>"}`
- AND a `LogProcesamiento` row is written with `actividad="input1_enrichment"` and NULL token fields

---

### Requirement: Legacy Endpoint Preservation

The existing endpoints `POST /upload-excel` and `POST /process-plan` MUST remain
operational and return their current response shapes without modification.

#### Scenario: Legacy endpoint after Sprint 1 deployment

- GIVEN the Sprint 1 code is deployed
- WHEN a client calls `POST /upload-excel` with a valid payload
- THEN the response status and body are identical to pre-Sprint-1 behavior
