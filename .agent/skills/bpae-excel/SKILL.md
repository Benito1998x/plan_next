---
name: bpae-excel
description: >
  Manejo de archivos Excel para Business Plan Automation Engine usando openpyxl.
  Trigger: When working with Excel files, reading templates, writing data, or manipulating cells.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## When to Use

- Reading client Excel files (plantilla_1.xlsx)
- Writing data to Excel templates
- Extracting data from specific cells
- Generating master Excel files
- Working with openpyxl library

## Critical Patterns

### Template Structure (FIXED)

**Hoja: INICIO**

```
A1: PLAN DE NEGOCIO (title, no modificar)

PARÁMETROS GLOBALES (A3:B16):
A4-B4: Nombre del Proyecto      (OBLIGATORIO)
A5-B5: Rubro / Sector           (OBLIGATORIO)
A6-B6: Ciudad                   (OBLIGATORIO)
A7-B7: Departamento
A8-B8: País
A9-B9: Moneda
A10-B10: Tipo de Cambio (Bs/$us)
A11-B11: Tasa de Inflación Anual
A12-B12: Horizonte de Proyección
A13-B13: Año Base
A14-B14: Año Inicio Operaciones
A15-B15: Impuesto IUE (%)
A16-B16: Impuesto IT (%)

PRODUCTOS / SERVICIOS (A18:D29):
A19: N° | B19: Nombre | C19: Unidad | D19: Peso
A20-D20: Producto 1
A21-D21: Producto 2
...
A29-D29: Producto 10
```

### Reading Excel

```python
from openpyxl import load_workbook

# NEVER modify template structure
wb = load_workbook(file_path, data_only=True)
ws = wb["INICIO"]  # Always use this sheet

# Read specific cells
nombre = ws["B4"].value      # Nombre del Proyecto
rubro = ws["B5"].value       # Rubro
ciudad = ws["B6"].value       # Ciudad

# Read products (rows 20-29)
productos = []
for fila in range(20, 30):
    nombre = ws[f"B{fila}"].value
    if nombre:  # Only if not empty
        productos.append({
            "nombre": nombre,
            "unidad": ws[f"C{fila}"].value or "Gramos",
            "peso": ws[f"D{fila}"].value or 125.0
        })
```

### Writing Excel

```python
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.title = "INICIO"

# Write parameters (column B)
ws["B4"] = "Shawarma Cruz"
ws["B5"] = "Restaurant"
ws["B6"] = "Santa Cruz de la Sierra"
# ... etc

# Write products (rows 20-29)
for i, prod in enumerate(productos):
    fila = 20 + i
    ws[f"A{fila}"] = i + 1
    ws[f"B{fila}"] = prod.nombre
    ws[f"C{fila}"] = prod.unidad_medida
    ws[f"D{fila}"] = prod.peso_volumen

wb.save(output_path)
```

### Data Types

| Field | Type | Format |
|-------|------|--------|
| Nombre | str | Text |
| Tipo de Cambio | float | Decimal (6.96) |
| Porcentajes | float | Decimal (0.25 = 25%) |
| Años | int | 4 digits (2025) |
| Horizonte | int | Years (5) |

**CRITICAL**: Porcentajes como decimales, NO como "25%"

### Validation

```python
# Required fields
CAMPOS_OBLIGATORIOS = ["nombre", "rubro", "ciudad"]

# Validate before processing
for campo in CAMPOS_OBLIGATORIOS:
    if not ws[f"B{4 + campos.index(campo)}"].value:
        raise ValidationError(f"Campo obligatorio faltante: {campo}")
```

### Cell Mapping Reference

```python
CELDAS_PARAMETROS = {
    "nombre": "B4",
    "rubro": "B5",
    "ciudad": "B6",
    "departamento": "B7",
    "pais": "B8",
    "moneda": "B9",
    "tipo_cambio": "B10",
    "inflacion": "B11",
    "horizonte": "B12",
    "anio_base": "B13",
    "anio_inicio": "B14",
    "impuesto_iue": "B15",
    "impuesto_it": "B16"
}
```

## Commands

```bash
# Install openpyxl
pip install openpyxl

# Read Excel
python -c "from openpyxl import load_workbook; wb = load_workbook('file.xlsx'); print(wb.sheetnames)"
```

## Resources

- **Template Map**: See [docs/plantilla_1_mapa.md](../../docs/plantilla_1_mapa.md)
- **Example**: See [docs/plantilla_1_ejemplo_rellenado.md](../../docs/plantilla_1_ejemplo_rellenado.md)
- **Service**: See [apps/api/services/excel_service.py](../apps/api/services/excel_service.py)

## Golden Rules

1. **NEVER** modify template structure (column A labels, row 19 headers)
2. **ALWAYS** use hoja "INICIO"
3. **ALWAYS** validate required fields before processing
4. **PORCENTAJES** as decimals (0.25), not strings ("25%")
5. **YEARS** as 4-digit integers (2025), not 2-digit
6. **CLOSE** workbook after reading: `wb.close()`
7. **USE** `data_only=True` to read calculated values