# Ejemplo Rellenado: `plantilla_1_-rellenado.xlsx`

> Documento de referencia para el agente de IA.  
> Muestra los valores exactos ingresados en cada celda del caso de ejemplo **"Shawarma Cruz"**.  
> Usar como guía de formato y validación al generar nuevos llenados.

---

## Hoja: `INICIO`

### Sección 1 — PARÁMETROS GLOBALES

| Celda valor | Campo | Valor en el ejemplo | Tipo |
|---|---|---|---|
| `B4` | Nombre del Proyecto | `Shawarma Cruz` | Texto |
| `B5` | Rubro / Sector | `Restaurant` | Texto |
| `B6` | Ciudad | `Santa Cruz de la Sierra` | Texto |
| `B7` | Departamento | `Santa Cruz` | Texto |
| `B8` | País | `Bolivia` | Texto |
| `B9` | Moneda | `Bs` | Texto |
| `B10` | Tipo de Cambio (Bs/$us) | `6.96` | Número decimal |
| `B11` | Tasa de Inflación Anual | `0.02` | Decimal (= 2%) |
| `B12` | Horizonte de Proyección (años) | `5` | Entero |
| `B13` | Año Base (Año 0) | `2025` | Entero |
| `B14` | Año Inicio Operaciones | `2026` | Entero |
| `B15` | Impuesto IUE (%) | `0.25` | Decimal (= 25%) |
| `B16` | Impuesto IT (%) | `0.03` | Decimal (= 3%) |

---

### Sección 2 — PRODUCTOS / SERVICIOS

| Fila | `A` (N°) | `B` (Nombre del Producto) | `C` (Unidad de Medida) | `D` (Peso/Vol por Unidad) |
|---|---|---|---|---|
| 20 | `1` | `Shawarma De Carne De Cordero` | `Gramos` | `250` |
| 21 | `2` | `Shawarma De Carne De Pollo` | `Gramos` | `250` |
| 22 | `3` | `Shawarma De Carne De Res` | `Gramos` | `250` |
| 23 | `4` | _(vacío)_ | _(vacío)_ | _(vacío)_ |
| 24 | `5` | _(vacío)_ | _(vacío)_ | _(vacío)_ |
| 25 | `6` | _(vacío)_ | _(vacío)_ | _(vacío)_ |
| 26 | `7` | _(vacío)_ | _(vacío)_ | _(vacío)_ |
| 27 | `8` | _(vacío)_ | _(vacío)_ | _(vacío)_ |
| 28 | `9` | _(vacío)_ | _(vacío)_ | _(vacío)_ |
| 29 | `10` | _(vacío)_ | _(vacío)_ | _(vacío)_ |

> Solo se registraron 3 productos de los 10 disponibles.  
> Las filas 23–29 tienen el número de ítem en columna A pero columnas B, C y D vacías.

---

## Observaciones del ejemplo (útiles para validación del agente)

| Aspecto | Valor observado | Regla inferida |
|---|---|---|
| Porcentajes | `0.02`, `0.25`, `0.03` | Siempre en decimal, nunca con símbolo `%` |
| Tipo de cambio | `6.96` | Número flotante, punto como separador decimal |
| Años | `2025`, `2026` | Entero de 4 dígitos |
| Horizonte | `5` | Entero pequeño (típicamente 3–10) |
| Unidad de medida | `Gramos` | Texto libre, capitalizado |
| Peso por unidad | `250` | Número entero o decimal sin unidad (la unidad va en col C) |
| Moneda | `Bs` | Símbolo o código corto, no nombre completo |
| País/Depto/Ciudad | Texto completo | Sin abreviaciones |

---

## JSON de referencia para el agente

```json
{
  "hoja": "INICIO",
  "parametros_globales": {
    "B4": "Shawarma Cruz",
    "B5": "Restaurant",
    "B6": "Santa Cruz de la Sierra",
    "B7": "Santa Cruz",
    "B8": "Bolivia",
    "B9": "Bs",
    "B10": 6.96,
    "B11": 0.02,
    "B12": 5,
    "B13": 2025,
    "B14": 2026,
    "B15": 0.25,
    "B16": 0.03
  },
  "productos": [
    {"fila": 20, "B": "Shawarma De Carne De Cordero", "C": "Gramos", "D": 250},
    {"fila": 21, "B": "Shawarma De Carne De Pollo",   "C": "Gramos", "D": 250},
    {"fila": 22, "B": "Shawarma De Carne De Res",     "C": "Gramos", "D": 250}
  ]
}
```

> Este JSON puede usarse directamente como estructura de salida del agente para luego escribir en el Excel con `openpyxl`.
