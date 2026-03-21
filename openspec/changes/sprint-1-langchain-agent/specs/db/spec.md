# Database Specification — Sprint 1 LangChain Agent

## Purpose

Defines schema changes required before Sprint 1 runs: 3 new tables
(`DatosNegocio`, `BuyerPersona`, `ConfiguracionMetodologica`) and 4 new
nullable columns on `LogProcesamiento`. All changes MUST be safe for the
existing ~47 test plans in `plan.db`.

---

## Requirements

### Requirement: New Table — DatosNegocio

The system MUST create table `DatosNegocio` with a 1:1 relationship to `Plan`
(unique FK on `plan_id`). All content columns MUST be nullable.

#### Scenario: Table created via SQLModel create_all()

- GIVEN `DatosNegocio` is registered in `models/db/__init__.py`
- WHEN `SQLModel.metadata.create_all(engine)` is called on a DB that lacks the table
- THEN the table is created with all columns matching the proposal schema
- AND existing tables (`Plan`, `ParametrosGlobales`, etc.) are NOT modified

#### Scenario: Record inserted after plan upload

- GIVEN a successful `POST /api/v1/upload/plan`
- WHEN the pipeline saves `DatosNegocio`
- THEN exactly one row exists in `DatosNegocio` with `plan_id` matching the new plan
- AND `created_at` is populated with the UTC timestamp of insertion

#### Scenario: Duplicate plan_id rejected

- GIVEN a `DatosNegocio` row already exists for `plan_id = 5`
- WHEN the pipeline attempts to insert a second row with `plan_id = 5`
- THEN an integrity error is raised (UNIQUE constraint on `plan_id`)

---

### Requirement: New Table — BuyerPersona

The system MUST create table `BuyerPersona` with a 1:1 relationship to `Plan`.
All content columns MUST be nullable.

#### Scenario: Table created and record inserted

- GIVEN a successful plan upload with `buyer_persona` section populated
- WHEN the pipeline saves `BuyerPersona`
- THEN exactly one row exists with the correct `plan_id` and `created_at` set

#### Scenario: Empty buyer persona section

- GIVEN the uploaded file has no data in the buyer persona section
- WHEN the pipeline saves `BuyerPersona`
- THEN a row is inserted with `plan_id` set and all content columns NULL
- AND no error is raised

---

### Requirement: New Table — ConfiguracionMetodologica

The system MUST create table `ConfiguracionMetodologica` with a 1:1 relationship
to `Plan`. The column `datos_adicionales` MUST store a JSON text blob for
overflow fields from the 5 CONFIGURACIÓN METODOLÓGICA subsections.

#### Scenario: Table created with datos_adicionales

- GIVEN a plan upload with all 5 CONFIGURACIÓN METODOLÓGICA subsections present
- WHEN the pipeline saves `ConfiguracionMetodologica`
- THEN the structured fields are in their respective columns
- AND any overflow fields are serialized to `datos_adicionales` as a JSON string

#### Scenario: datos_adicionales is NULL when no overflow

- GIVEN all 5 subsections map cleanly to the defined columns
- WHEN the pipeline saves `ConfiguracionMetodologica`
- THEN `datos_adicionales` is NULL

---

### Requirement: Migration — LogProcesamiento New Columns

`scripts/migrate_sprint1.py` MUST add 4 columns to `LogProcesamiento` using
`ALTER TABLE ADD COLUMN`. The script MUST be idempotent: running it twice MUST
NOT raise an error or duplicate columns.

Columns to add:

| Column | Type | Default |
|--------|------|---------|
| `tokens_prompt` | INTEGER | NULL |
| `tokens_completion` | INTEGER | NULL |
| `costo_usd` | REAL | NULL |
| `actividad` | TEXT | NULL |

#### Scenario: Migration runs on existing plan.db

- GIVEN `plan.db` with ~47 existing `LogProcesamiento` rows and without the 4 new columns
- WHEN `migrate_sprint1.py` is executed
- THEN all 4 columns are added to `LogProcesamiento`
- AND existing rows have NULL in all 4 new columns
- AND existing row data in other columns is unchanged

#### Scenario: Migration is idempotent

- GIVEN `plan.db` where the 4 columns already exist (migration already ran)
- WHEN `migrate_sprint1.py` is executed a second time
- THEN no error is raised
- AND no duplicate columns are created

#### Scenario: Existing 47 plans remain accessible

- GIVEN `plan.db` after migration
- WHEN `SELECT * FROM plan` is executed
- THEN all 47 rows are returned with their original data intact
- AND querying `ParametrosGlobales` and `Producto` by `plan_id` returns correct results

---

### Requirement: Model Exports

`apps/api/models/db/__init__.py` MUST export `DatosNegocio`, `BuyerPersona`,
and `ConfiguracionMetodologica` so that all services can import them from a
single location.

#### Scenario: New models importable from package root

- GIVEN Sprint 1 code is in place
- WHEN `from models.db import DatosNegocio, BuyerPersona, ConfiguracionMetodologica` is executed
- THEN no `ImportError` is raised
