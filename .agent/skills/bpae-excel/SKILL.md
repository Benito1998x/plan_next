---
name: bpae-excel
description: >
  Manejo dinámico de archivos Excel para Business Plan Automation Engine.
  Soporta múltiples versiones de plantilla y escalado a planes de negocio complejos.
  Trigger: When working with Excel files, reading templates, writing data, or manipulating cells.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "2.0"
---

## When to Use

- Reading client Excel files (any template version)
- Writing data to Excel templates
- Extracting data from specific cells
- Generating master Excel files
- Working with openpyxl library
- Adding new sections/tables to templates

## Architecture Overview

### Template Versioning

```
templates/
├── v1/
│   └── plantilla_1.xlsx          # Current: Simple template
├── v2/
│   └── plantilla_2.xlsx          # Future: More tables
└── v3/
    └── plantilla_completa.xlsx   # Future: Full business plan
```

### Configuration-Driven Cell Mapping

Instead of hardcoding cells, use configuration:

```python
# In config/excel_templates.yaml

templates:
  v1:
    name: "plantilla_1"
    description: "Simple template - Phase 1"
    sheet: "INICIO"
    
    sections:
      parametros_globales:
        start_row: 4
        end_row: 16
        columns:
          label: "A"
          value: "B"
        fields:
          - nombre
          - rubro
          - ciudad
          - departamento
          - pais
          - moneda
          - tipo_cambio
          - inflacion
          - horizonte
          - anio_base
          - anio_inicio
          - impuesto_iue
          - impuesto_it
        required:
          - nombre
          - rubro
          - ciudad
      
      productos_servicios:
        header_row: 19
        data_start_row: 20
        data_end_row: 29
        columns:
          numero: "A"
          nombre: "B"
          unidad: "C"
          peso: "D"
        required:
          - nombre
  
  v2:
    name: "plantilla_2"
    description: "Expanded template - Phase 2"
    # ... additional sections
```

## Critical Patterns

### 1. Dynamic Template Loader

```python
from pathlib import Path
from typing import Dict, Any, List
import yaml

class TemplateConfig:
    """Loads template configuration from YAML."""
    
    def __init__(self, config_path: Path):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
    
    def get_template(self, version: str = "v1") -> Dict[str, Any]:
        """Get template configuration for a specific version."""
        return self.config["templates"].get(version)
    
    def get_section(self, version: str, section: str) -> Dict[str, Any]:
        """Get a specific section configuration."""
        template = self.get_template(version)
        return template["sections"].get(section)
    
    def get_required_fields(self, version: str, section: str) -> List[str]:
        """Get required fields for a section."""
        section_config = self.get_section(version, section)
        return section_config.get("required", [])
```

### 2. Generic Excel Reader

```python
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

class ExcelReader:
    """Generic Excel reader that works with any template version."""
    
    def __init__(self, template_config: TemplateConfig):
        self.config = template_config
    
    def read_section(
        self, 
        ws: Worksheet, 
        version: str, 
        section: str
    ) -> Dict[str, Any]:
        """
        Read a section from worksheet using configuration.
        
        Works with any template version and any section.
        """
        section_config = self.config.get_section(version, section)
        
        if section_config.get("header_row"):
            # Table format (like productos_servicios)
            return self._read_table(ws, section_config)
        else:
            # Key-value format (like parametros_globales)
            return self._read_key_value(ws, section_config)
    
    def _read_key_value(
        self, 
        ws: Worksheet, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Read key-value pairs (parameters section)."""
        result = {}
        
        start = config["start_row"]
        end = config["end_row"]
        label_col = config["columns"]["label"]
        value_col = config["columns"]["value"]
        
        for i, field in enumerate(config["fields"]):
            row = start + i
            value = ws[f"{value_col}{row}"].value
            result[field] = self._convert_value(value, field)
        
        return result
    
    def _read_table(
        self, 
        ws: Worksheet, 
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Read table data (products section)."""
        result = []
        
        start = config["data_start_row"]
        end = config["data_end_row"]
        cols = config["columns"]
        
        for row in range(start, end + 1):
            row_data = {}
            has_data = False
            
            for field, col in cols.items():
                value = ws[f"{col}{row}"].value
                row_data[field] = self._convert_value(value, field)
                if value is not None:
                    has_data = True
            
            if has_data:
                result.append(row_data)
        
        return result
    
    def _convert_value(self, value: Any, field: str) -> Any:
        """Convert value to appropriate type."""
        if value is None:
            return None
        
        # Percentage fields
        if field in ["inflacion", "impuesto_iue", "impuesto_it"]:
            return float(value) if isinstance(value, (int, float)) else None
        
        # Year fields
        if field in ["anio_base", "anio_inicio", "horizonte"]:
            return int(value) if isinstance(value, (int, float)) else None
        
        # Float fields
        if field in ["tipo_cambio", "peso"]:
            return float(value) if isinstance(value, (int, float)) else None
        
        # String fields
        return str(value).strip() if value else None
```

### 3. Generic Excel Writer

```python
class ExcelWriter:
    """Generic Excel writer that works with any template version."""
    
    def write_section(
        self,
        ws: Worksheet,
        version: str,
        section: str,
        data: Any
    ) -> None:
        """
        Write a section to worksheet using configuration.
        
        Automatically determines format (key-value or table).
        """
        section_config = self.config.get_section(version, section)
        
        if section_config.get("header_row"):
            # Table format
            self._write_table(ws, section_config, data)
        else:
            # Key-value format
            self._write_key_value(ws, section_config, data)
    
    def _write_key_value(
        self,
        ws: Worksheet,
        config: Dict[str, Any],
        data: Dict[str, Any]
    ) -> None:
        """Write key-value pairs."""
        start = config["start_row"]
        value_col = config["columns"]["value"]
        
        for i, field in enumerate(config["fields"]):
            row = start + i
            value = data.get(field)
            if value is not None:
                ws[f"{value_col}{row}"] = value
    
    def _write_table(
        self,
        ws: Worksheet,
        config: Dict[str, Any],
        data: List[Dict[str, Any]]
    ) -> None:
        """Write table data."""
        start = config["data_start_row"]
        cols = config["columns"]
        
        for i, row_data in enumerate(data):
            row = start + i
            for field, col in cols.items():
                value = row_data.get(field)
                if value is not None:
                    ws[f"{col}{row}"] = value
```

## Adding New Template Versions

### Step 1: Create Template Configuration

Add new version to `config/excel_templates.yaml`:

```yaml
templates:
  v2:
    name: "plantilla_2"
    description: "Expanded template - Phase 2"
    sheet: "INICIO"
    
    sections:
      parametros_globales:
        # Same as v1...
        
      productos_servicios:
        # Same as v1...
      
      # NEW SECTION
      analisis_mercado:
        header_row: 32
        data_start_row: 33
        data_end_row: 50
        columns:
          aspecto: "A"
          descripcion: "B"
          valoracion: "C"
        required:
          - aspecto
```

### Step 2: Create Template File

Create the actual Excel file in `templates/v2/plantilla_2.xlsx`.

### Step 3: Use New Version

```python
reader = ExcelReader(template_config)
reader.set_version("v2")
data = reader.read_section(ws, "analisis_mercado")
```

## Extending for Complex Business Plans

### Future Structure (v3+)

```yaml
templates:
  v3:
    sheet: "INICIO"
    sections:
      # Basic
      - parametros_globales
      - productos_servicios
      
      # Market Analysis
      - analisis_pestel
      - analisis_porter
      - analisis_foda
      
      # Financial
      - inversion_inicial
      - estructura_costos
      - flujo_caja
      - indicadores_rentabilidad
      
      # Operations
      - capacidad_instalada
      - mano_obra
      - activos_fijos
```

## Validation Pattern

```python
class ExcelValidator:
    """Validate Excel data against template configuration."""
    
    def validate(
        self,
        version: str,
        section: str,
        data: Any
    ) -> List[str]:
        """Return list of validation errors."""
        errors = []
        required = self.config.get_required_fields(version, section)
        
        if isinstance(data, dict):
            # Key-value validation
            for field in required:
                if field not in data or data[field] is None:
                    errors.append(f"Campo requerido faltante: {field}")
        
        elif isinstance(data, list):
            # Table validation
            for i, row in enumerate(data):
                for field in required:
                    if field not in row or row[field] is None:
                        errors.append(f"Fila {i+1}: campo '{field}' faltante")
        
        return errors
```

## Commands

```bash
# Install dependencies
pip install openpyxl pyyaml

# Create template config
python -c "from services.template_config import create_default_config; create_default_config('config/excel_templates.yaml')"

# Validate template
python -c "from services.excel_reader import ExcelReader; r = ExcelReader(); r.validate_template('v1')"
```

## Resources

- **Template Map**: See [docs/plantilla_1_mapa.md](../../docs/plantilla_1_mapa.md)
- **Example**: See [docs/plantilla_1_ejemplo_rellenado.md](../../docs/plantilla_1_ejemplo_rellenado.md)
- **Config**: Will be in `config/excel_templates.yaml` (create as needed)
- **Service**: See [apps/api/services/excel_service.py](../apps/api/services/excel_service.py)

## Golden Rules

1. **NEVER** hardcode cell references - use configuration
2. **ALWAYS** load template config from YAML
3. **SUPPORT** multiple versions via `version` parameter
4. **VALIDATE** required fields before processing
5. **CONVERT** types (percentage, year, float) automatically
6. **EXTEND** by adding new sections to config, not to code
7. **CLOSE** workbook after reading: `wb.close()`
8. **USE** `data_only=True` to read calculated values

## Migration Guide

### From v1 (hardcoded) to v2 (config-driven):

```python
# OLD (hardcoded)
nombre = ws["B4"].value
rubro = ws["B5"].value

# NEW (config-driven)
template_config = TemplateConfig("config/excel_templates.yaml")
reader = ExcelReader(template_config)
params = reader.read_section(ws, "v1", "parametros_globales")
nombre = params["nombre"]
rubro = params["rubro"]
```

### Benefits:
- Easy to add new sections without code changes
- Support for multiple template versions
- Automatic type conversion
- Built-in validation