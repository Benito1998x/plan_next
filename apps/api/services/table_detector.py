"""
Table Detector - Detecta tablas dinámicamente en Excel.

Busca patrones por contenido, no por posición fija.
Tolerante a variaciones en la posición de las tablas.
"""

from typing import List, Dict, Any, Optional, Tuple
from openpyxl.worksheet.worksheet import Worksheet


class TableDetector:
    """
    Detecta tablas en Excel por contenido, no por posición fija.

    Busca:
    - Títulos de sección ("PARÁMETROS GLOBALES", "PRODUCTOS / SERVICIOS")
    - Encabezados de tabla
    - Patrones de datos

    Usage:
        detector = TableDetector()
        params_range = detector.find_section(ws, "PARÁMETROS GLOBALES")
        products_range = detector.find_table(ws, ["N°", "Nombre", "Unidad", "Peso"])
    """

    # Patrones de títulos de sección (variaciones comunes)
    SECTION_PATTERNS = {
        "parametros_globales": [
            "PARÁMETROS GLOBALES",
            "PARAMETROS GLOBALES",
            "Parámetros Globales",
            "Parametros Globales",
            "DATOS GLOBALES",
            "Datos Globales",
            "INFORMACIÓN GENERAL",
            "Información General",
        ],
        "productos_servicios": [
            "PRODUCTOS / SERVICIOS",
            "PRODUCTOS Y SERVICIOS",
            "Productos / Servicios",
            "Productos y Servicios",
            "CATÁLOGO",
            "Catalogo",
            "PRODUCTOS",
            "Productos",
        ],
    }

    # Patrones de encabezados de tabla
    HEADER_PATTERNS = {
        "productos_servicios": [
            ["N°", "Nombre del Producto", "Unidad de Medida", "Peso/Vol por Unidad"],
            ["N°", "Nombre", "Unidad", "Peso"],
            ["No", "Producto", "Unidad", "Peso"],
            ["#", "Nombre del Producto", "Unidad de Medida", "Peso/Vol"],
        ]
    }

    def __init__(self):
        """Inicializa el detector."""
        pass

    def find_section(
        self, ws: Worksheet, section_name: str, max_row: int = 50
    ) -> Optional[Tuple[int, int]]:
        """
        Busca una sección por su título.

        Args:
            ws: Worksheet
            section_name: Nombre de la sección (ej: "parametros_globales")
            max_row: Máxima fila a buscar

        Returns:
            Tupla (fila_inicio, fila_fin) o None si no encuentra
        """
        patterns = self.SECTION_PATTERNS.get(section_name, [])

        for row in range(1, max_row + 1):
            cell_value = ws[f"A{row}"].value
            if cell_value:
                cell_str = str(cell_value).strip().upper()
                for pattern in patterns:
                    if pattern.upper() in cell_str:
                        # Encontró el título
                        start_row = row + 1  # Datos empiezan después del título

                        # Buscar fin de sección (próximo título o fila vacía)
                        end_row = self._find_section_end(ws, start_row, max_row)

                        return (start_row, end_row)

        return None

    def _find_section_end(self, ws: Worksheet, start_row: int, max_row: int) -> int:
        """
        Encuentra el final de una sección.

        Busca:
        - Fila completamente vacía
        - Próximo título de sección
        """
        for row in range(start_row, max_row + 1):
            # Verificar si la fila está vacía
            is_empty = self._is_row_empty(ws, row)
            if is_empty:
                return row - 1

            # Verificar si es otro título de sección
            if self._is_section_title(ws, row):
                return row - 1

        return max_row

    def _is_row_empty(self, ws: Worksheet, row: int) -> bool:
        """Verifica si una fila está vacía."""
        for col in range(1, 10):  # Verificar primeras 10 columnas
            if ws.cell(row=row, column=col).value is not None:
                return False
        return True

    def _is_section_title(self, ws: Worksheet, row: int) -> bool:
        """Verifica si una fila es un título de sección."""
        cell_value = ws[f"A{row}"].value
        if cell_value:
            cell_str = str(cell_value).strip().upper()
            for patterns in self.SECTION_PATTERNS.values():
                for pattern in patterns:
                    if pattern.upper() == cell_str:
                        return True
        return False

    def find_table(
        self, ws: Worksheet, expected_headers: List[str], max_row: int = 50
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Busca una tabla por sus encabezados.

        Args:
            ws: Worksheet
            expected_headers: Lista esperada de encabezados
            max_row: Máxima fila a buscar

        Returns:
            Tupla (fila_inicio, fila_fin, col_inicio, col_fin) o None
        """
        # Buscar fila de encabezados
        for row in range(1, max_row + 1):
            # Verificar si esta fila tiene los encabezados
            header_match = self._check_headers(ws, row, expected_headers)

            if header_match:
                start_col, end_col = header_match
                header_row = row

                # Buscar fin de datos
                data_end_row = self._find_data_end(
                    ws, header_row + 1, max_row, start_col
                )

                return (header_row + 1, data_end_row, start_col, end_col)

        return None

    def _check_headers(
        self, ws: Worksheet, row: int, expected_headers: List[str]
    ) -> Optional[Tuple[int, int]]:
        """
        Verifica si una fila tiene los encabezados esperados.

        Returns:
            Tupla (col_inicio, col_fin) si encuentra, None si no
        """
        # Buscar en las primeras 20 columnas
        for start_col in range(1, 20):
            match_count = 0

            for i, expected in enumerate(expected_headers):
                cell_value = ws.cell(row=row, column=start_col + i).value

                if cell_value:
                    cell_str = str(cell_value).strip().lower()
                    expected_str = expected.lower()

                    # Match parcial (nombre contiene la palabra clave)
                    if expected_str in cell_str or cell_str in expected_str:
                        match_count += 1

            # Si al menos 75% de los encabezados coinciden
            if match_count >= len(expected_headers) * 0.75:
                return (start_col, start_col + len(expected_headers) - 1)

        return None

    def _find_data_end(
        self, ws: Worksheet, start_row: int, max_row: int, start_col: int
    ) -> int:
        """
        Encuentra el final de los datos de una tabla.

        Busca:
        - Filas vacías
        - Cambio de sección
        """
        for row in range(start_row, max_row + 1):
            # Verificar si la fila tiene datos
            has_data = False
            for col in range(start_col, start_col + 5):
                if ws.cell(row=row, column=col).value is not None:
                    has_data = True
                    break

            if not has_data:
                return row - 1

        return max_row

    def detect_all_sections(self, ws: Worksheet, max_row: int = 50) -> Dict[str, Any]:
        """
        Detecta todas las secciones conocidas en el worksheet.

        Returns:
            Dict con información de cada sección encontrada:
            {
                "parametros_globales": {"row_start": 4, "row_end": 16},
                "productos_servicios": {"header_row": 19, "data_start": 20, "data_end": 29}
            }
        """
        result = {}

        # Buscar sección de parámetros
        params_range = self.find_section(ws, "parametros_globales", max_row)
        if params_range:
            result["parametros_globales"] = {
                "row_start": params_range[0],
                "row_end": params_range[1],
                "type": "key_value",
            }
        else:
            # Fallback: buscar por patrones de campos conocidos
            result["parametros_globales"] = self._detect_key_value_section(
                ws, ["NOMBRE", "RUBRO", "SECTOR", "CIUDAD"], max_row
            )

        # Buscar tabla de productos
        products_range = self.find_table(
            ws, ["N°", "Nombre", "Unidad", "Peso"], max_row
        )
        if products_range:
            result["productos_servicios"] = {
                "header_row": products_range[0] - 1,
                "data_start": products_range[0],
                "data_end": products_range[1],
                "col_start": products_range[2],
                "col_end": products_range[3],
                "type": "table",
            }
        else:
            # Fallback: buscar por patrones de encabezado
            result["productos_servicios"] = self._detect_table_section(ws, max_row)

        return result

    def _detect_key_value_section(
        self, ws: Worksheet, keywords: List[str], max_row: int
    ) -> Dict[str, Any]:
        """
        Detecta una sección key-value por palabras clave.

        Busca filas con formato:
        | Texto | Valor |
        """
        best_row = None
        best_match_count = 0

        for row in range(1, max_row + 1):
            match_count = 0

            # Verificar si columna A tiene texto y columna B tiene valor
            a_value = ws[f"A{row}"].value
            b_value = ws[f"B{row}"].value

            if a_value and b_value is not None:
                a_str = str(a_value).strip().upper()

                for keyword in keywords:
                    if keyword.upper() in a_str:
                        match_count += 1

            if match_count > best_match_count:
                best_match_count = match_count
                best_row = row

        if best_row and best_match_count > 0:
            return {
                "row_start": best_row,
                "row_end": best_row + 12,  # Aproximación
                "type": "key_value",
            }

        return {"row_start": 4, "row_end": 16, "type": "key_value"}  # Default

    def _detect_table_section(self, ws: Worksheet, max_row: int) -> Dict[str, Any]:
        """
        Detecta una tabla de productos por patrones.

        Busca:
        - Encabezados típicos: N°, Nombre, Producto
        - Datos numéricos consecutivos (1, 2, 3...)
        """
        for row in range(1, max_row + 1):
            # Verificar si hay "N°" o "#" en la fila
            for col in range(1, 10):
                value = ws.cell(row=row, column=col).value
                if value and str(value).strip() in ["N°", "No", "#", "Número"]:
                    # Encontró encabezado
                    return {
                        "header_row": row,
                        "data_start": row + 1,
                        "data_end": row + 10,
                        "col_start": col,
                        "col_end": col + 3,
                        "type": "table",
                    }

        # Default
        return {
            "header_row": 19,
            "data_start": 20,
            "data_end": 29,
            "col_start": 1,
            "col_end": 4,
            "type": "table",
        }
