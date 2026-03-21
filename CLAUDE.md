# BPAE — Business Plan Automation Engine

## Proyecto
**Nombre:** BPAE (Business Plan Automation Engine)
**Stack:** Python · FastAPI · LangChain · SQLModel · SQLite · OpenAI API
**Objetivo:** Automatizar la generación de planes de negocio desde Excel inputs del usuario
**Mercado:** Bolivia (Ley 843, DS 24051, ASFI)
**Rama activa:** restore-17-marzo-2026

---

## Flujo General

```
Input 1.xlsx (vacío)
    → Usuario rellena
    → Sube al sistema
    → LangChain lee dinámicamente (por etiqueta, no por celda)
    → Valida + guarda en DB
    → Genera plantilla de salida (mismo formato Input 1, datos rellenados)
         ↓
    Sprint 2: AI diseña encuesta (tamaño de muestra + 16-20 preguntas) + agrega hojas
         ↓
    Sprint 3: Usuario sube respuestas → Tabula → KPIs
```

---

## Sprints

### Sprint 1 — LangChain Excel Agent [ACTIVO]
**Meta:** Input 1 vacío → usuario rellena → LangChain lee dinámico → DB → salida (Input 1 rellenado)

**Input 1.xlsx — 2 hojas:**
- `INICIO`: Parámetros Globales (12 campos) · Productos/Servicios (5 cols) · Datos del Negocio (8 campos) · Buyer Persona (8 campos)
- `CONFIGURACIÓN METODOLÓGICA`: 5 secciones (muestra, ventas, depreciación, capital trabajo, financiamiento)

**LangChain aquí:** agente que identifica secciones y campos por texto de etiqueta (col A), lee valor (col B). Sin hardcodear posiciones de celda. Si el usuario mueve o agrega campos, el agente lo detecta.

**Output S1:** mismo formato que Input 1, pero con todos los datos procesados/validados rellenados. Base para que Sprint 2 agregue más hojas.

### Sprint 2 — Survey Designer [PENDIENTE]
LangChain analiza datos de S1 → determina tamaño de muestra → genera 16-20 preguntas de encuesta. Agrega nuevas hojas al archivo de salida de S1.

### Sprint 3 — Tabulation Pipeline [PENDIENTE]
Usuario sube respuestas → Bronze→Silver→Gold → KPIs → Word

---

## Estructura Clave

```
apps/api/
  api/v1/       → Endpoints (upload.py, survey.py, complete.py)
  config/       → YAML (excel_templates.yaml, defaults.yaml)
  core/         → exceptions.py, validators.py
  database/     → SQLite singleton
  models/db/    → plan_data.py, survey.py, global_data.py, trazabilidad.py
  services/     → excel_reader.py, word_service.py, ai_agent.py
    pipeline/   → bronze.py, silver.py, gold.py, writer.py
data/
  Input 1.xlsx  → Template de entrada principal (referencia de estructura)
  Encuesta.xlsx → Template encuesta
plantillas/     → Outputs generados (fase 1/, fase 2/, fase 3/)
docs/           → Documentación de fases
```

---

## Base de Datos

- **Motor:** SQLite en `apps/api/data/plan.db`
- **ORM:** SQLModel + SQLAlchemy
- **Tablas existentes:** Plan, ParametrosGlobales, Producto, Survey, SurveyResponse, Auditoria, LogProcesamiento
- **Tablas a agregar en S1:** DatosNegocio, BuyerPersona, ConfiguracionMetodologica

---

## LLM Config

- **Dev:** OpenAI GPT-4o-mini (`OPENAI_API_KEY` en `.env`)
- **Prod:** MiniMax 2.5 (OpenAI-compatible)
- **LangChain:** Se incorpora en Sprint 1 — agente de lectura dinámica de Excel

---

## SDD — Spec-Driven Development

**Persistence:** Engram (gentle-ai)
**Flujo:** proposal → spec → design → tasks → apply → verify → archive
**Comandos:** /sdd-new · /sdd-ff · /sdd-apply · /sdd-verify · /sdd-archive

---

## REGLAS DE COLABORACIÓN — LEER SIEMPRE

### Antes de escribir código
1. Mostrar QUÉ se va a cambiar y POR QUÉ — esperar confirmación
2. Preguntar: "¿Esta es la lógica que querés?"
3. Si hay duda sobre el comportamiento esperado, STOP y preguntar

### Después de cada tarea
1. STOP — no avanzar a la siguiente sin revisión del usuario
2. Preguntar: "¿Revisás el código? ¿El comportamiento es el esperado?"
3. Verificar que lo anterior funciona antes de agregar más
4. Una tarea a la vez — nunca implementar en bloque sin checkpoints

### NUNCA
- Implementar múltiples tareas sin revisión intermedia
- Asumir que el código funciona sin verificación del usuario
- Cambiar código que ya funciona sin avisar
- Avanzar sin confirmación explícita en cada paso
- Escribir código sin haber leído el código existente primero
