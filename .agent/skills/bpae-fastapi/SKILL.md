---
name: bpae-fastapi
description: >
  Convenciones de FastAPI para el proyecto BPAE.
  Trigger: When writing FastAPI endpoints, routers, or API-related code in project_next.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0.0"
---

## When to Use

- Crear nuevos endpoints en la API
- Modificar routers existentes
- Estructurar responses de API
- Manejar errores en endpoints
- Definir Pydantic models para request/response

## Critical Patterns

### Nomenclatura de Endpoints

**Rutas (URLs):**
- Usar `kebab-case` (guiones medios)
- SIEMPRE incluir prefijo `/api/v1/`
- Nombre de recurso en plural

```python
# ✅ CORRECTO
@app.get("/api/v1/planes")
@app.get("/api/v1/planes/{plan_id}")
@app.post("/api/v1/generaciones")

# ❌ INCORRECTO
@app.get("/planes")                    # Falta versión API
@app.get("/api/v1/crearPlan")          # camelCase en URL
@app.post("/api/v1/generar_plan/")     # snake_case en URL
```

**Funciones (handlers):**
- Usar `snake_case`
- Verbo descriptivo + recurso
- Prefijo `get_`, `create_`, `update_`, `delete_`, `generate_`

```python
# ✅ CORRECTO
async def get_plan(plan_id: str): ...
async def create_plan(plan_data: PlanCreate): ...
async def generate_pestel(plan_id: str): ...

# ❌ INCORRECTO
async def plan(): ...                   # No descriptivo
async def getPlan(): ...                # camelCase
async def crear_plan(): ...             # Español (código en inglés)
```

### Estructura de Responses

**Formato estándar para TODAS las responses:**

```python
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    """Formato estándar de respuesta API"""
    data: Optional[T] = None
    error: Optional[str] = None
    message: Optional[str] = None

class PlanListResponse(APIResponse[list[PlanResponse]]):
    pass

class PlanResponse(APIResponse[Plan]):
    pass
```

**Uso en endpoints:**

```python
from fastapi import HTTPException

@router.get("/{plan_id}", response_model=APIResponse[Plan])
async def get_plan(plan_id: str):
    plan = await plan_service.get_plan(plan_id)
    if not plan:
        return APIResponse(error="Plan not found", message="El plan no existe")
    return APIResponse(data=plan, message="Plan encontrado")

@router.post("", response_model=APIResponse[Plan], status_code=201)
async def create_plan(plan_data: PlanCreate):
    try:
        plan = await plan_service.create_plan(plan_data)
        return APIResponse(data=plan, message="Plan creado exitosamente")
    except ValidationError as e:
        return APIResponse(error=str(e), message="Error de validación")
```

### HTTP Status Codes

| Código | Cuándo usar | Ejemplo BPAE |
|--------|-------------|--------------|
| **200** | OK, operación exitosa | GET /planes/{id} - Plan encontrado |
| **201** | Recurso creado | POST /planes - Plan creado |
| **400** | Request inválido | Datos no pasan validación Pydantic |
| **401** | No autenticado | Falta token JWT (futuro) |
| **404** | Recurso no encontrado | Plan ID no existe |
| **422** | Validación falló | Pydantic validation error |
| **500** | Error interno | Exception no manejada |
| **501** | No implementado | Endpoint en construcción |

### Manejo de Errores

**NUNCA dejes que exceptions lleguen al cliente crudo:**

```python
# ❌ MAL - Exception expuesta al cliente
@app.get("/{plan_id}")
async def get_plan(plan_id: str):
    return await plan_service.get_plan(plan_id)  # Si falla, traceback expuesto

# ✅ BIEN - Manejo apropiado
@app.get("/{plan_id}", response_model=APIResponse[Plan])
async def get_plan(plan_id: str):
    try:
        plan = await plan_service.get_plan(plan_id)
        if not plan:
            return APIResponse(error="NOT_FOUND", message="Plan no encontrado")
        return APIResponse(data=plan)
    except RepositoryError as e:
        logger.error(f"Database error: {e}")
        return APIResponse(error="DATABASE_ERROR", message="Error de base de datos")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return APIResponse(error="INTERNAL_ERROR", message="Error interno del servidor")
```

**Excepciones custom del proyecto (en `core/exceptions.py`):**

```python
from core.exceptions import ExternalAPIError, RepositoryError, ValidationError

try:
    result = await external_service.call()
except ExternalAPIError as e:
    # Error de MiniMax, Tavily, OpenCode Go
    return APIResponse(
        error="EXTERNAL_API_ERROR", 
        message=f"Error en servicio externo: {e.service}"
    )
```

### Pydantic Models

**Separación de responsabilidades:**

```python
# models/plan.py

class PlanBase(BaseModel):
    """Campos base compartidos"""
    nombre: str = Field(..., min_length=3, max_length=200)
    rubro: str = Field(..., min_length=2, max_length=100)

class PlanCreate(PlanBase):
    """Solo campos necesarios para crear"""
    pass

class PlanUpdate(BaseModel):
    """Campos opcionales para actualizar"""
    nombre: Optional[str] = Field(None, min_length=3, max_length=200)
    estado: Optional[str] = None

class Plan(PlanBase):
    """Modelo completo con todos los campos"""
    id: str
    estado: str
    created_at: datetime
    
    class Config:
        from_attributes = True  # Para conversión desde dict/objeto
```

**Validaciones en campos:**

```python
from pydantic import Field, validator

class PlanCreate(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=200)
    inversion_inicial: float = Field(default=0.0, ge=0)  # >= 0
    
    @validator('nombre')
    def nombre_no_vacio(cls, v):
        if not v.strip():
            raise ValueError('El nombre no puede estar vacío')
        return v.strip()
```

### Dependency Injection

**Usar `Depends` para inyección de dependencias:**

```python
from fastapi import Depends

# Dependency reutilizable
async def get_plan_repository() -> PlanRepository:
    return SupabasePlanRepository(get_supabase_client())

async def get_plan_service(
    repo: PlanRepository = Depends(get_plan_repository)
) -> PlanService:
    return PlanService(repo)

# Uso en endpoint
@router.post("", response_model=APIResponse[Plan])
async def create_plan(
    plan_data: PlanCreate,
    service: PlanService = Depends(get_plan_service)
):
    plan = await service.create_plan(plan_data)
    return APIResponse(data=plan)
```

### Async/Await

**TODOS los endpoints deben ser async:**

```python
# ✅ CORRECTO
@app.get("/{plan_id}")
async def get_plan(plan_id: str):  # <-- async
    plan = await service.get_plan(plan_id)  # <-- await
    return plan

# ❌ INCORRECTO
@app.get("/{plan_id}")
def get_plan(plan_id: str):  # <-- Falta async
    plan = service.get_plan(plan_id)  # <-- Bloqueante
    return plan
```

### Routers y Organización

**Estructura de routers:**

```python
# api/v1/planes.py
from fastapi import APIRouter

router = APIRouter(
    prefix="/planes",
    tags=["planes"],  # Para documentación OpenAPI
    responses={404: {"description": "Not found"}}
)

@router.get("/{plan_id}")
async def get_plan(plan_id: str): ...

@router.post("")
async def create_plan(plan: PlanCreate): ...

# main.py
from api.v1 import planes, health

app.include_router(health.router, prefix="/api/v1")
app.include_router(planes.router, prefix="/api/v1")
```

## Commands

```python
# Ejecutar servidor desarrollo
uvicorn src.backend.main:app --reload --port 8000

# Ejecutar con log detallado
uvicorn src.backend.main:app --reload --log-level debug

# Ver documentación API
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

## Code Examples

### Endpoint CRUD Completo

```python
# api/v1/planes.py

from fastapi import APIRouter, HTTPException, status
from typing import List
from models.plan import Plan, PlanCreate, PlanUpdate
from services.plan_service import PlanService
from core.schemas import APIResponse

router = APIRouter(prefix="/planes", tags=["planes"])

@router.post(
    "",
    response_model=APIResponse[Plan],
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo plan de negocio",
    description="Crea un plan en estado 'borrador' con la información básica"
)
async def create_plan(plan_data: PlanCreate):
    """Crear un nuevo plan de negocio"""
    try:
        plan = await plan_service.create(plan_data)
        return APIResponse(data=plan, message="Plan creado exitosamente")
    except ValidationError as e:
        return APIResponse(error="VALIDATION_ERROR", message=str(e))

@router.get(
    "/{plan_id}",
    response_model=APIResponse[Plan],
    summary="Obtener plan por ID"
)
async def get_plan(plan_id: str):
    """Obtener un plan específico por su UUID"""
    plan = await plan_service.get_by_id(plan_id)
    if not plan:
        return APIResponse(error="NOT_FOUND", message="Plan no encontrado")
    return APIResponse(data=plan)

@router.get(
    "",
    response_model=APIResponse[List[Plan]],
    summary="Listar todos los planes"
)
async def list_plans(limit: int = 100, offset: int = 0):
    """Listar planes con paginación"""
    plans = await plan_service.list_all(limit=limit, offset=offset)
    return APIResponse(data=plans, message=f"{len(plans)} planes encontrados")

@router.put(
    "/{plan_id}",
    response_model=APIResponse[Plan],
    summary="Actualizar plan"
)
async def update_plan(plan_id: str, plan_update: PlanUpdate):
    """Actualizar información de un plan"""
    updated = await plan_service.update(plan_id, plan_update)
    if not updated:
        return APIResponse(error="NOT_FOUND", message="Plan no encontrado")
    return APIResponse(data=updated, message="Plan actualizado")

@router.delete(
    "/{plan_id}",
    response_model=APIResponse[bool],
    summary="Eliminar plan"
)
async def delete_plan(plan_id: str):
    """Eliminar un plan permanentemente"""
    deleted = await plan_service.delete(plan_id)
    if not deleted:
        return APIResponse(error="NOT_FOUND", message="Plan no encontrado")
    return APIResponse(data=True, message="Plan eliminado")
```

### Endpoint de Generación con IA

```python
# api/v1/generaciones.py

@router.post(
    "/pestel/{plan_id}",
    response_model=APIResponse[SeccionGenerada],
    summary="Generar análisis PESTEL"
)
async def generate_pestel(plan_id: str):
    """
    Genera análisis PESTEL usando Tavily + MiniMax.
    
    1. Busca datos del sector con Tavily
    2. Genera análisis con MiniMax 2.5
    3. Guarda resultado en la sección del plan
    """
    try:
        plan = await plan_service.get_by_id(plan_id)
        if not plan:
            return APIResponse(error="NOT_FOUND", message="Plan no encontrado")
        
        # Generar PESTEL
        pestel = await generation_service.generate_pestel(plan)
        
        # Guardar sección
        await plan_service.add_section(plan_id, "pestel", pestel)
        
        return APIResponse(data=pestel, message="PESTEL generado exitosamente")
        
    except ExternalAPIError as e:
        logger.error(f"Error generando PESTEL: {e}")
        return APIResponse(
            error="GENERATION_ERROR",
            message=f"Error al generar: {e.message}"
        )
```

## Golden Rules

1. **SIEMPRE** usar formato de response estándar (`APIResponse`)
2. **SIEMPRE** usar async/await en endpoints
3. **NUNCA** exponer detalles de errores internos al cliente
4. **SIEMPRE** validar input con Pydantic models
5. **SIEMPRE** usar nombres descriptivos en inglés (snake_case)
6. **SIEMPRE** incluir tags en routers para documentación
7. **NUNCA** usar print, usar logging
8. **SIEMPRE** manejar excepciones con try/except apropiado

## Resources

- **FastAPI docs**: https://fastapi.tiangolo.com/
- **Pydantic docs**: https://docs.pydantic.dev/
- **Ejemplo en proyecto**: `src/backend/api/v1/health.py`
- **Modelos**: `src/backend/models/plan.py`
