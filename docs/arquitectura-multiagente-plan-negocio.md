# Arquitectura Multi-Agente para Plan de Negocio con Datos Asincrónicos y Múltiples Fuentes

## Visión General

El sistema debe permitir que un profesional (asesor) recopile información de clientes poco técnicos a lo largo de varias semanas, mediante formularios Google o plantillas Excel sencillas. Los datos pueden llegar en fragmentos, y el sistema debe integrarlos, completarlos con búsquedas externas, calcular indicadores clave (demanda, capacidad, costos, etc.) y finalmente generar un plan de negocio en Excel con múltiples hojas (frecuencias de encuesta, análisis de demanda, estructura de costos, activos, organigrama, etc.) y opcionalmente un informe en Word.

La clave es manejar la asincronía y la evolución de los datos, utilizando agentes de IA especializados para tareas específicas, con modelos económicos (GPT-5 nano/mini en desarrollo, MiniMax 2.5 en producción).

---

## 1. Capas de Datos (Refinadas)

| Capa | Descripción |
|------|-------------|
| **Bronce** | Datos crudos de cada entrega (CSV de Google Form, Excel subido, etc.). Almacenados con metadatos: ID de proyecto, fecha, tipo de entrega. Pueden estar incompletos o con formatos variables. |
| **Plata** | Datos consolidados y limpios del proyecto, integrados de todas las entregas. Campos normalizados, sin duplicados. Aún pueden faltar campos necesarios. |
| **Oro** | Datos enriquecidos y listos para la plantilla. Incluyen campos del cliente (Plata), datos externos obtenidos, e indicadores calculados. Estructurados por hoja de Excel. |

---

## 2. Flujo de Trabajo Asincrónico (por Proyecto)

```
[Inicio] → Nueva entrega (formulario/Excel) → Almacenar en Bronce
         → Actualizar estado del proyecto
         → Disparar proceso de integración y cálculo
         → Generar nuevo Excel (opcional bajo demanda)
         → Notificar al profesional
```

Cada proyecto tiene un ciclo de vida de hasta un mes, con múltiples entregas. El sistema mantiene un repositorio de todos los campos recibidos y los pendientes.

---

## 3. Equipo de Agentes

### Agente 1: Orquestador Central
- **Rol**: Coordina todo el flujo, gestiona el estado de cada proyecto, recibe eventos (nuevas entregas, solicitudes manuales), invoca a los demás agentes en el orden adecuado y persiste los resultados.
- **Implementación**: Backend (Python / Node.js) con base de datos (PostgreSQL / MongoDB) y colas (Redis / Celery).
- **IA**: No requiere — solo lógica de negocio.

### Agente 2: Integrador de Entregas (Bronce → Plata)
- **Rol**: Unifica y limpia todas las entregas de un proyecto. Maneja versiones (el dato más reciente prevalece) y detecta campos faltantes.
- **IA**: Modelo ligero (GPT-5 nano) para interpretar formatos inconsistentes. Lo ideal es un esquema predefinido con mapeo de preguntas a campos estándar.
- **Salida**: JSON con todos los campos Plata + lista de campos requeridos aún no proporcionados.

### Agente 3: Buscador de Datos Externos
- **Rol**: Obtiene campos que el cliente no ha provisto (población, precios de referencia, costos de activos) desde fuentes externas confiables (APIs gubernamentales, scraping, bases de datos de mercado).
- **IA**: Modelo mediano (GPT-5 mini) con **function calling** para búsquedas estructuradas. Decide qué fuente usar según contexto (rubro, ubicación) y devuelve valores con nivel de confianza.
- **Salida**: Valores encontrados (o estimaciones) para los campos solicitados.

### Agente 4: Calculador de Indicadores de Negocio (Plata + Externos → Oro)
- **Rol**: Aplica modelos de negocio predefinidos para calcular todos los indicadores necesarios.
- **IA**: Modelo mediano (GPT-5 mini) que interpreta qué fórmulas aplicar según el rubro. Las fórmulas residen en un archivo de configuración externo (ajustable por el profesional). Un módulo numérico sin IA ejecuta las operaciones finales.
- **Indicadores calculados**:
  - Demanda: potencial, disponible, efectiva, objetivo.
  - Capacidad instalada y necesaria.
  - Mano de obra mínima.
  - Inversión inicial, costos fijos y variables.
  - Frecuencias de encuesta.
- **Salida**: JSON completo con todos los campos Oro por hoja de Excel.

### Agente 5: Poblador de Excel (Oro → Excel Final)
- **Rol**: Inserta el JSON Oro en la plantilla de Excel (múltiples hojas) siguiendo un mapeo predefinido (campo → celda/rango nombrado). Actualiza fórmulas y tablas dinámicas.
- **IA**: No requiere — script con `openpyxl` / `xlwings`.
- **Salida**: Archivo Excel listo para el cliente.

### Agente 6: Generador de Informe Word *(Opcional)*
- **Rol**: Crea un documento Word con tablas relevantes y texto explicativo generado automáticamente.
- **IA**: Modelo ligero (GPT-5 nano) para redactar párrafos introductorios y de conclusión. Inserción de tablas con `python-docx`.
- **Salida**: Archivo Word.

---

## 4. Manejo de la Asincronía y Estado del Proyecto

Cada proyecto mantiene un registro en base de datos con:

- **Datos Plata actuales** — últimos valores conocidos de cada campo.
- **Historial de entregas** — referencias a archivos Bronce.
- **Lista de campos pendientes** — los que faltan para completar el plan.
- **Datos Oro calculados** — última versión generada.
- **Estado del proyecto**: `recibiendo datos` | `completo` | `en revisión`

### Secuencia al recibir una nueva entrega

1. El **Orquestador** guarda la entrega en Bronce.
2. Invoca al **Integrador** para fusionar los nuevos datos con los Plata existentes.
3. Actualiza la lista de pendientes.
4. Si hay pendientes buscables externamente, lanza el **Buscador** en segundo plano (no bloqueante).
5. Cuando el Buscador termina (o si no hay pendientes), invoca al **Calculador** para generar nuevos Oro.
6. A demanda, genera el Excel final (no en cada entrega, para no recargar el sistema).

El profesional puede ver el progreso en un dashboard, consultar los campos pendientes y forzar la búsqueda o recalcular manualmente.

---

## 5. Ejemplo de Campos y Cálculos Típicos

### Datos que provee el cliente (en varias entregas)
- Nombre de la empresa, rubro, ciudad, departamento.
- Número y nombres de productos.
- Respuestas de encuesta (15 preguntas sobre preferencias, frecuencia de compra, precios, etc.).
- Costos de materia prima, mano de obra y gastos generales.
- Activos fijos (terreno, maquinaria) con precios.
- Número de empleados actuales (si aplica).

### Datos que obtiene el Buscador
- Población total de la ciudad/departamento (fuente: INE).
- Precios de materias primas por rubro (APIs de commodities / scraping).
- Costos promedio de activos similares.
- Tasas de interés y tipo de cambio.

### Indicadores calculados

| Indicador | Fórmula |
|-----------|---------|
| Demanda potencial | Población × % segmento objetivo |
| Demanda disponible | Demanda potencial × % con acceso al producto |
| Demanda efectiva | Demanda disponible × % intención de compra (encuesta) |
| Demanda objetivo | Demanda efectiva × % participación de mercado esperado |
| Capacidad necesaria | Demanda objetivo ÷ productividad por unidad |
| Número de empleados | (Capacidad necesaria × horas/unidad) ÷ horas/empleado |
| Inversión inicial | Suma de activos + capital de trabajo estimado |
| Costos variables | Materia prima + mano de obra directa + otros |
| Costos fijos | Alquiler + servicios + salarios administrativos |

> Las **frecuencias de encuesta** (ej. "el 60% prefiere el producto A") se tabulan y alimentan directamente los porcentajes de demanda.

---

## 6. Modelos de IA y Costos

### Entorno de Desarrollo (presupuesto: $5)

| Modelo | Uso | Costo aprox. |
|--------|-----|--------------|
| GPT-5 nano | Integración (ambigüedad) + generación de textos | $0.05 / M tokens |
| GPT-5 mini | Búsquedas y cálculos complejos | Ligeramente mayor |

**Estrategia**: usar nano en el 90% de las tareas, mini solo cuando se requiere razonamiento más fino.

### Entorno de Producción

| Modelo | Uso | Costo aprox. |
|--------|-----|--------------|
| **MiniMax 2.5** | Todos los agentes de IA (unificado) | $0.30 / M tokens |

MiniMax 2.5 reemplaza a nano y mini, ofreciendo excelente relación costo/rendimiento con function calling robusto.

### Costo estimado por proyecto

- Integración: 2–3 llamadas pequeñas
- Búsquedas externas: 5–10 llamadas
- Cálculos: 2–3 llamadas
- **Total: ~15 llamadas → < $0.10 por proyecto**

---

## 7. Ventajas de la Arquitectura

- **Modularidad** — Cada agente es independiente, fácil de mantener y actualizar.
- **Escalabilidad** — Múltiples proyectos pueden procesarse en paralelo.
- **Flexibilidad** — Las fórmulas de negocio son configurables externamente, adaptables a distintos rubros.
- **Trazabilidad** — Registro completo: datos del cliente, búsquedas externas y cálculos realizados.
- **Costo optimizado** — Modelos baratos y IA solo donde aporta valor real.

---

## 8. Interfaz para el Profesional (Asesor)

Panel web sencillo **(React + FastAPI)** con las siguientes funciones:

- [ ] Ver lista de proyectos activos.
- [ ] Consultar campos recibidos y pendientes por proyecto.
- [ ] Subir archivos manualmente (si el cliente los envía por otro medio).
- [ ] Forzar la búsqueda externa de un campo específico.
- [ ] Editar manualmente un valor si la IA no acertó.
- [ ] Generar el Excel y Word bajo demanda.
- [ ] Recibir notificaciones cuando el proyecto esté listo.

---

## Conclusión

Esta arquitectura cumple con todos los requisitos: manejo de entregas asincrónicas, integración de datos desde formularios Google o Excel, búsqueda externa de información faltante, cálculo de indicadores de negocio (demanda, capacidad, costos) y generación automática de un plan de negocio en Excel con múltiples hojas.

El resultado es un sistema **modular, escalable, flexible y rentable**, ideal para un servicio de asesoría en planes de negocio, donde el profesional supervisa y ajusta el proceso sin perder el control del output final.
