# Phase 0 Report — Input 1.xlsx Investigation

**Change**: sprint-1-langchain-agent
**Date**: 2026-03-21
**Status**: COMPLETE — gates Phase 1

---

## 1. Anchor Map — INICIO Sheet

Sheet dimensions: 45 rows × 5 columns.

| Section | Exact Col A String (copy-paste) | Row | Merge Range | Bold |
|---------|----------------------------------|-----|-------------|------|
| Parámetros Globales | `'PARÁMETROS GLOBALES DEL PROYECTO'` | 1 | A1:C1 | YES |
| Productos / Servicios | `'PRODUCTOS / SERVICIOS'` | 14 | A14:E14 | YES |
| Datos del Negocio | `'DATOS DEL NEGOCIO'` | 26 | A26:C26 | YES |
| Buyer Persona | `'BUYER PERSONA / SEGMENTACIÓN'` | 36 | A36:C36 | YES |

### Pattern for INICIO sections

All 4 section title rows follow the same pattern:
- Col A is merged across the full content width (A:C or A:E)
- Col A cell is **bold**
- Col B and C are empty (part of the merge)
- Immediately followed by a header row (`Campo | Valor | Notas`) that is also bold but NOT merged

### Header rows (Campo | Valor | Notas)

| Section | Header row |
|---------|-----------|
| Parámetros Globales | Row 2 |
| Datos del Negocio | Row 27 |
| Buyer Persona | Row 37 |

> Productos / Servicios uses a different header (row 15): `N° | Nombre del Producto/Servicio | Tipo | Unidad de Medida | Precio (Bs)` — this is a table, not a KV section.

---

## 2. Anchor Map — CONFIGURACIÓN METODOLÓGICA Sheet

Sheet dimensions: 27 rows × 3 columns.

| Subsection | Exact Col A String (copy-paste) | Row | Merge Range | Bold |
|------------|----------------------------------|-----|-------------|------|
| Sheet title | `'CONFIGURACIÓN METODOLÓGICA'` | 1 | A1:C1 | YES |
| A — Tamaño Muestra | `'A — TAMAÑO DE LA MUESTRA'` | 3 | A3:C3 | YES |
| B — Proyección Ventas | `'B — PROYECCIÓN DE VENTAS Y PRECIOS'` | 8 | A8:C8 | YES |
| C — Depreciación | `'C — DEPRECIACIÓN DE ACTIVOS'` | 13 | A13:C13 | YES |
| D — Capital de Trabajo | `'D — CAPITAL DE TRABAJO'` | 17 | A17:C17 | YES |
| E — Financiamiento | `'E — FINANCIAMIENTO'` | 21 | A21:C21 | YES |
| Footer note (NOT a subsection) | `'Nota: La tasa de descuento para evaluación es 20% fija'` | 27 | A27:C27 | NO |

> Row 27 is a merged note row, NOT a subsection. It has no header row and no data below it. `_scan_section()` must NOT attempt to parse it.

### Header rows (Campo | Valor | Explicación) for CONFIG METOD.

| Subsection | Header row |
|------------|-----------|
| A | Row 4 |
| B | Row 9 |
| C | Row 14 |
| D | Row 18 |
| E | Row 22 |

---

## 3. Complete Field Map — INICIO Sheet

### 3.1 — Parámetros Globales (rows 3–12)

| Row | Col A Label (exact) | Col B Current Value | Type | Has Dropdown | Dropdown Options |
|-----|---------------------|---------------------|------|--------------|-----------------|
| 3 | `'Nombre del Proyecto'` | `'Shawarma Cruz'` | str | NO | — |
| 4 | `'Rubro / Sector'` | `'Alimentación y Bebidas'` | str | YES (B4) | `Alimentación y Bebidas,Comercio al por Menor,Servicios Profesionales,Tecnología y Software,Manufactura / Producción,Turismo y Hospitalidad,Belleza y Estética,Salud y Bienestar,Educación y Capacitación,Agropecuario,Construcción,Transporte y Logística,Otros` |
| 5 | `'Ciudad'` | `'Santa Cruz de la Sierra'` | str | NO | — |
| 6 | `'Departamento'` | `'Santa Cruz'` | str | YES (B6) | `Santa Cruz,La Paz,Cochabamba,Tarija,Potosí,Chuquisaca,Oruro,Beni,Pando` |
| 7 | `'País'` | `'Bolivia'` | str | NO | — (locked) |
| 8 | `'Moneda'` | `'Bs'` | str | YES (B8) | `BOB,USD` |
| 9 | `'Tipo de Cambio (Bs/USD)'` | `6.96` | float | NO | — |
| 10 | `'Fecha de Elaboración'` | `'20/03/2026'` | str | NO | — |
| 11 | `'Horizonte del Proyecto (años)'` | `5` | int | YES (B11) | `3,4,5` |
| 12 | `'Nombre del Responsable'` | `'María Cecilia Vargas'` | str | NO | — |

> Row 13 is empty (gap between sections).

### 3.2 — Datos del Negocio (rows 28–35)

| Row | Col A Label (exact) | Col B Current Value | Type | Has Dropdown | Dropdown Options |
|-----|---------------------|---------------------|------|--------------|-----------------|
| 28 | `'Horario de Atención'` | `'Lunes a Domingo 11:00-22:00'` | str | NO | — |
| 29 | `'Días Laborales/Semana'` | `7` | int | YES (B29) | `5,6,7` |
| 30 | `'Semanas Laborales/Año'` | `50` | int | NO | — (locked) |
| 31 | `'Horas Laborales/Día'` | `8` | int | NO | — (locked) |
| 32 | `'Zona / Dirección'` | `'Centro'` | str | NO | — |
| 33 | `'Canal de Venta'` | `'Ambos'` | str | YES (B33) | `Físico,Online,Ambos` |
| 34 | `'Capacidad Diaria (unidades)'` | `120` | int | NO | — |
| 35 | `'N° de Socios/Fundadores'` | `2` | int | NO | — |

### 3.3 — Buyer Persona (rows 38–45)

| Row | Col A Label (exact) | Col B Current Value | Type | Has Dropdown | Dropdown Options |
|-----|---------------------|---------------------|------|--------------|-----------------|
| 38 | `'Edad Objetivo (rango)'` | `'18-35 años'` | str | NO | — |
| 39 | `'Género Objetivo'` | `'Ambos'` | str | YES (B39) | `Masculino,Femenino,Ambos` |
| 40 | `'Ocupación Principal'` | `'Estudiantes y profesionales'` | str | NO | — |
| 41 | `'Zona de Residencia Objetivo'` | `'Zona Sur'` | str | NO | — |
| 42 | `'Motivaciones de Compra'` | `'Sabor, conveniencia, precio'` | str | NO | — |
| 43 | `'Canal de Información Preferido'` | `'Instagram'` | str | YES (B43) | `Instagram,Facebook,TikTok,WhatsApp,Boca a boca,Google,Televisión,Radio,Otro` |
| 44 | `'Nivel Socioeconómico (NSE)'` | `'C'` | str | YES (B44) | `A,B,C,D,E` |
| 45 | `'Problema que Resuelve'` | `'Ofrece una opción rápida y asequible...'` | str (long) | NO | — |

---

## 4. Complete Field Map — CONFIGURACIÓN METODOLÓGICA Sheet

### A — Tamaño de la Muestra (rows 5–6)

| Row | Col A Label (exact) | Col B Current Value | Has Dropdown | Options |
|-----|---------------------|---------------------|--------------|---------|
| 5 | `'Precisión de los resultados'` | `'95% confianza, 5% margen de error'` | NO | — |
| 6 | `'Tipo de mercado'` | `'Mediano (1.000 - 10.000)'` | YES (B6) | `Grande (más de 10.000 personas),Mediano (1.000 - 10.000),Pequeño (menos de 1.000)` |

> Note: B5 also has a dropdown (B5): `⭐ Excelente,✅ Buena (recomendado),⚡ Rápida` — but this is a "Precisión" quality picker, stored in the same cell logic. The formula1 for B5 contains emoji characters (⭐, ✅, ⚡). openpyxl reads these correctly.

### B — Proyección de Ventas y Precios (rows 10–11)

| Row | Col A Label (exact) | Col B Current Value | Has Dropdown | Options |
|-----|---------------------|---------------------|--------------|---------|
| 10 | `'Método de proyección'` | `'Tendencia lineal'` | YES (B10) | `Regresión Lineal (recomendado),Incremento Porcentual Fijo` |
| 11 | `'Cómo evolucionarán los precios'` | `'Inflación anual 3.5% (BCB)'` | YES (B11) | `Ajuste por inflación,Precio constante,Incremento fijo anual` |

### C — Depreciación de Activos (row 15)

| Row | Col A Label (exact) | Col B Current Value | Has Dropdown | Options |
|-----|---------------------|---------------------|--------------|---------|
| 15 | `'Método de depreciación'` | `'Línea recta'` | YES (B15) | `Línea Recta (recomendado),Suma de Dígitos,Doble Saldo Decreciente` |

### D — Capital de Trabajo (row 19)

| Row | Col A Label (exact) | Col B Current Value | Has Dropdown | Options |
|-----|---------------------|---------------------|--------------|---------|
| 19 | `'Dinero para operar'` | `2` | YES (B19) | `1 mes de gastos,2 meses de gastos,⭐ 3 meses de gastos (recomendado),6 meses de gastos` |

> Note: current value is integer `2` (months), not the full dropdown string. `_extract_kv()` will receive an integer for this cell when `data_only=True`.

### E — Financiamiento (rows 23–25)

| Row | Col A Label (exact) | Col B Current Value | Has Dropdown | Options |
|-----|---------------------|---------------------|--------------|---------|
| 23 | `'¿Necesitás financiamiento externo?'` | `'Sí. con banco'` | YES (B23) | `Sí. con banco,Sí. con inversores,No. capital propio` |
| 24 | `'Forma de pago'` | `'No aplica'` | YES (B24) | `Cuota fija mensual (Francés),Cuota decreciente (Alemán),Pago al final (Bullet)` |
| 25 | `'Frecuencia de pago'` | `'Anual'` | YES (B25) | `Mensual,Bimestral,Trimestral,Semestral,Anual` |

---

## 5. Products Table Schema (INICIO, rows 15–25)

**Section anchor row**: 14 — `'PRODUCTOS / SERVICIOS'` (merged A14:E14, bold)
**Header row**: 15

| Col | Letter | Header (exact) | Has Dropdown | Options |
|-----|--------|----------------|--------------|---------|
| 1 | A | `'N°'` | NO | — (row index integer) |
| 2 | B | `'Nombre del Producto/Servicio'` | NO | — |
| 3 | C | `'Tipo'` | YES (C16:C25) | `Producto,Servicio` |
| 4 | D | `'Unidad de Medida'` | YES (D16:D25) | `Unidad,Kilogramo (kg),Gramo (g),Litro (L),Mililitro (mL),Metro (m),Metro cuadrado (m²),Caja,Bolsa,Paquete,Porción,Servicio,Hora,Día,Mes,Consulta,Otro` |
| 5 | E | `'Precio (Bs)'` | NO | — (numeric) |

**Data rows**: 16–25 (10 slots)
**Non-empty data rows in sample file**: 16, 17, 18 (3 products)
**Empty rows** (rows 19–25): Col A contains integer index (4–10), all other cols are None.
**Termination logic**: stop when col B is None (not col A, since col A always has an index number).

---

## 6. Dropdown Preservation Test Result

**Script**: `test_dropdown_preservation.py`
**Method**: `load_workbook(keep_vba=False, data_only=False)` → write B3 → save → reload → count DV objects

```
DataValidation objects BEFORE write: 11
DataValidation objects AFTER write:  11
SqRef sets match: True
B3 write confirmed: True

DROPDOWNS PRESERVED: YES
```

openpyxl 3.1.5 with `keep_vba=False` preserves all 11 DataValidation objects across a write+save+reload cycle. The `fill_input1_template()` method is safe to use without any special handling.

---

## 7. Surprises and Issues Found

### 7.1 — Row gaps between sections (CRITICAL for `_scan_section()`)

The sheet has intentional empty rows between sections. These are the gaps:

| Location | Empty rows |
|----------|-----------|
| INICIO: Between parámetros globales and products | Row 13 |
| INICIO: No gap — products ends row 25, datos negocio starts row 26 immediately |
| CONFIG METOD: Between sheet title and section A | Row 2 |
| CONFIG METOD: Between section A and B | Row 7 |
| CONFIG METOD: Between section B and C | Row 12 |
| CONFIG METOD: Between section C and D | Row 16 |
| CONFIG METOD: Between section D and E | Row 20 |
| CONFIG METOD: Row 26 is empty between E and the note |

**Implication**: `_scan_section()` must search the ENTIRE column A for the anchor string, not assume a fixed offset from a previous section. A simple linear scan of col A until the string matches is the correct approach.

### 7.2 — Productos section uses DIFFERENT structure

Unlike the 3 KV sections, PRODUCTOS / SERVICIOS is a **table** (not key-value). The header row has 5 columns (N°, Nombre, Tipo, Unidad, Precio). `_extract_table()` must be called for this section, NOT `_extract_kv()`.

The termination condition for the table is: col B value is None (since col A always has a number 1–10, even for empty rows).

### 7.3 — CONFIG METOD: `Dinero para operar` B19 value is integer, not string

When read with `data_only=True`, B19 returns the integer `2`, not the display string "2 meses de gastos". The LangChain enrichment chain must handle raw integer/float values in the raw_dict and normalize them.

### 7.4 — CONFIG METOD B5 has dropdown with emoji characters

`B5` formula1: `"⭐ Excelente,✅ Buena (recomendado),⚡ Rápida"` — openpyxl reads and preserves emoji correctly in formula1 strings (confirmed in test). No issue for reading.

### 7.5 — Row 27 in CONFIG METOD is a note, not a subsection

`'Nota: La tasa de descuento para evaluación es 20% fija'` is a merged row with no children. `_scan_section()` must not try to parse it. This row only appears in the merged cells list — it will never be passed as a section anchor to `Input1Reader`.

### 7.6 — INICIO has no `Año Base` / `Año Inicio Operaciones` / tax fields

The design.md `PlanData` schema includes `anio_base`, `anio_inicio_operaciones`, `impuesto_iue`, `impuesto_it` — but none of these fields exist in Input 1.xlsx. The LangChain enrichment chain will supply these as **defaults** (2025, 2026, 25.0, 3.0) since they are not in the raw_dict. The `Input1Reader` will simply not return these keys; the enrichment chain / PlanData defaults cover them.

### 7.7 — INICIO has no `descripcion_negocio`, `mision`, `vision`, `propuesta_valor`, `ventaja_competitiva`, `modelo_negocio`, `etapa_negocio`

These `DatosNegocio` fields from `PlanData` do not exist in Input 1.xlsx. The raw_dict will be missing them entirely. The LangChain enrichment chain is responsible for inferring or leaving them as None.

### 7.8 — `Nombre del Responsable` (row 12) maps to no field in PlanData

This field exists in the sheet but has no corresponding column in `PlanData` or any DB table. It should be extracted but ignored (or could map to a future field). For now, the raw_dict will carry it but the chain prompt should note it's metadata.

---

## 8. Exact Anchor Strings for `Input1Reader` (copy-paste ready)

### INICIO sheet anchors

```python
# Section title anchors (col A, merged, bold)
ANCHOR_PARAMS_GLOBALES   = "PARÁMETROS GLOBALES DEL PROYECTO"
ANCHOR_PRODUCTOS         = "PRODUCTOS / SERVICIOS"
ANCHOR_DATOS_NEGOCIO     = "DATOS DEL NEGOCIO"
ANCHOR_BUYER_PERSONA     = "BUYER PERSONA / SEGMENTACIÓN"
```

### CONFIGURACIÓN METODOLÓGICA sheet anchors

```python
# Subsection anchors (col A, merged, bold)
ANCHOR_CONFIG_A = "A — TAMAÑO DE LA MUESTRA"
ANCHOR_CONFIG_B = "B — PROYECCIÓN DE VENTAS Y PRECIOS"
ANCHOR_CONFIG_C = "C — DEPRECIACIÓN DE ACTIVOS"
ANCHOR_CONFIG_D = "D — CAPITAL DE TRABAJO"
ANCHOR_CONFIG_E = "E — FINANCIAMIENTO"
```

### Products table header row (row 15) — exact strings

```python
PRODUCTOS_HEADERS = {
    "B": "Nombre del Producto/Servicio",
    "C": "Tipo",
    "D": "Unidad de Medida",
    "E": "Precio (Bs)",
}
```

---

## 9. Implementation Guidance for Phase 1

### `_scan_section(ws, section_title)` logic

```python
# Scan ALL of col A looking for an exact string match
for row in range(1, ws.max_row + 1):
    if ws.cell(row=row, column=1).value == section_title:
        return row  # returns the ANCHOR row itself
# If not found, raise or return -1
```

The anchor row IS the section title row. The header row (`Campo | Valor`) is always anchor_row + 1 (for INICIO) or anchor_row + 1 for CONFIG METOD subsections. Data rows start at anchor_row + 2.

**Exception**: PRODUCTOS / SERVICIOS has anchor at row 14, header at row 15 (anchor+1), data at rows 16–25 (anchor+2 through anchor+11).

### `_extract_kv(ws, header_row)` termination condition

Stop reading when col A is None AND col B is None. In INICIO, empty row 13 between parámetros globales and productos is the natural stop. For sections immediately adjacent (e.g., DATOS DEL NEGOCIO ends row 35, BUYER PERSONA starts row 36), the stop condition is hitting a merged/bold section title in col A (its value will be the next anchor string).

A robust approach: stop when `ws.cell(row, 1).value is None` (both A and B are None means end of section). This works for all sections that have a gap row before the next anchor.

**CRITICAL edge case**: DATOS DEL NEGOCIO ends at row 35, and BUYER PERSONA anchor is at row 36 with NO gap row between them. `_extract_kv()` reading DATOS DEL NEGOCIO should stop when it encounters col A = `'BUYER PERSONA / SEGMENTACIÓN'` (a non-null, non-field value). The safest termination: stop when `ws.cell(row, 1).value` is in the known anchor set OR when both A and B are None.

### `_extract_table(ws, header_row)` termination condition

For PRODUCTOS: stop when col B (Nombre del Producto/Servicio) is None. Col A will always have an integer, so cannot be used as termination.

---

*Phase 0 COMPLETE. All findings are definitive. Phase 1 may proceed.*
