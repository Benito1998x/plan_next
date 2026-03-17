---
name: bpae-word
description: >
  Generación de documentos Word para Business Plan Automation Engine usando python-docx.
  Trigger: When working with Word documents, creating business plans, or generating DOCX files.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## When to Use

- Generating Word documents from Excel data
- Creating business plan documents
- Inserting tables from Excel into Word
- Adding titles and sections to documents
- Working with python-docx library

## Critical Patterns

### Document Structure

```
PLAN DE NEGOCIO: [Business Name]

1. Datos Globales
   [Tabla de Parámetros Globales pegada desde Excel]

2. Productos / Servicios
   [Tabla de Productos pegada desde Excel]

[... más secciones según requerimiento ...]
```

### Creating Word Document

```python
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Create document
doc = Document()

# Title
title = doc.add_heading("PLAN DE NEGOCIO", level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

# Section heading
doc.add_heading("1. Datos Globales", level=1)

# Paragraph
doc.add_paragraph("Información del proyecto:")

# Save
doc.save(output_path)
```

### Adding Tables from Excel

```python
from docx import Document
from openpyxl import load_workbook

def add_excel_table_to_word(doc, ws, start_row, end_row, title):
    """Copy table from Excel worksheet to Word document."""
    # Add section title
    doc.add_heading(title, level=2)
    
    # Create table
    num_rows = end_row - start_row + 1
    num_cols = 2  # For parameters (Campo, Valor)
    
    table = doc.add_table(rows=num_rows, cols=num_cols)
    table.style = "Table Grid"
    
    # Fill table
    for i, row in enumerate(range(start_row, end_row + 1)):
        cells = table.rows[i].cells
        # Label
        cells[0].text = ws[f"A{row}"].value or ""
        # Value  
        cells[1].text = str(ws[f"B{row}"].value) if ws[f"B{row}"].value else ""
    
    # Format first row as header
    for cell in table.rows[0].cells:
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
```

### Styling Tables

```python
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

def style_table(table):
    """Apply consistent styling to table."""
    # Center table
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    # Style header row
    for cell in table.rows[0].cells:
        # Bold text
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(11)
        
        # Shading (optional)
        shading = qn('w:shd')
        cell._tc.get_or_add_tcPr().append(
            parse_xml(r'<w:shd {} w:fill="D9E2F3"/>'.format(shading))
        )
```

### Formatting Values

```python
def format_value(value, field_type):
    """Format values for Word display."""
    if value is None:
        return ""
    
    if field_type == "percentage":
        # 0.25 -> "25%"
        return f"{float(value) * 100:.0f}%"
    elif field_type == "currency":
        # 6.96 -> "Bs 6.96"
        return f"Bs {float(value):.2f}"
    elif field_type == "year":
        # 2025 -> "2025"
        return str(int(value))
    else:
        return str(value)
```

### Common Methods

```python
class WordService:
    def create_business_plan(self, plan_data: dict, output_path: Path) -> Path:
        """Create complete business plan document."""
        doc = Document()
        
        # Title
        title = doc.add_heading(
            f"PLAN DE NEGOCIO: {plan_data['nombre']}", 
            level=0
        )
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Section 1: Global Parameters
        doc.add_heading("1. Datos Globales", level=1)
        self._add_parameters_table(doc, plan_data["parametros"])
        
        # Section 2: Products
        doc.add_heading("2. Productos / Servicios", level=1)
        self._add_products_table(doc, plan_data["productos"])
        
        doc.save(output_path)
        return output_path
```

### Reading from Excel to Word

```python
def generar_word_desde_excel(self, excel_path: Path, output_path: Path):
    """Generate Word document from Excel template."""
    # Read Excel
    wb = load_workbook(excel_path, data_only=True)
    ws = wb["INICIO"]
    
    # Create Word
    doc = Document()
    
    # Title
    nombre = ws["B4"].value or "Sin Nombre"
    doc.add_heading(f"PLAN DE NEGOCIO: {nombre}", level=0)
    
    # Parameters table
    doc.add_heading("1. Datos Globales", level=1)
    params_table = doc.add_table(rows=13, cols=2)
    
    param_labels = [
        ("Nombre del Proyecto", "B4"),
        ("Rubro / Sector", "B5"),
        ("Ciudad", "B6"),
        ("Departamento", "B7"),
        ("País", "B8"),
        ("Moneda", "B9"),
        ("Tipo de Cambio", "B10"),
        ("Tasa de Inflación", "B11"),
        ("Horizonte (años)", "B12"),
        ("Año Base", "B13"),
        ("Año Inicio", "B14"),
        ("Impuesto IUE", "B15"),
        ("Impuesto IT", "B16")
    ]
    
    for i, (label, cell) in enumerate(param_labels):
        row = params_table.rows[i]
        row.cells[0].text = label
        row.cells[1].text = str(ws[cell].value or "")
    
    # Products table
    doc.add_heading("2. Productos / Servicios", level=1)
    # ... add products
    
    wb.close()
    doc.save(output_path)
    return output_path
```

## Commands

```bash
# Install python-docx
pip install python-docx

# Test document creation
python -c "from docx import Document; doc = Document(); doc.add_heading('Test', 0); doc.save('test.docx')"
```

## Resources

- **python-docx docs**: https://python-docx.readthedocs.io/
- **Service reference**: See WordService implementation (pending)

## Golden Rules

1. **ALWAYS** use `data_only=True` when reading Excel values
2. **NEVER** hardcode cell references - use constants or mapping
3. **FORMAT** percentages as "25%" not "0.25" in Word display
4. **CENTER** main title with `WD_ALIGN_PARAGRAPH.CENTER`
5. **STYLE** tables consistently (Table Grid)
6. **CLOSE** Excelworkbook after reading: `wb.close()`
7. **USE** level 0 for title, level 1 for sections, level 2 for subsections
8. **SEPARATE** data extraction from formatting logic