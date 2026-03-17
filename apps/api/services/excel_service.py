"""
Excel Service - Lee y genera archivos Excel usando IA (GPT-5nano/MiniMax).

Flujo:
1. Cliente sube Excel con datos
2. GPT-5nano lee y extrae datos (flexible ante variaciones)
3. Sistema valida campos obligatorios
4. Sistema guarda en BD (Plan, ParametrosGlobales, Producto)
5. Sistema completa con datos globales (defaults.yaml)
6. Sistema genera Excel plantilla maestra
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from database import get_database
from models.db import Plan, ParametrosGlobales, Producto, EstadoPlan
from services.config_service import get_config_service
from core.exceptions import ValidationError, ProcessingError, TemplateError, ErrorCodes


class ExcelService:
    """
    Servicio para procesar archivos Excel del plan de negocio.

    Usa GPT-5nano/MiniMax para lectura flexible de datos.
    Guarda en BD y genera plantilla maestra.
    """

    # Campos obligatorios en Parámetros Globales
    CAMPOS_OBLIGATORIOS_GLOBALES = ["nombre", "rubro", "ciudad", "departamento"]

    # Campos obligatorios en Productos
    CAMPOS_OBLIGATORIOS_PRODUCTOS = ["nombre", "unidad_medida", "peso_volumen"]

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa el servicio Excel.

        Args:
            api_key: API key para GPT-5nano/MiniMax (opcional, usa env var)
        """
        self.config = get_config_service()
        self.db = get_database()
        self.api_key = api_key

    async def leer_excel_cliente(self, file_path: Path) -> Dict[str, Any]:
        """
        Lee un Excel del cliente y extrae los datos usando IA.

        Args:
            file_path: Ruta al archivo Excel del cliente

        Returns:
            Dict con datos extraídos:
            {
                "parametros_globales": {...},
                "productos": [...]
            }

        Raises:
            ValidationError: Si faltan campos obligatorios
            ProcessingError: Si hay error al leer el archivo
        """
        # Paso 1: Leer Excel con openpyxl
        try:
            wb = load_workbook(file_path, data_only=True)
        except Exception as e:
            raise ProcessingError(
                message=f"Error al leer Excel: {str(e)}",
                file_name=str(file_path),
                operation="leer",
                code=ErrorCodes.EXCEL_READ_ERROR,
            )

        # Paso 2: Buscar las dos tablas
        # Asumimos que están en hojas separadas o en la misma hoja
        ws = wb.active

        # Extraer datos crudos del Excel
        datos_crudos = self._extraer_datos_crudos(ws)

        # Paso 3: Usar IA para estructurar los datos
        datos_estructurados = await self._estructurar_con_ia(datos_crudos)

        # Paso 4: Validar campos obligatorios
        self._validar_campos_obligatorios(datos_estructurados)

        return datos_estructurados

    def _extraer_datos_crudos(self, worksheet: Worksheet) -> Dict[str, Any]:
        """
        Extrae todos los datos del worksheet de forma cruda.

        Args:
            worksheet: Hoja de Excel

        Returns:
            Dict con datos crudos extraídos
        """
        datos = {"hoja": worksheet.title, "filas": []}

        # Leer todas las filas con datos
        for row in worksheet.iter_rows(values_only=True):
            # Filtrar filas vacías
            if any(cell is not None for cell in row):
                datos["filas"].append(list(row))

        return datos

    async def _estructurar_con_ia(self, datos_crudos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Usa GPT-5nano/MiniMax para estructurar los datos crudos.

        Args:
            datos_crudos: Datos extraídos del Excel

        Returns:
            Dict estructurado con parametros_globales y productos
        """
        # TODO: Implementar llamada a MiniMax API
        # Por ahora, parseamos manualmente asumiendo formato conocido

        # Buscar tabla de Parámetros Globales
        parametros = self._buscar_parametros_globales(datos_crudos["filas"])

        # Buscar tabla de Productos
        productos = self._buscar_productos(datos_crudos["filas"])

        return {"parametros_globales": parametros, "productos": productos}

    def _buscar_parametros_globales(self, filas: List[List]) -> Dict[str, Any]:
        """
        Busca y extrae parámetros globales del Excel.

        Asume formato:
        | Campo | Valor |
        |-------|-------|
        | Nombre | Shawarma Cruz |
        | Rubro | Restaurant |

        Args:
            filas: Lista de filas del Excel

        Returns:
            Dict con parámetros encontrados
        """
        parametros = {}

        for i, fila in enumerate(filas):
            # Buscar patrones: "Nombre", "Rubro", "Ciudad", "Departamento"
            if len(fila) >= 2:
                campo = str(fila[0]).strip().lower() if fila[0] else ""
                valor = fila[1] if len(fila) > 1 else None

                # Mapear campos conocidos
                if "nombre" in campo or "proyecto" in campo or "empresa" in campo:
                    parametros["nombre"] = valor
                elif "rubro" in campo or "sector" in campo:
                    parametros["rubro"] = valor
                elif "ciudad" in campo:
                    parametros["ciudad"] = valor
                elif "departamento" in campo or "depto" in campo:
                    parametros["departamento"] = valor

        return parametros

    def _buscar_productos(self, filas: List[List]) -> List[Dict[str, Any]]:
        """
        Busca y extrae productos del Excel.

        Asume formato de tabla:
        | N° | Nombre | Unidad | Peso |

        Args:
            filas: Lista de filas del Excel

        Returns:
            Lista de productos encontrados
        """
        productos = []
        en_tabla_productos = False

        for i, fila in enumerate(filas):
            # Detectar inicio de tabla de productos
            if len(fila) >= 2:
                primera_celda = str(fila[0]).strip().lower() if fila[0] else ""

                # Buscar encabezado "Producto" o "Productos/Servicios"
                if "producto" in primera_celda or "servicio" in primera_celda:
                    en_tabla_productos = True
                    continue

                # Si estamos en la tabla, extraer productos
                if en_tabla_productos and fila[0] is not None:
                    # Ignorar filas de encabezado
                    if str(fila[0]).strip().lower() in ["n°", "n", "numero", "#"]:
                        continue

                    producto = {
                        "numero": fila[0] if fila[0] else len(productos) + 1,
                        "nombre": fila[1] if len(fila) > 1 else "",
                        "unidad_medida": fila[2] if len(fila) > 2 else "Gramos",
                        "peso_volumen": fila[3] if len(fila) > 3 else 125.0,
                    }

                    # Validar que tiene nombre
                    if producto["nombre"]:
                        productos.append(producto)

        return productos

    def _validar_campos_obligatorios(self, datos: Dict[str, Any]) -> None:
        """
        Valida que todos los campos obligatorios estén presentes.

        Args:
            datos: Datos estructurados

        Raises:
            ValidationError: Si faltan campos obligatorios
        """
        errores = []

        # Validar parámetros globales
        params = datos.get("parametros_globales", {})
        for campo in self.CAMPOS_OBLIGATORIOS_GLOBALES:
            if campo not in params or params[campo] is None:
                errores.append(f"Parámetro faltante: {campo}")

        # Validar productos
        productos = datos.get("productos", [])
        if not productos:
            errores.append("No se encontraron productos")
        else:
            for i, prod in enumerate(productos):
                for campo in self.CAMPOS_OBLIGATORIOS_PRODUCTOS:
                    if campo not in prod or prod[campo] is None:
                        errores.append(f"Producto {i + 1}: campo '{campo}' faltante")

        if errores:
            raise ValidationError(
                message="Faltan campos obligatorios",
                field="validacion",
                code=ErrorCodes.MISSING_FIELD,
                details={"errores": errores},
            )

    async def guardar_en_bd(self, datos: Dict[str, Any]) -> Plan:
        """
        Guarda los datos en la base de datos.

        Args:
            datos: Datos estructurados del Excel

        Returns:
            Plan creado en la BD

        Raises:
            DatabaseError: Si hay error al guardar
        """
        with self.db.get_session() as session:
            # Crear Plan
            plan = Plan(
                nombre=datos["parametros_globales"]["nombre"],
                rubro=datos["parametros_globales"]["rubro"],
                ciudad=datos["parametros_globales"]["ciudad"],
                departamento=datos["parametros_globales"]["departamento"],
                estado=EstadoPlan.EN_PROCESO,
            )
            session.add(plan)
            session.commit()
            session.refresh(plan)

            # Crear Parámetros Globales (completados con defaults)
            config_data = self.config.get_all()
            parametros = ParametrosGlobales(
                plan_id=plan.id,
                pais=config_data.get("pais", {}).get("nombre", "Bolivia"),
                moneda_codigo=config_data.get("moneda", {}).get("codigo", "Bs"),
                tipo_cambio_usd=config_data.get("moneda", {}).get(
                    "tipo_cambio_usd", 6.96
                ),
                tasa_inflacion_anual=config_data.get("indicadores", {}).get(
                    "tasa_inflacion_anual", 2.0
                ),
                tasa_interes_promedio=config_data.get("indicadores", {}).get(
                    "tasa_interes_promedio", 8.5
                ),
                horizonte_anios=config_data.get("proyeccion", {}).get(
                    "horizonte_anios", 5
                ),
                anio_base=config_data.get("proyeccion", {}).get("anio_base", 2025),
                anio_inicio_operaciones=config_data.get("proyeccion", {}).get(
                    "anio_inicio_operaciones", 2026
                ),
                impuesto_iue=config_data.get("impuestos", {})
                .get("iue", {})
                .get("porcentaje", 25.0),
                impuesto_it=config_data.get("impuestos", {})
                .get("it", {})
                .get("porcentaje", 3.0),
            )
            session.add(parametros)

            # Crear Productos
            for i, prod_data in enumerate(datos.get("productos", [])):
                producto = Producto(
                    plan_id=plan.id,
                    numero=i + 1,
                    nombre=prod_data["nombre"],
                    unidad_medida=prod_data.get("unidad_medida", "Gramos"),
                    peso_volumen=prod_data.get("peso_volumen", 125.0),
                )
                session.add(producto)

            session.commit()

            return plan

    def generar_plantilla_maestra(
        self,
        plan: Plan,
        parametros: ParametrosGlobales,
        productos: List[Producto],
        output_path: Path,
    ) -> Path:
        """
        Genera la plantilla Excel maestra con todos los datos.

        Args:
            plan: Plan de negocio
            parametros: Parámetros globales
            productos: Lista de productos
            output_path: Ruta donde guardar el archivo

        Returns:
            Path al archivo generado

        Raises:
            TemplateError: Si hay error al generar la plantilla
        """
        # TODO: Implementar generación de Excel
        # Por ahora, crear un Excel básico
        wb = Workbook()
        ws = wb.active
        ws.title = "Parámetros Globales"

        # Escribir parámetros
        ws["A1"] = "Campo"
        ws["B1"] = "Valor"

        parametros_data = [
            ("Nombre del Proyecto", plan.nombre),
            ("Rubro", plan.rubro),
            ("Ciudad", plan.ciudad),
            ("Departamento", plan.departamento),
            ("País", parametros.pais),
            ("Moneda", parametros.moneda_codigo),
            ("Tipo de Cambio (USD)", parametros.tipo_cambio_usd),
            ("Tasa de Inflación Anual (%)", parametros.tasa_inflacion_anual),
            ("Horizonte de Proyección (años)", parametros.horizonte_anios),
            ("Año Base", parametros.anio_base),
            ("Año Inicio Operaciones", parametros.anio_inicio_operaciones),
            ("Impuesto IUE (%)", parametros.impuesto_iue),
            ("Impuesto IT (%)", parametros.impuesto_it),
        ]

        for i, (campo, valor) in enumerate(parametros_data, start=2):
            ws[f"A{i}"] = campo
            ws[f"B{i}"] = valor

        # Crear hoja de productos
        ws_productos = wb.create_sheet("Productos")
        ws_productos["A1"] = "N°"
        ws_productos["B1"] = "Nombre"
        ws_productos["C1"] = "Unidad de Medida"
        ws_productos["D1"] = "Peso/Volumen"

        for i, prod in enumerate(productos, start=2):
            ws_productos[f"A{i}"] = prod.numero
            ws_productos[f"B{i}"] = prod.nombre
            ws_productos[f"C{i}"] = prod.unidad_medida
            ws_productos[f"D{i}"] = prod.peso_volumen

        # Guardar archivo
        wb.save(output_path)

        return output_path
