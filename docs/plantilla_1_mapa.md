# Mapa de Plantilla: `plantilla_1.xlsx`

> Documento de referencia para el agente de IA.  
> Describe cada celda de la hoja `INICIO`, qué dato contiene y cómo debe llenarse.

---

## Hoja: `INICIO`

### Sección 1 — Encabezado

| Celda | Contenido fijo | Descripción |
|-------|---------------|-------------|
| `A1`  | `PLAN DE NEGOCIO` | Título del documento. **No modificar.** |

---

### Sección 2 — PARÁMETROS GLOBALES (`A3:B16`)

> **Etiquetas en columna A (fijas, no modificar). Valores a ingresar en columna B.**

| Celda etiqueta | Celda valor | Campo | Tipo de dato | Notas / Formato esperado |
|---|---|---|---|---|
| `A3` | — | `PARÁMETROS GLOBALES` | Título de sección. Sin valor. | **No modificar.** |
| `A4` | `B4` | Nombre del Proyecto | Texto | Nombre comercial o razón social del proyecto. |
| `A5` | `B5` | Rubro / Sector | Texto | Categoría económica (ej. "Restaurant", "Manufactura"). |
| `A6` | `B6` | Ciudad | Texto | Ciudad de operación del negocio. |
| `A7` | `B7` | Departamento | Texto | Departamento/estado/provincia. |
| `A8` | `B8` | País | Texto | País de operación. |
| `A9` | `B9` | Moneda | Texto | Símbolo de moneda local (ej. `Bs`, `USD`, `PEN`). |
| `A10` | `B10` | Tipo de Cambio (Bs/$us) | Número decimal | Tasa de cambio respecto al dólar. Ej: `6.96` |
| `A11` | `B11` | Tasa de Inflación Anual | Número decimal (%) | En formato decimal. Ej: `0.02` = 2% |
| `A12` | `B12` | Horizonte de Proyección (años) | Entero | Cantidad de años a proyectar. Ej: `5` |
| `A13` | `B13` | Año Base (Año 0) | Entero (año) | Año de inicio de la evaluación. Ej: `2025` |
| `A14` | `B14` | Año Inicio Operaciones | Entero (año) | Primer año de actividad real. Ej: `2026` |
| `A15` | `B15` | Impuesto IUE (%) | Número decimal (%) | Impuesto a las Utilidades. Ej: `0.25` = 25% |
| `A16` | `B16` | Impuesto IT (%) | Número decimal (%) | Impuesto a las Transacciones. Ej: `0.03` = 3% |

---

### Sección 3 — PRODUCTOS / SERVICIOS (`A18:D29`)

> **Fila 19 = encabezados fijos. Filas 20–29 = datos de productos (hasta 10 ítems).**

#### Encabezados (fila 19) — No modificar

| Celda | Contenido fijo |
|-------|---------------|
| `A19` | `N°` |
| `B19` | `Nombre del Producto` |
| `C19` | `Unidad de Medida` |
| `D19` | `Peso/Vol por Unidad` |

#### Filas de datos (20–29)

| Celda col A | Celda col B | Celda col C | Celda col D | Descripción |
|---|---|---|---|---|
| `A20` (= `1`) | `B20` | `C20` | `D20` | Producto/Servicio 1 |
| `A21` (= `2`) | `B21` | `C21` | `D21` | Producto/Servicio 2 |
| `A22` (= `3`) | `B22` | `C22` | `D22` | Producto/Servicio 3 |
| `A23` (= `4`) | `B23` | `C23` | `D23` | Producto/Servicio 4 |
| `A24` (= `5`) | `B24` | `C24` | `D24` | Producto/Servicio 5 |
| `A25` (= `6`) | `B25` | `C25` | `D25` | Producto/Servicio 6 |
| `A26` (= `7`) | `B26` | `C26` | `D26` | Producto/Servicio 7 |
| `A27` (= `8`) | `B27` | `C27` | `D27` | Producto/Servicio 8 |
| `A28` (= `9`) | `B28` | `C28` | `D28` | Producto/Servicio 9 |
| `A29` (= `10`) | `B29` | `C29` | `D29` | Producto/Servicio 10 |

> **Columna A (N°):** Valores fijos del 1 al 10. **No modificar.**  
> **Columna B:** Nombre descriptivo del producto o servicio.  
> **Columna C:** Unidad de medida (ej. `Gramos`, `Litros`, `Unidad`, `Hora`).  
> **Columna D:** Peso o volumen por unidad en número (ej. `250` para 250 gramos).

---

## Resumen de celdas editables por el agente

| Rango | Cantidad de celdas | Propósito |
|---|---|---|
| `B4:B16` | 13 celdas | Parámetros globales del proyecto |
| `B20:D29` | 30 celdas | Catálogo de productos/servicios (máx. 10) |

**Total celdas a completar: hasta 43**

---

## Reglas para el agente

1. **Nunca modificar** las celdas de etiqueta (columna A filas 4–16) ni los encabezados (fila 19).
2. **Números decimales como porcentaje** deben ingresarse en formato decimal (`0.25`, no `25%`).
3. **Años** deben ser enteros de 4 dígitos (`2025`, no `25`).
4. **Productos vacíos**: si hay menos de 10 productos, las filas sobrantes pueden dejarse en blanco (columnas B, C, D).
5. La hoja de trabajo es `INICIO` — siempre apuntar a esta hoja.
