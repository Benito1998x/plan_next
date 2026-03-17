---
name: bpae-context
description: >
  Contexto del Business Plan Automation Engine (BPAE) para Nextstat.
  Trigger: Always load when working on project_next.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0.0"
---

## When to Use

- **Always** when working on the Business Plan Automation Engine project
- When generating any section of the business plan document
- When making architectural decisions about the codebase
- When integrating with MiniMax 2.5, Supabase, or Tavily APIs
- When creating new endpoints or services

## Critical Patterns

### Project Identity
- **Name**: Business Plan Automation Engine (BPAE)
- **Author**: Ricardo Benito Vasquez Roca
- **Company**: Nextstat
- **Status**: Phase 1 - Experimentation
- **Current Focus**: Simple template validation

### Tech Stack (Non-Negotiable)
| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | FastAPI (Python) | API REST |
| Database | Supabase (PostgreSQL) | Data persistence |
| LLM Production | MiniMax 2.5 | Text generation |
| LLM Development | OpenCode Go API | Free testing/development |
| Frontend | Next.js | User interface |
| Documents | python-docx | Word generation |
| Spreadsheets | openpyxl | Excel generation |
| Research | Tavily API | Web search |
| Cache | Redis | Session storage |
| KB Vector | ChromaDB | Knowledge base |
| Infrastructure | Oracle Cloud Free Tier | Deployment |

### Project Structure (Monorepo)

```
project_next/
├── apps/
│   ├── web/          # Next.js frontend
│   └── api/          # FastAPI backend
├── docs/             # Documentation
└── .agent/           # Skills and AI context
```

### Document Structure (What BPAE Generates)

The system generates professional business plans with this structure:

```
PLAN DE NEGOCIO: [Business Name]

PRELIMINARES
├── Portada (with corporate identity)
├── Tabla de Contenido
└── Resumen Ejecutivo

CAPÍTULO I: DEFINICIÓN DEL NEGOCIO
├── Descripción del Negocio
├── Misión y Visión
└── Identificación del Problema

CAPÍTULO II: ANÁLISIS DE MERCADO
├── Análisis PESTEL (automated via Tavily + MiniMax)
├── Análisis 5 Fuerzas de Porter (automated)
└── Análisis FODA

CAPÍTULO III: INVESTIGACIÓN DE MERCADO
├── Buyer Persona
├── Diseño de Encuesta (semi-automated)
└── TAM/SAM/SOM

CAPÍTULO IV: ANÁLISIS FINANCIERO
├── Inversiones Iniciales
├── Estructura de Costos
├── Estado de Resultados Proyectado
├── Flujo de Caja Proyectado
└── Indicadores (VPN, TIR, Payback)

CAPÍTULO V: CONCLUSIONES
└── Síntesis de Viabilidad
```

### Automation Levels

| Section | Level | Human Input Required |
|---------|-------|---------------------|
| PESTEL | 🤖 Automated | Business sector, city |
| Porter 5 Forces | 🤖 Automated | Competitors, location |
| FODA | 🤖 Automated | Results from above |
| Buyer Persona | 👤 Semi-auto | Target segment description |
| Survey Design | 👤 Semi-auto | Approval of questions |
| Survey Results | ✋ Manual | User applies survey offline |
| Financial Excel | 🤖 Automated | Investment estimates, costs |
| Indicators | 🤖 Automated | Financial projections |

### FastAPI Conventions

**Endpoint Structure:**
```python
# ALWAYS use /api/v1/ prefix
@app.get("/api/v1/planes")
@app.post("/api/v1/planes")

# ALWAYS async for I/O operations
async def get_planes():
    ...

# ALWAYS return standard format
return {
    "data": result,
    "error": None,
    "message": "Success"
}
```

**Naming:**
- Endpoints: `kebab-case` → `/planes-negocio`
- Functions: `snake_case` → `generar_pestel()`
- Classes: `PascalCase` → `PlanGenerator`
- Variables: descriptive → `buyer_persona`, NOT `bp`

### Excel Master Template Rules

```python
# CRITICAL: Only write to Control Panel sheet
# NEVER touch formulas in other sheets

# Panel de Control structure:
# A1: Label, B1: Value (this is where you write)
# Example:
ws['B2'] = precio_unitario  # ✓ CORRECT
ws['C10'] = formula_custom  # ✗ WRONG - breaks template
```

### MiniMax 2.5 Integration

**Endpoint:**
```
POST https://api.minimaxi.chat/v1/text/chatcompletion_v2
```

**Required Headers:**
```python
headers = {
    "Authorization": f"Bearer {MINIMAX_API_KEY}",
    "Content-Type": "application/json"
}
```

**Request Format:**
```python
payload = {
    "model": "MiniMax-Text-01",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    "temperature": 0.7,
    "max_tokens": 4096
}
```

**CRITICAL:** Always validate JSON response before using.

### Supabase Conventions

**Table Naming:** `snake_case`, plural
- `planes_negocio` ✓
- `PlanesNegocio` ✗

**Standard Columns:**
```sql
id: uuid PRIMARY KEY
created_at: timestamp
updated_at: timestamp
user_id: uuid REFERENCES auth.users
```

## Code Examples

### Generating PESTEL Analysis

```python
async def generar_pestel(rubro: str, ciudad: str) -> dict:
    """
    Generate PESTEL analysis using Tavily + MiniMax.
    """
    # Step 1: Research with Tavily
    research_data = await tavily_search(
        f"{rubro} sector {ciudad} regulations economy trends"
    )
    
    # Step 2: Generate with MiniMax
    system_prompt = """Eres un analista de mercado experto. 
    Genera un análisis PESTEL profesional en español."""
    
    user_prompt = f"""
    Rubro: {rubro}
    Ubicación: {ciudad}
    Datos de investigación: {research_data}
    
    Genera análisis en JSON:
    {{
        "politico_legal": "...",
        "economico": "...",
        "socio_cultural": "...",
        "tecnologico": "...",
        "ecologico": "..."
    }}
    """
    
    response = await minimax_chat(system_prompt, user_prompt)
    return json.loads(response)
```

### Word Document Structure

```python
def create_business_plan(doc_data: dict) -> Document:
    """
    Create Word document with proper styling.
    """
    doc = Document()
    
    # Title
    title = doc.add_heading(doc_data['titulo'], level=0)
    
    # Chapter 1
    doc.add_heading('Capítulo I: Definición del Negocio', level=1)
    doc.add_heading('1.1 Descripción del Negocio', level=2)
    doc.add_paragraph(doc_data['descripcion'])
    
    # Use styles, never hardcode
    # ✓ CORRECT
    paragraph = doc.add_paragraph()
    paragraph.style = 'Normal'
    run = paragraph.add_run('Bold text')
    run.bold = True
    
    # ✗ WRONG
    # paragraph.bold = True  # Applies to whole paragraph
    
    return doc
```

### Excel Financial Template

```python
def fill_financial_template(plan_data: dict, template_path: str):
    """
    Fill master Excel template via Control Panel.
    """
    wb = load_workbook(template_path)
    panel = wb['Panel de Control']
    
    # Only write to Control Panel
    panel['B2'] = plan_data['precio_unitario']
    panel['B3'] = plan_data['costo_variable']
    panel['B4'] = plan_data['unidades_mes_1']
    # ... etc
    
    # Formulas in other sheets auto-calculate
    wb.save(f"output/plan_{plan_data['id']}.xlsx")
```

## Project Phases

### Phase 1: Experimentation (CURRENT)
- **Goal**: Validate IA + Excel manipulation workflow
- **Scope**: Simple template (2 tables: PARAMETROS GLOBALES, PRODUCTOS/SERVICIOS)
- **Architecture**: FastAPI + Next.js + openpyxl + python-docx
- **Agents**: Minimal (1-2 agents for calculation and population)
- **Data Flow**: Direct input → Excel → Word
- **Deliverables**: Working Excel → Word pipeline

### Phase 2: Enhanced Template
- **Goal**: Add calculations, validation, specialized agents
- **Scope**: Silver layer (clean data), more complex Excel
- **Architecture**: Add Redis cache, ChromaDB
- **Deliverables**: Robust financial calculations

### Phase 3: Full Multi-Agent System
- **Goal**: Complete architecture as documented
- **Scope**: Bronze/Silver/Gold layers, 6 agents, orchestrator
- **Architecture**: Full Supabase persistence, dashboard
- **Deliverables**: Production-ready system

## Commands

```bash
# Start Next.js development
cd apps/web && npm run dev

# Start FastAPI backend
cd apps/api && uvicorn main:app --reload --port 8000

# Start engram server (for memory persistence)
engram serve &

# Run tests
pytest tests/ -v

# Check project status
# Use /status in OpenCode to see SDD workflow state
```

## Resources

- **Implementation Plan**: `project/plan_implementacion_v2.md`
- **Complete Index**: `docs/indice-completo.md`
- **MVP Index**: `docs/indice-mvp.md`
- **Repository**: https://github.com/Benito1998x/project_next
- **Skill Registry**: `.atl/skill-registry.md`

### External Documentation
- **FastAPI**: https://fastapi.tiangolo.com/
- **Supabase Python**: https://supabase.com/docs/reference/python/
- **python-docx**: https://python-docx.readthedocs.io/
- **openpyxl**: https://openpyxl.readthedocs.io/

## Golden Rules

1. **NEVER** generate code without SDD workflow (`/sdd-new`, `/sdd-apply`)
2. **NEVER** hardcode values in Excel formulas (use Control Panel)
3. **ALWAYS** validate MiniMax JSON response before parsing
4. **ALWAYS** explain WHY before making changes (Gentleman persona)
5. **ALWAYS** ask before assuming business requirements
6. **ALWAYS** use async for I/O operations (database, API calls)
7. **ALWAYS** cache Tavily results in Redis (24h TTL)
8. **ALWAYS** commit conventions: `type: description`

## Decision Log

Key architectural decisions (stored in engram):
- `sdd-init/project_next` - Project initialization context
- `bpae/indice-plan-negocio` - Document structure
- Future: `bpae/decision-*` for each major decision

## Environment Variables Required

```bash
# APIs
MINIMAX_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here

# Database
SUPABASE_URL=https://...supabase.co
SUPABASE_KEY=your_key_here

# Cache
REDIS_URL=redis://localhost:6379

# App
APP_ENV=development|production
DEBUG=true|false
```

## Contact

- **Developer**: Ricardo Benito Vasquez Roca
- **Email**: benitosvasquez1998@gmail.com
- **Project**: Business Plan Automation Engine for Nextstat
