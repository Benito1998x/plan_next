"""
Input1Reader — reads Input 1.xlsx by scanning section anchor labels.

Uses openpyxl with data_only=True for value reading.
Never hardcodes row numbers. Finds sections by their title strings.

ANCHOR STRINGS are taken verbatim from phase0-report.md.
"""

import re
import openpyxl
from pathlib import Path


# ---------------------------------------------------------------------------
# Anchor strings — INICIO sheet
# ---------------------------------------------------------------------------
INICIO_ANCHORS = {
    "parametros": "PARÁMETROS GLOBALES DEL PROYECTO",
    "productos":  "PRODUCTOS / SERVICIOS",
    "negocio":    "DATOS DEL NEGOCIO",
    "buyer":      "BUYER PERSONA / SEGMENTACIÓN",
}

# ---------------------------------------------------------------------------
# Anchor strings — CONFIGURACIÓN METODOLÓGICA sheet
# ---------------------------------------------------------------------------
CONFIG_ANCHORS = {
    "muestra":        "A — TAMAÑO DE LA MUESTRA",
    "ventas":         "B — PROYECCIÓN DE VENTAS Y PRECIOS",
    "depreciacion":   "C — DEPRECIACIÓN DE ACTIVOS",
    "capital":        "D — CAPITAL DE TRABAJO",
    "financiamiento": "E — FINANCIAMIENTO",
}


class Input1Reader:
    """
    Label-based scanner for Input 1.xlsx.

    Reads both INICIO and CONFIGURACIÓN METODOLÓGICA sheets by locating
    section title anchors in col A, then extracting key-value pairs or
    table rows below each anchor. Row numbers are NEVER hardcoded — the
    reader finds every position dynamically.
    """

    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self._wb = openpyxl.load_workbook(self.filepath, data_only=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read(self) -> dict:
        """
        Reads all sections and returns a raw dict (not yet validated).

        Returns a dict with keys:
            parametros        → dict of label: value
            productos         → list of row dicts
            datos_negocio     → dict of label: value
            buyer_persona     → dict of label: value
            config_metodologica → dict of subsection_key: {label: value}
        """
        inicio = self._wb["INICIO"]
        config = self._wb["CONFIGURACIÓN METODOLÓGICA"]

        anchor_rows_inicio = self._find_anchors(inicio, INICIO_ANCHORS)
        anchor_rows_config = self._find_anchors(config, CONFIG_ANCHORS)

        return {
            "parametros": self._extract_kv(
                inicio, anchor_rows_inicio["parametros"], anchor_rows_inicio
            ),
            "productos": self._extract_table(
                inicio, anchor_rows_inicio["productos"], anchor_rows_inicio
            ),
            "datos_negocio": self._extract_kv(
                inicio, anchor_rows_inicio["negocio"], anchor_rows_inicio
            ),
            "buyer_persona": self._extract_kv(
                inicio, anchor_rows_inicio["buyer"], anchor_rows_inicio
            ),
            "config_metodologica": self._extract_all_config(config, anchor_rows_config),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_anchors(self, sheet, anchors: dict) -> dict[str, int]:
        """
        Scans col A for section title strings.
        Returns {key: row_number} for every anchor found.

        Unrecognised or missing anchors are simply absent from the result
        (no exception raised). Callers that require a specific anchor
        must check for its presence.
        """
        result: dict[str, int] = {}
        # Build a reverse map: exact string → key
        anchor_values = {v: k for k, v in anchors.items()}

        for row in sheet.iter_rows(min_col=1, max_col=1):
            cell = row[0]
            val = cell.value
            if val and isinstance(val, str):
                stripped = val.strip()
                if stripped in anchor_values:
                    result[anchor_values[stripped]] = cell.row

        return result

    def _scan_section(self, sheet, section_title: str) -> int:
        """
        Returns the row index of the anchor row whose col A value exactly
        matches `section_title`. Returns -1 if not found.

        This is the canonical low-level scan used internally and exposed
        for unit testing.
        """
        for row in range(1, sheet.max_row + 1):
            if sheet.cell(row=row, column=1).value == section_title:
                return row
        return -1

    def _extract_kv(
        self, sheet, section_row: int, all_anchors: dict[str, int]
    ) -> dict:
        """
        Extracts key-value pairs from the rows below a section title.

        Layout assumption (confirmed by phase0-report.md):
          section_row     → section title (bold, merged)
          section_row + 1 → column header ("Campo | Valor | Notas")
          section_row + 2 → first data row

        Stops when:
          - The current row is in known_anchor_rows (next section reached), OR
          - Both col A AND col B are None (true empty gap row).

        Returns {normalized_key: raw_value}.
        Empty cells return None as value (not empty string).
        """
        known_anchor_rows = set(all_anchors.values())
        result: dict = {}
        data_start = section_row + 2  # skip title + header row

        for r in range(data_start, sheet.max_row + 1):
            if r in known_anchor_rows:
                break  # hit next section anchor

            label_cell = sheet.cell(row=r, column=1)
            value_cell = sheet.cell(row=r, column=2)
            label = label_cell.value
            value = value_cell.value

            if label is None and value is None:
                continue  # skip blank rows within section

            if label is None:
                continue  # value-only row — no label to key on

            if isinstance(label, str):
                label = label.strip()
                # Skip the column header row if it appears inside the range
                if label in ("Campo", ""):
                    continue
                if label.lower().startswith("nota:") or label.lower().startswith("nota "):
                    continue
                key = self._normalize_key(label)
                result[key] = value  # None stays None — not coerced to ""

        return result

    def _extract_table(
        self, sheet, section_row: int, all_anchors: dict[str, int]
    ) -> list[dict]:
        """
        Extracts table rows below a section title.

        Layout (PRODUCTOS / SERVICIOS):
          section_row     → section title
          section_row + 1 → header row  (N°, Nombre, Tipo, Unidad, Precio)
          section_row + 2 → first data row

        Termination: stop when col B (product name) is None — col A always
        contains a row index integer even for empty product slots.

        Returns list of dicts keyed by the normalized column header.
        """
        known_anchor_rows = set(all_anchors.values())
        header_row_num = section_row + 1

        # Read headers from the header row
        headers: list[str] = []
        for cell in sheet[header_row_num]:
            if cell.value is not None:
                headers.append(str(cell.value).strip())
            else:
                break  # stop at first empty column header

        rows: list[dict] = []
        for r in range(section_row + 2, sheet.max_row + 1):
            if r in known_anchor_rows:
                break

            # Termination: col B (index 1) is None → no more products
            col_b_val = sheet.cell(row=r, column=2).value
            if col_b_val is None:
                break

            row_vals = [
                sheet.cell(row=r, column=c).value
                for c in range(1, len(headers) + 1)
            ]
            row_dict = dict(zip(headers, row_vals))
            rows.append(row_dict)

        return rows

    def _extract_all_config(
        self, sheet, anchor_rows: dict[str, int]
    ) -> dict:
        """
        Iterates over all 5 CONFIG subsection anchors and extracts each
        as a flat key-value dict. Returns {subsection_key: {label: value}}.
        """
        result: dict = {}
        for key, row in anchor_rows.items():
            section_data = self._extract_kv(sheet, row, anchor_rows)
            result[key] = section_data
        return result

    def _normalize_key(self, label: str) -> str:
        """
        Converts a Spanish label to a snake_case ASCII-friendly key.
        Example: 'Nombre del Proyecto' → 'nombre_del_proyecto'
        Preserves accented chars (á, é, etc.) for LangChain prompt readability.
        """
        key = label.lower().strip()
        # Remove characters that are neither word chars, accented letters, nor spaces
        key = re.sub(r"[^\w\sáéíóúüñ]", "", key)
        key = re.sub(r"\s+", "_", key)
        return key
