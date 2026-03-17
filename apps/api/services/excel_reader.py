"""
Excel Reader - Lee archivos Excel usando configuración dinámica.

Soporta cualquier versión de plantilla definida en excel_templates.yaml.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from services.template_config import TemplateConfig, get_template_config
from core.exceptions import ValidationError, ProcessingError, ErrorCodes


class ExcelReader:
    """
    Lector genérico de archivos Excel que funciona con cualquier versión de plantilla.

    Usa TemplateConfig para determinar la estructura de celdas.

    Usage:
        reader = ExcelReader()
        data = reader.read_file("plantilla.xlsx", version="v1")
        params = data["parametros_globales"]
        products = data["productos_servicios"]
    """

    def __init__(self, template_config: Optional[TemplateConfig] = None):
        """
        Inicializa el lector.

        Args:
            template_config: Configuración de plantillas. Si es None, usa la default.
        """
        self.config = template_config or get_template_config()

    def read_file(self, file_path: Path, version: str = "v1") -> Dict[str, Any]:
        """
        Lee un archivo Excel completo según la versión de plantilla.

        Args:
            file_path: Ruta al archivo Excel
            version: Versión de la plantilla (ej: "v1", "v2")

        Returns:
            Dict con todas las secciones:
            {
                "parametros_globales": {...},
                "productos_servicios": [...],
                ...
            }

        Raises:
            ProcessingError: Si no puede leer el archivo
            ValidationError: Si faltan campos requeridos
        """
        # Cargar workbook
        try:
            wb = load_workbook(file_path, data_only=True)
        except Exception as e:
            raise ProcessingError(
                message=f"Error al abrir Excel: {str(e)}",
                file_name=str(file_path),
                operation="abrir",
                code=ErrorCodes.EXCEL_READ_ERROR,
            )

        # Obtener configuración de la plantilla
        template = self.config.get_template(version)
        sheet_name = template.get("sheet", "INICIO")

        # Verificar que existe la hoja
        if sheet_name not in wb.sheetnames:
            raise ProcessingError(
                message=f"Hoja '{sheet_name}' no encontrada",
                file_name=str(file_path),
                operation="leer",
                code=ErrorCodes.EXCEL_READ_ERROR,
            )

        ws = wb[sheet_name]

        # Leer todas las secciones
        result = {}
        sections = template.get("sections", {})

        for section_name in sections.keys():
            result[section_name] = self.read_section(ws, version, section_name)

        wb.close()

        return result

    def read_section(self, ws: Worksheet, version: str, section: str) -> Any:
        """
        Lee una sección específica del worksheet.

        Detecta automáticamente si es key-value o table.

        Args:
            ws: Worksheet de openpyxl
            version: Versión de la plantilla
            section: Nombre de la sección

        Returns:
            Dict (key-value) o List (table) con los datos
        """
        section_config = self.config.get_section(version, section)
        section_type = section_config.get("type", "key_value")

        if section_type == "table":
            return self._read_table(ws, section_config)
        else:
            return self._read_key_value(ws, section_config)

    def _read_key_value(self, ws: Worksheet, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lee datos en formato key-value (parámetros).

        Formato:
        | A          | B        |
        |------------|----------|
        | Nombre     | Shawarma |
        | Rubro      | Restaurant|

        Args:
            ws: Worksheet
            config: Configuración de la sección

        Returns:
            Dict con los campos
        """
        result = {}

        start_row = config.get("start_row", 4)
        columns = config.get("columns", {"label": "A", "value": "B"})
        value_col = columns.get("value", "B")

        fields = config.get("fields", [])

        for field in fields:
            if isinstance(field, dict):
                field_name = field.get("name")
                field_type = field.get("type", "string")
                row = start_row + fields.index(field)

                value = ws[f"{value_col}{row}"].value
                result[field_name] = self._convert_value(value, field_type)
            else:
                # Formato antiguo (string)
                row = start_row + fields.index(field)
                value = ws[f"{value_col}{row}"].value
                result[field] = self._convert_value(value, "string")

        return result

    def _read_table(
        self, ws: Worksheet, config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Lee datos en formato tabla (productos).

        Formato:
        | A   | B          | C       | D      |
        |-----|------------|---------|--------|
        | N°  | Nombre     | Unidad  | Peso   |
        | 1   | Shawarma   | Gramos  | 250    |
        | 2   | Pollo      | Gramos  | 250    |

        Args:
            ws: Worksheet
            config: Configuración de la sección

        Returns:
            Lista de dicts con las filas
        """
        result = []

        data_start_row = config.get("data_start_row", 20)
        data_end_row = config.get("data_end_row", 29)
        columns_config = config.get("columns", {})

        for row_num in range(data_start_row, data_end_row + 1):
            row_data = {}
            has_data = False

            for field_name, col_config in columns_config.items():
                if isinstance(col_config, dict):
                    col_letter = col_config.get("column", "A")
                    field_type = col_config.get("type", "string")
                else:
                    col_letter = col_config
                    field_type = "string"

                value = ws[f"{col_letter}{row_num}"].value
                converted = self._convert_value(value, field_type)
                row_data[field_name] = converted

                if converted is not None:
                    has_data = True

            if has_data:
                result.append(row_data)

        return result

    def _convert_value(self, value: Any, field_type: str) -> Any:
        """
        Convierte un valor al tipo apropiado.

        Args:
            value: Valor de la celda
            field_type: Tipo esperado (string, integer, float, percentage, year)

        Returns:
            Valor convertido
        """
        if value is None:
            return None

        try:
            if field_type == "string":
                return str(value).strip()

            elif field_type == "integer":
                return int(float(value))  # Handle "250.0" -> 250

            elif field_type == "float":
                return float(value)

            elif field_type == "percentage":
                # Si ya viene como decimal (0.25), dejarlo
                # Si viene como texto ("25%"), convertir
                if isinstance(value, str) and "%" in value:
                    return float(value.replace("%", "")) / 100
                return float(value)

            elif field_type == "year":
                year = int(value)
                # Validar rango
                if 2000 <= year <= 2100:
                    return year
                return None

            else:
                return value

        except (ValueError, TypeError):
            return None

    def validate_required_fields(
        self, data: Dict[str, Any], version: str, section: str
    ) -> List[str]:
        """
        Valida que todos los campos requeridos estén presentes.

        Args:
            data: Datos leídos
            version: Versión de la plantilla
            section: Nombre de la sección

        Returns:
            Lista de errores (vacía si todo ok)
        """
        errors = []
        required = self.config.get_required_fields(version, section)

        section_data = data.get(section, {})

        if isinstance(section_data, dict):
            # Key-value validation
            for field in required:
                if field not in section_data or section_data[field] is None:
                    errors.append(f"Campo requerido faltante: {field}")

        elif isinstance(section_data, list):
            # Table validation
            if not section_data:
                errors.append(f"Sección '{section}' está vacía")
            else:
                for i, row in enumerate(section_data):
                    for field in required:
                        if field not in row or row[field] is None:
                            errors.append(f"Fila {i + 1}: campo '{field}' faltante")

        return errors
