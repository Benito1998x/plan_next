# Business Plan Automation Engine (BPAE) - plan-next

Sistema para generar planes de negocio automáticamente a partir de datos del cliente.

## Fase Actual: 1

**Objetivo**: Experimentación con manipulación de Excel → Word

## Stack Tecnológico

- **Backend**: FastAPI (Python)
- **Database**: SQLite + SQLModel
- **Frontend**: Next.js (pendiente)
- **Documents**: openpyxl (Excel), python-docx (Word)

## Estructura del Proyecto

```
plan-next/
├── apps/
│   └── api/                    # FastAPI backend
│       ├── api/v1/             # Endpoints
│       ├── config/             # Configuración YAML
│       ├── core/               # Excepciones, validadores
│       ├── database/           # SQLite manager
│       ├── models/             # SQLModel + Pydantic
│       ├── scripts/            # Scripts de inicialización
│       ├── services/           # Lógica de negocio
│       ├── templates/          # Plantillas Excel
│       └── requirements.txt
├── docs/                       # Documentación
└── .agent/                     # Skills de IA
```

## Instalación

### 1. Activar entorno virtual

```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r apps/api/requirements.txt
```

### 3. Inicializar base de datos

```bash
cd apps/api
python scripts/init_db.py
```

## Uso

### Iniciar servidor de desarrollo

```bash
cd apps/api
uvicorn main:app --reload --port 8000
```

### Documentación API

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Configuración

Los valores por defecto están en `apps/api/config/defaults.yaml`:

- Moneda: Boliviano (Bs)
- Tipo de cambio: 6.96 Bs/USD
- Impuesto IUE: 25%
- Impuesto IT: 3%

## Modelo de Datos

### Tablas

**Datos Globales:**
- `moneda` - Monedas disponibles
- `impuesto` - Tipos de impuestos
- `ciudad` - Ciudades de Bolivia
- `tipo_cambio` - Histórico de tipos de cambio
- `indicador_economico` - Indicadores económicos

**Datos del Plan:**
- `plan` - Plan de negocio principal
- `parametros_globales` - Parámetros específicos del plan
- `producto` - Productos/servicios del plan
- `version_plan` - Versiones generadas

**Trazabilidad:**
- `auditoria` - Registro de cambios
- `log_procesamiento` - Log de archivos procesados

## Desarrollo

### Fases del Proyecto

| Fase | Estado | Descripción |
|------|--------|-------------|
| 1 | 🔄 En progreso | Infraestructura + BD |
| 2 | ⏳ Pendiente | Core Services (Excel, Word) |
| 3 | ⏳ Pendiente | API Endpoints |
| 4 | ⏳ Pendiente | Frontend Next.js |
| 5 | ⏳ Pendiente | Agentes IA |

## Autor

Ricardo Benito Vasquez Roca - Nextstat