"""
Excel Writer - Escribe archivos Excel usando configuración dinámica.

Soporta cualquier versión de plantilla definida en excel_templates.yaml.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.styles import Font, Alignment, PatternFill

from services.template_config import TemplateConfig, get_template_config
from core.exceptions import TemplateError, ErrorCodes


class ExcelWriter:
    """
    Escritor genérico de archivos Excel que funciona con cualquier versión de plantilla.

    Usa TemplateConfig para determinar la estructura de celdas.

    Usage:
        writer = ExcelWriter()
        writer.write_file(
            output_path,
            version="v1",
            data={
                "parametros_globales": {...},
                "productos_servicios": [...]
            }
        )
    """

    def __init__(self, template_config: Optional[TemplateConfig] = None):
        """
        Inicializa el escritor.

        Args:
            template_config: Configuración de plantillas. Si es None, usa la default.
        """
        self.config = template_config or get_template_config()

    def write_file(
        self,
        output_path: Path,
        version: str = "v1",
        data: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Escribe un archivo Excel con los datos proporcionados.

        Args:
            output_path: Ruta donde guardar el archivo
            version: Versión de la plantilla
            data: Datos a escribir (por sección)

        Returns:
            Path al archivo guardado

        Raises:
            TemplateError: Si hay error al escribir
        """
        data = data or {}

        try:
            wb = Workbook()
            ws = wb.active

            # Obtener configuración de la plantilla
            template = self.config.get_template(version)
            sheet_name = template.get("sheet", "INICIO")
            ws.title = sheet_name

            # Escribir título
            ws["A1"] = "PLAN DE NEGOCIO"
            ws["A1"].font = Font(bold=True, size=14)
            ws["A1"].alignment = Alignment(horizontal="center")
            ws.merge_cells("A1:D1")

            # Escribir cada sección
            sections = template.get("sections", {})
            current_row = 3

            for section_name, section_config in sections.items():
                current_row = self._write_section(
                    ws,
                    current_row,
                    section_name,
                    section_config,
                    data.get(section_name),
                )

            wb.save(output_path)
            return output_path

        except Exception as e:
            raise TemplateError(
                message=f"Error al generar Excel: {str(e)}",
                template_name=str(output_path),
                code=ErrorCodes.EXCEL_WRITE_ERROR,
            )

    def _write_section(
        self,
        ws: Worksheet,
        start_row: int,
        section_name: str,
        config: Dict[str, Any],
        data: Any,
    ) -> int:
        """
        Escribe una sección en el worksheet.

        Args:
            ws: Worksheet
            start_row: Fila inicial
            section_name: Nombre de la sección
            config: Configuración de la sección
            data: Datos a escribir

        Returns:
            Siguiente fila disponible
        """
        section_type = config.get("type", "key_value")

        # Escribir título de sección
        title_row = start_row
        ws[f"A{title_row}"] = section_name.upper().replace("_", " ")
        ws[f"A{title_row}"].font = Font(bold=True)
        current_row = title_row + 1

        if section_type == "table":
            # Escribir tabla
            return self._write_table(ws, current_row, config, data)
        else:
            # Escribir key-value
            return self._write_key_value(ws, current_row, config, data)

    def _write_key_value(
        self,
        ws: Worksheet,
        start_row: int,
        config: Dict[str, Any],
        data: Optional[Dict[str, Any]],
    ) -> int:
        """
        Escribe datos en formato key-value (parámetros).

        Args:
            ws: Worksheet
            start_row: Fila inicial
            config: Configuración de la sección
            data: Dict con los datos

        Returns:
            Siguiente fila disponible
        """
        data = data or {}
        columns = config.get("columns", {"label": "A", "value": "B"})
        label_col = columns.get("label", "A")
        value_col = columns.get("value", "B")
        fields = config.get("fields", [])

        current_row = start_row

        for field in fields:
            if isinstance(field, dict):
                field_name = field.get("name")
                field_label = field.get("label", field_name)
                field_type = field.get("type", "string")
                field_value = data.get(field_name)

                # Usar default si no hay valor
                if field_value is None:
                    field_value = field.get("default")
            else:
                # Formato antiguo
                field_name = field
                field_label = field
                field_value = data.get(field_name)
                field_type = "string"

            # Escribir etiqueta
            ws[f"{label_col}{current_row}"] = field_label
            ws[f"{label_col}{current_row}"].font = Font(bold=True)

            # Escribir valor
            if field_value is not None:
                # Formatear según tipo
                if field_type == "percentage":
                    # Mostrar como porcentaje
                    ws[f"{value_col}{current_row}"] = field_value
                    ws[f"{value_col}{current_row}"].number_format = "0.00%"
                elif field_type == "float":
                    ws[f"{value_col}{current_row}"] = field_value
                    ws[f"{value_col}{current_row}"].number_format = "0.00"
                else:
                    ws[f"{value_col}{current_row}"] = field_value

            current_row += 1

        return current_row + 1  # Espacio extra

    def _write_table(
        self,
        ws: Worksheet,
        start_row: int,
        config: Dict[str, Any],
        data: Optional[List[Dict[str, Any]]],
    ) -> int:
        """
        Escribe datos en formato tabla (productos).

        Args:
            ws: Worksheet
            start_row: Fila inicial (incluye encabezado)
            config: Configuración de la sección
            data: Lista de dicts con las filas

        Returns:
            Siguiente fila disponible
        """
        data = data or []
        columns_config = config.get("columns", {})
        max_rows = config.get("max_rows", 10)

        # Escribir encabezados
        header_row = start_row

        # Título de la sección (ya escrito en _write_section)
        current_row = header_row + 1

        # Encabezados de columnas
        col_idx = 1
        for field_name, col_config in columns_config.items():
            if isinstance(col_config, dict):
                col_letter = col_config.get("column", chr(64 + col_idx))
                header = col_config.get("label", field_name)
            else:
                col_letter = col_config
                header = field_name

            ws[f"{col_letter}{current_row}"] = header
            ws[f"{col_letter}{current_row}"].font = Font(bold=True)
            ws[f"{col_letter}{current_row}"].fill = PatternFill(
                start_color="D9E2F3", end_color="D9E2F3", fill_type="solid"
            )
            col_idx += 1

        current_row += 1

        # Escribir datos
        for i, row_data in enumerate(data[:max_rows]):
            for field_name, col_config in columns_config.items():
                if isinstance(col_config, dict):
                    col_letter = col_config.get("column", "A")
                    field_type = col_config.get("type", "string")
                else:
                    col_letter = col_config
                    field_type = "string"

                value = row_data.get(field_name)

                if value is not None:
                    if field_type == "percentage":
                        ws[f"{col_letter}{current_row}"] = value
                        ws[f"{col_letter}{current_row}"].number_format = "0.00%"
                    elif field_type == "float":
                        ws[f"{col_letter}{current_row}"] = value
                        ws[f"{col_letter}{current_row}"].number_format = "0.00"
                    else:
                        ws[f"{col_letter}{current_row}"] = value

            current_row += 1

        return current_row + 1  # Espacio extra

    def apply_style(
        self, ws: Worksheet, section: str, start_row: int, end_row: int
    ) -> None:
        """
        Aplica estilos a una sección (opcional).

        Args:
            ws: Worksheet
            section: Nombre de la sección
            start_row: Fila inicial
            end_row: Fila final
        """
        # TODO: Implementar estilos personalizados
        pass
