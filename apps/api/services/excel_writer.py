"""
Excel Writer - Escribe archivos Excel usando configuración dinámica.

Soporta cualquier versión de plantilla definida en excel_templates.yaml.
También expone fill_input1_template() para el pipeline Sprint 1.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.styles import Font, Alignment, PatternFill

from core.exceptions import TemplateError, ErrorCodes

# Mapeo fijo de celdas → coincide con plantilla 1.xlsx
_PARAM_CELLS = {
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
    "impuesto_it": "B16",
}
_PRODUCTOS_FILA_INICIO = 20
_PRODUCTOS_COLS = {"nombre": "B", "unidad_medida": "C", "peso_volumen": "D"}

# Estilos que la plantilla 1.xlsx define para sus celdas de input
# fgColor usa formato AARRGGBB: FF=opaco + FFFFCC=amarillo claro
_YELLOW_FILL = PatternFill(fill_type="solid", fgColor="FFFFFFCC")
_BLUE_FONT   = Font(color="FF0000FF", bold=True, size=10)          # AARRGGBB: opaco azul puro

# Number formats por campo (solo los que necesitan algo distinto de 'General')
_PARAM_NUMBER_FORMATS = {
    "tipo_cambio":  '#,##0.00',   # 6.96
    "inflacion":    '0%',          # 2%
    "horizonte":    '0',           # 5
    "anio_base":    '0',           # 2025
    "anio_inicio":  '0',           # 2026
    "impuesto_iue": '0%',          # 25%
    "impuesto_it":  '0%',          # 3%
}


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

    def __init__(self):
        """Inicializa el escritor."""
        self.config = None  # template_config removed in Sprint 1 cleanup

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
        """Aplica estilos a una sección (opcional)."""
        pass

    def fill_template(
        self,
        template_path: Path,
        output_path: Path,
        parametros: Dict[str, Any],
        productos: List[Dict[str, Any]],
    ) -> Path:
        """
        Rellena la plantilla Excel existente con los datos del plan.

        Abre plantilla 1.xlsx, escribe los valores en las celdas correctas
        y guarda como un archivo nuevo, preservando todo el formato original.

        Args:
            template_path: Ruta a la plantilla .xlsx (plantilla 1.xlsx)
            output_path: Ruta del archivo de salida
            parametros: Dict con parámetros globales del plan
            productos: Lista de productos (máx 10)

        Returns:
            Path al archivo generado
        """
        try:
            wb = load_workbook(template_path)
            ws = wb["INICIO"]

            # Parámetros globales → celdas B4:B16
            for field, cell_addr in _PARAM_CELLS.items():
                value = parametros.get(field)
                if value is None:
                    continue
                cell = ws[cell_addr]
                cell.value = value
                # Aplicar estilo: font azul bold + fill amarillo + number format
                cell.font = _BLUE_FONT
                cell.fill = _YELLOW_FILL
                if field in _PARAM_NUMBER_FORMATS:
                    cell.number_format = _PARAM_NUMBER_FORMATS[field]

            # Productos → filas 20-29, columnas B, C, D
            for i, prod in enumerate(productos[:10]):
                row = _PRODUCTOS_FILA_INICIO + i
                for col_key, col_letter in _PRODUCTOS_COLS.items():
                    cell = ws[f"{col_letter}{row}"]
                    cell.value = prod.get(col_key, "")
                    cell.font = _BLUE_FONT
                    cell.fill = _YELLOW_FILL

            wb.save(output_path)
            return output_path

        except Exception as e:
            raise TemplateError(
                message=f"Error al rellenar plantilla Excel: {str(e)}",
                template_name=str(template_path),
                code=ErrorCodes.EXCEL_WRITE_ERROR,
            )

    def fill_input1_template(
        self,
        plan_id: int,
        plan_data,  # PlanData from models.schemas
        template_path: Path,
        output_path: Path,
    ) -> Path:
        """
        Writes enriched PlanData back into a copy of input1_vacio.xlsx.

        Strategy: label-based row lookup in col A → write value in col B.
        Uses a SEPARATE load_workbook() call (no data_only) so dropdown
        Data Validation lists are preserved.

        Args:
            plan_id:       Plan DB id (used for logging only)
            plan_data:     PlanData Pydantic model from enrichment chain
            template_path: Path to input1_vacio.xlsx (clean template)
            output_path:   Destination path for the filled copy

        Returns:
            output_path
        """
        try:
            # Write pass: NO data_only — preserves dropdowns
            wb = load_workbook(template_path)

            inicio = wb["INICIO"]
            config_sheet = wb["CONFIGURACIÓN METODOLÓGICA"]

            # ── 1. Parámetros Globales (INICIO, kv section) ──────────────
            # NOTE: labels must match col A strings verbatim from input1_vacio.xlsx
            params = plan_data.parametros
            param_map = {
                "Nombre del Proyecto": params.nombre_proyecto,
                "Rubro / Sector": params.rubro_sector,
                "Ciudad": params.ciudad,
                "Departamento": params.departamento,
                "País": params.pais,
                "Moneda": params.moneda,
                "Tipo de Cambio (Bs/USD)": params.tipo_cambio,
                "Fecha de Elaboración": params.fecha_elaboracion,
                "Horizonte del Proyecto (años)": params.horizonte_anios,
                "Nombre del Responsable": params.nombre_responsable,
                "Año Base (Año 0)": params.anio_base,
                "Año Inicio Operaciones": params.anio_inicio_operaciones,
                "N° de Productos/Servicios": params.num_productos_servicios,
            }
            self._write_kv_by_label(inicio, param_map)

            # ── 2. Productos / Servicios (INICIO, table section) ──────────
            self._write_products_by_label(inicio, plan_data.productos)

            # ── 3. Datos del Negocio (INICIO, kv section) ─────────────────
            # NOTE: labels must match col A strings verbatim from input1_vacio.xlsx
            dn = plan_data.datos_negocio
            negocio_map = {
                "Horario de Atención": dn.horario_atencion,
                "Días Laborales/Semana": dn.dias_laborales_semana,
                "Semanas Laborales/Año": dn.semanas_laborales_anio,
                "Horas Laborales/Día": dn.horas_laborales_dia,
                "Zona / Dirección": dn.zona_direccion,
                "Canal de Venta": dn.canal_venta,
                "Capacidad Diaria (unidades)": dn.capacidad_diaria_unidades,
                "N° de Socios/Fundadores": dn.num_socios_fundadores,
            }
            self._write_kv_by_label(inicio, negocio_map)

            # ── 4. Buyer Persona (INICIO, kv section) ─────────────────────
            # NOTE: labels must match col A strings verbatim from input1_vacio.xlsx
            bp = plan_data.buyer_persona
            buyer_map = {
                "Edad Objetivo (rango)": bp.edad_objetivo,
                "Género Objetivo": bp.genero_objetivo,
                "Ocupación Principal": bp.ocupacion_principal,
                "Zona de Residencia Objetivo": bp.zona_residencia_objetivo,
                "Motivaciones de Compra": bp.motivaciones_compra,
                "Canal de Información Preferido": bp.canal_informacion_preferido,
                "Nivel Socioeconómico (NSE)": bp.nivel_socioeconomico,
                "Problema que Resuelve": bp.problema_que_resuelve,
            }
            self._write_kv_by_label(inicio, buyer_map)

            # ── 5. Configuración Metodológica (separate sheet, kv) ────────
            # NOTE: labels must match col A strings verbatim from input1_vacio.xlsx
            cm = plan_data.config_metodologica
            config_map = {
                "Precisión de los resultados": cm.precision_muestra,
                "Tipo de mercado": cm.tipo_mercado,
                "Método de proyección": cm.metodo_proyeccion_ventas,
                "Cómo evolucionarán los precios": cm.evolucion_precios,
                "Método de depreciación": cm.metodo_depreciacion,
                "Dinero para operar": cm.meses_capital_trabajo,
                "¿Necesitás financiamiento externo?": cm.necesita_financiamiento,
                "Forma de pago": cm.forma_pago,
                "Frecuencia de pago": cm.frecuencia_pago,
            }
            self._write_kv_by_label(config_sheet, config_map)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            wb.save(output_path)
            return output_path

        except TemplateError:
            raise
        except Exception as e:
            raise TemplateError(
                message=f"Error al rellenar Input 1 template: {str(e)}",
                template_name=str(template_path),
                code=ErrorCodes.EXCEL_WRITE_ERROR,
            )

    # ── Private helpers for fill_input1_template ──────────────────────────

    def _write_kv_by_label(
        self, sheet: Worksheet, label_value_map: Dict[str, Any]
    ) -> None:
        """
        Scans col A for each label in label_value_map and writes the
        corresponding value into col B of the same row.

        Labels that are not found in col A are silently skipped.
        None values are also skipped (leave template cell as-is).
        """
        for row in sheet.iter_rows(min_col=1, max_col=1):
            cell = row[0]
            raw = cell.value
            if raw is None:
                continue
            label = str(raw).strip()
            if label in label_value_map:
                value = label_value_map[label]
                if value is not None:
                    target = sheet.cell(row=cell.row, column=2)
                    # Skip MergedCell non-master cells (read-only in openpyxl)
                    from openpyxl.cell.cell import MergedCell
                    if not isinstance(target, MergedCell):
                        target.value = value

    def _write_products_by_label(
        self, sheet: Worksheet, productos: list
    ) -> None:
        """
        Locates the PRODUCTOS / SERVICIOS section header in col A,
        then writes each ProductoData row below it (col A=numero,
        col B=nombre, col C=tipo, col D=unidad_medida, col E=precio_bs).

        Writes only as many rows as there are productos — existing
        blank rows below are left intact.
        """
        anchor = "PRODUCTOS / SERVICIOS"
        header_row: Optional[int] = None

        for row in sheet.iter_rows(min_col=1, max_col=1):
            cell = row[0]
            if cell.value and str(cell.value).strip() == anchor:
                # data rows start 2 below: anchor + header row
                header_row = cell.row + 1
                break

        if header_row is None or not productos:
            return

        data_start = header_row + 1
        for idx, prod in enumerate(productos):
            r = data_start + idx
            sheet.cell(row=r, column=1).value = prod.numero
            sheet.cell(row=r, column=2).value = prod.nombre
            sheet.cell(row=r, column=3).value = prod.tipo
            sheet.cell(row=r, column=4).value = prod.unidad_medida
            sheet.cell(row=r, column=5).value = prod.precio_bs
