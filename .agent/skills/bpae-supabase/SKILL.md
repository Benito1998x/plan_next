---
name: bpae-supabase
description: >
  Convenciones de Supabase para el proyecto BPAE.
  Trigger: When working with Supabase queries, tables, or database operations in project_next.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0.0"
---

## When to Use

- Crear o modificar tablas en Supabase
- Escribir queries (select, insert, update, delete)
- Manejar errores de base de datos
- Definir nombres de columnas y tipos
- Implementar repositorios que usan Supabase

## Critical Patterns

### Nomenclatura de Tablas

**Nombres de tablas:**
- Usar `snake_case` (minúsculas con guiones bajos)
- SIEMPRE en plural
- En español (coincidir con términos de negocio)

```sql
-- ✅ CORRECTO
CREATE TABLE planes (
CREATE TABLE secciones (
CREATE TABLE resultados_encuestas (

-- ❌ INCORRECTO
CREATE TABLE Plan (                 -- CamelCase
CREATE TABLE plan (                 -- Singular
CREATE TABLE business_plans (       -- Inglés (usamos español)
```

**Tablas del proyecto BPAE:**

| Tabla | Propósito | Columnas principales |
|-------|-----------|---------------------|
| `planes` | Planes de negocio | id, nombre, rubro, ciudad, inversion_inicial, estado, created_at |
| `secciones` | Secciones generadas | id, plan_id, tipo, contenido, orden, generado_automaticamente |
| `encuestas` | Encuestas diseñadas | id, plan_id, preguntas_json, estado |
| `resultados_encuestas` | Respuestas recibidas | id, encuesta_id, respuestas_json, fecha |
| `usuarios` | Usuarios del sistema | id, email, nombre, rol, created_at |

### Nomenclatura de Columnas

**Reglas:**
- `snake_case` en español
- ID siempre como `id` (UUID)
- Timestamps: `created_at`, `updated_at`
- Foreign keys: `{tabla}_id` (ej: `plan_id`)
- Estados: valores en español

```sql
-- ✅ CORRECTO
CREATE TABLE planes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre TEXT NOT NULL,
    rubro TEXT NOT NULL,
    ciudad TEXT NOT NULL,
    inversion_inicial DECIMAL DEFAULT 0,
    estado TEXT DEFAULT 'borrador',  -- 'borrador', 'activo', 'completado'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- Foreign key example
CREATE TABLE secciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES planes(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL,  -- 'pestel', 'porter', 'foda', etc.
    contenido JSONB,
    orden INTEGER DEFAULT 0,
    generado_automaticamente BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ❌ INCORRECTO
CREATE TABLE planes (
    ID UUID PRIMARY KEY,             -- Mayúsculas
    Nombre TEXT,                     -- CamelCase
    planId UUID,                     -- CamelCase FK
    status TEXT,                     -- Inglés
    createdAt TIMESTAMP              -- CamelCase
);
```

### Tipos de Datos Estándar

| Tipo de dato | Uso | Ejemplo |
|--------------|-----|---------|
| `UUID` | IDs únicos | `id`, `plan_id` |
| `TEXT` | Strings | `nombre`, `rubro`, `ciudad` |
| `DECIMAL(12,2)` | Montos monetarios | `inversion_inicial`, `presupuesto` |
| `INTEGER` | Conteos, cantidades | `cantidad_empleados`, `orden` |
| `BOOLEAN` | Flags | `activo`, `generado_automaticamente` |
| `TIMESTAMP` | Fechas y horas | `created_at`, `updated_at` |
| `JSONB` | Datos estructurados | `contenido`, `preguntas_json`, `metadata` |
| `TEXT[]` | Arrays de strings | `tags`, `categorias` |

### Queries con Supabase Client

**Estructura básica:**

```python
from supabase import create_client
from core.config import settings

# Inicializar cliente
supabase = create_client(settings.supabase_url, settings.supabase_key)

# SELECT
response = await supabase.table("planes").select("*").eq("estado", "activo").execute()
planes = response.data

# INSERT
response = await supabase.table("planes").insert({
    "nombre": "Café Artesanal",
    "rubro": "Gastronomía",
    "ciudad": "La Paz"
}).execute()
nuevo_plan = response.data[0]

# UPDATE
response = await supabase.table("planes").update({
    "estado": "completado"
}).eq("id", plan_id).execute()

# DELETE
response = await supabase.table("planes").delete().eq("id", plan_id).execute()
```

**Filtros comunes:**

```python
# Igualdad
.eq("columna", valor)

# Diferente
.neq("columna", valor)

# Mayor/menor
.gt("inversion_inicial", 10000)   # >
.gte("created_at", "2026-01-01")  # >=
.lt("created_at", "2026-12-31")   # <
.lte("orden", 5)                  # <=

# LIKE (búsqueda texto)
.like("nombre", "%Café%")
.ilike("rubro", "%gastronomía%")  # Case insensitive

# IN
.in_("estado", ["borrador", "activo"])

# IS NULL / IS NOT NULL
.is_("updated_at", None)
.not_is("deleted_at", None)

# Ordenamiento
.order("created_at", desc=True)
.order("nombre", desc=False)

# Paginación
.limit(100)
.offset(0)

# Combinados
response = await supabase.table("planes")\
    .select("*")\
    .eq("rubro", "Gastronomía")\
    .gte("inversion_inicial", 50000)\
    .order("created_at", desc=True)\
    .limit(10)\
    .execute()
```

**Joins (relaciones):**

```python
# Select con join
response = await supabase.table("secciones")\
    .select("*, planes(nombre, rubro)")\
    .eq("plan_id", plan_id)\
    .execute()

# El resultado incluye datos del plan relacionado
for seccion in response.data:
    print(seccion["tipo"])           # De secciones
    print(seccion["planes"]["nombre"])  # Del join con planes
```

### Manejo de Errores

**Tipos de errores comunes:**

```python
from core.exceptions import RepositoryError

try:
    response = await supabase.table("planes").insert(data).execute()
except Exception as e:
    error_message = str(e)
    
    # Error de conexión
    if "connection" in error_message.lower():
        raise RepositoryError("No se puede conectar a la base de datos")
    
    # Violación de constraint (ej: unique, foreign key)
    if "duplicate" in error_message.lower() or "unique" in error_message.lower():
        raise RepositoryError("Ya existe un registro con esos datos")
    
    if "foreign key" in error_message.lower():
        raise RepositoryError("El registro relacionado no existe")
    
    # Error genérico
    raise RepositoryError(f"Error de base de datos: {error_message}")
```

**Verificar si registro existe:**

```python
async def exists(self, plan_id: str) -> bool:
    response = await self.client.table("planes")\
        .select("id")\
        .eq("id", plan_id)\
        .limit(1)\
        .execute()
    return len(response.data) > 0
```

### Transacciones

**Nota**: Supabase client de Python no soporta transacciones explícitas tradicionales. Para operaciones atómicas:

```python
# Opción 1: Usar RPC (stored procedures en PostgreSQL)
response = await supabase.rpc("mi_funcion_atomica", {
    "param1": valor1,
    "param2": valor2
}).execute()

# Opción 2: Manejar errores y hacer rollback manual si es posible
# (Para MVP, mantener operaciones simples)
```

### Patrón Repository con Supabase

```python
# repositories/plan_repository.py

from typing import Optional, List
from supabase import Client
from repositories.base import PlanRepository
from models.plan import Plan, PlanCreate

class SupabasePlanRepository(PlanRepository):
    """Implementación de PlanRepository usando Supabase"""
    
    def __init__(self, client: Client):
        self.client = client
        self.table = "planes"
    
    async def get_by_id(self, plan_id: str) -> Optional[Plan]:
        """Obtener plan por ID"""
        try:
            response = await self.client.table(self.table)\
                .select("*")\
                .eq("id", plan_id)\
                .limit(1)\
                .execute()
            
            if response.data:
                return Plan(**response.data[0])
            return None
            
        except Exception as e:
            raise RepositoryError(f"Error al obtener plan: {str(e)}")
    
    async def create(self, plan: PlanCreate) -> Plan:
        """Crear nuevo plan"""
        try:
            response = await self.client.table(self.table)\
                .insert(plan.model_dump())\
                .execute()
            
            return Plan(**response.data[0])
            
        except Exception as e:
            raise RepositoryError(f"Error al crear plan: {str(e)}")
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[Plan]:
        """Listar planes con paginación"""
        try:
            response = await self.client.table(self.table)\
                .select("*")\
                .order("created_at", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()
            
            return [Plan(**item) for item in response.data]
            
        except Exception as e:
            raise RepositoryError(f"Error al listar planes: {str(e)}")
    
    async def update(self, plan_id: str, plan_data: dict) -> Optional[Plan]:
        """Actualizar plan"""
        try:
            # Agregar updated_at
            plan_data["updated_at"] = datetime.utcnow().isoformat()
            
            response = await self.client.table(self.table)\
                .update(plan_data)\
                .eq("id", plan_id)\
                .execute()
            
            if response.data:
                return Plan(**response.data[0])
            return None
            
        except Exception as e:
            raise RepositoryError(f"Error al actualizar plan: {str(e)}")
    
    async def delete(self, plan_id: str) -> bool:
        """Eliminar plan"""
        try:
            response = await self.client.table(self.table)\
                .delete()\
                .eq("id", plan_id)\
                .execute()
            
            return len(response.data) > 0
            
        except Exception as e:
            raise RepositoryError(f"Error al eliminar plan: {str(e)}")
```

### Columnas Estándar para Todas las Tablas

**SIEMPRE incluir:**

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
created_at TIMESTAMP DEFAULT NOW(),
updated_at TIMESTAMP  -- Opcional, actualizar manualmente
```

**Opcional según necesidad:**

```sql
user_id UUID REFERENCES auth.users(id),  -- Para RLS (Row Level Security)
metadata JSONB,                           -- Datos adicionales flexibles
estado TEXT DEFAULT 'activo',            -- Estado del registro
orden INTEGER DEFAULT 0,                 -- Para ordenamiento manual
```

### Estados Comunes

**Valores estándar para campo `estado`:**

| Tabla | Estados posibles | Default |
|-------|-----------------|---------|
| `planes` | 'borrador', 'activo', 'completado', 'archivado' | 'borrador' |
| `secciones` | 'pendiente', 'generando', 'completado', 'error' | 'pendiente' |
| `encuestas` | 'disenando', 'aplicando', 'finalizada' | 'disenando' |

### Queries Avanzadas

**Búsqueda full-text (si habilitas en Supabase):**

```python
# Requiere crear índice full-text en Supabase
response = await supabase.table("planes")\
    .select("*")\
    .text_search("nombre", "Café")\
    .execute()
```

**Agregaciones (count, sum, etc):**

```python
# Contar planes por rubro
response = await supabase.rpc("get_planes_count_by_rubro").execute()

# O hacerlo en Python si no tienes RPC
response = await supabase.table("planes").select("rubro").execute()
from collections import Counter
rubros_count = Counter([p["rubro"] for p in response.data])
```

## Commands

```bash
# Ver tablas en Supabase Studio
# https://app.supabase.com/project/{project-ref}/editor

# Ejecutar SQL directo en SQL Editor
# https://app.supabase.com/project/{project-ref}/sql
```

## Code Examples

### Crear tabla completa

```sql
-- SQL para crear tabla planes
CREATE TABLE planes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre TEXT NOT NULL,
    rubro TEXT NOT NULL,
    ciudad TEXT NOT NULL,
    inversion_inicial DECIMAL(12,2) DEFAULT 0,
    estado TEXT DEFAULT 'borrador',
    contenido JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- Índices comunes
CREATE INDEX idx_planes_estado ON planes(estado);
CREATE INDEX idx_planes_rubro ON planes(rubro);
CREATE INDEX idx_planes_created_at ON planes(created_at DESC);
```

### Query complejo

```python
async def get_planes_with_stats(self) -> List[dict]:
    """Obtener planes con conteo de secciones"""
    # Obtener planes
    planes_response = await self.client.table("planes").select("*").execute()
    
    # Para cada plan, contar secciones
    result = []
    for plan in planes_response.data:
        secciones_count = await self.client.table("secciones")\
            .select("id", count="exact")\
            .eq("plan_id", plan["id"])\
            .execute()
        
        plan["total_secciones"] = secciones_count.count
        result.append(plan)
    
    return result
```

## Golden Rules

1. **SIEMPRE** usar `snake_case` en español para nombres
2. **SIEMPRE** incluir `id`, `created_at` en cada tabla
3. **NUNCA** usar camelCase o Mayúsculas en nombres de tabla/columna
4. **SIEMPRE** manejar errores con try/except y convertir a RepositoryError
5. **SIEMPRE** usar `.execute()` al final de cada query
6. **SIEMPRE** validar que response.data existe antes de acceder
7. **NUNCA** exponer errores crudos de Supabase al API (traducir a mensajes amigables)
8. **SIEMPRE** usar índices en columnas de búsqueda frecuente (estado, rubro, plan_id)

## Resources

- **Supabase Python Docs**: https://supabase.com/docs/reference/python/
- **Supabase Studio**: https://app.supabase.com
- **Postgres SQL Reference**: https://www.postgresql.org/docs/current/sql.html
- **Ejemplo en proyecto**: `src/backend/repositories/plan_repository.py`
