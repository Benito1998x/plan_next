"""
Excel Service - Lee y genera archivos Excel con estructura fija.

Basado en plantilla_1.xlsx y plantilla_1_ejemplo_rellenado.xlsx

Flujo:
1. Cliente sube Excel (plantilla_1.xlsx llenado)
2. Sistema lee celdas específicas (B4:B16 para parámetros, B20:D29 para productos)
3. Sistema valida campos obligatorios (nombre, rubro, ciudad)
4. Sistema guarda en BD (Plan, ParametrosGlobales, Producto)
5. Sistema completa con datos globales (defaults.yaml)
6. Sistema genera Excel plantilla maestra
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from database import get_database
from models.db import Plan, ParametrosGlobales, Producto, EstadoPlan
from models.db.plan_data import DatosNegocio, BuyerPersona
from services.config_service import get_config_service
from core.exceptions import ValidationError, ProcessingError, TemplateError, ErrorCodes


class ExcelService:
    """
    Servicio para procesar archivos Excel del plan de negocio.

    Estructura fija de la plantilla:
    - Hoja: INICIO
    - Parámetros Globales: celdas B4:B16
    - Productos/Servicios: filas 20-29, columnas A-D
    """

    # ============================================
    # MAPEO DE CELDAS - ESTRUCTURA FIJA
    # ============================================

    # Parámetros Globales (columna B, filas 4-16)
    CELDAS_PARAMETROS = {
        "nombre": "B4",  # Nombre del Proyecto
        "rubro": "B5",  # Rubro / Sector
        "ciudad": "B6",  # Ciudad
        "departamento": "B7",  # Departamento
        "pais": "B8",  # País
        "moneda": "B9",  # Moneda
        "tipo_cambio": "B10",  # Tipo de Cambio (Bs/$us)
        "inflacion": "B11",  # Tasa de Inflación Anual
        "horizonte": "B12",  # Horizonte de Proyección (años)
        "anio_base": "B13",  # Año Base (Año 0)
        "anio_inicio": "B14",  # Año Inicio Operaciones
        "impuesto_iue": "B15",  # Impuesto IUE (%)
        "impuesto_it": "B16",  # Impuesto IT (%)
    }

    # Productos/Servicios (filas 20-29)
    FILAS_PRODUCTOS_INICIO = 20
    FILAS_PRODUCTOS_FIN = 29
    COLUMNAS_PRODUCTOS = {
        "numero": "A",  # N° (1-10, fijo)
        "nombre": "B",  # Nombre del Producto
        "unidad": "C",  # Unidad de Medida
        "peso": "D",  # Peso/Vol por Unidad
    }

    # Datos del Negocio (columna B, filas 32-35)
    CELDAS_DATOS_NEGOCIO = {
        "horario_atencion": "B32",   # Horario de Atención
        "zona_direccion":   "B33",   # Zona / Dirección
        "canal_venta":      "B34",   # Canal de Venta
        "capacidad_diaria": "B35",   # Capacidad Diaria (unidades)
    }

    # Buyer Persona (columna B, filas 38-44)
    CELDAS_BUYER_PERSONA = {
        "edad_objetivo":            "B38",  # Edad Objetivo (rango)
        "genero_objetivo":          "B39",  # Género Objetivo
        "ocupacion_principal":      "B40",  # Ocupación Principal
        "zona_residencia_objetivo": "B41",  # Zona de Residencia Objetivo
        "motivaciones_compra":      "B42",  # Motivaciones de Compra
        "canal_informacion":        "B43",  # Canal de Información Preferido
        "nivel_socioeconomico":     "B44",  # Nivel Socioeconómico (NSE)
    }

    # Campos obligatorios (mínimo para crear plan)
    CAMPOS_OBLIGATORIOS = ["nombre", "rubro", "ciudad"]

    # Nombre de la hoja de trabajo
    HOJA_TRABAJO = "INICIO"

    def __init__(self):
        """Inicializa el servicio Excel."""
        self.config = get_config_service()
        self.db = get_database()

    def leer_excel_cliente(self, file_path: Path) -> Dict[str, Any]:
        """
        Lee un Excel del cliente y extrae los datos de celdas específicas.

        Args:
            file_path: Ruta al archivo Excel del cliente

        Returns:
            Dict con datos extraídos:
            {
                "parametros_globales": {nombre, rubro, ciudad, ...},
                "productos": [{nombre, unidad, peso}, ...]
            }

        Raises:
            ValidationError: Si faltan campos obligatorios
            ProcessingError: Si hay error al leer el archivo
        """
        # Paso 1: Verificar que el archivo existe
        if not file_path.exists():
            raise ProcessingError(
                message=f"Archivo no encontrado: {file_path}",
                file_name=str(file_path),
                operation="leer",
                code=ErrorCodes.EXCEL_READ_ERROR,
            )

        # Paso 2: Cargar el archivo Excel
        try:
            wb = load_workbook(file_path, data_only=True)
        except Exception as e:
            raise ProcessingError(
                message=f"Error al abrir Excel: {str(e)}",
                file_name=str(file_path),
                operation="abrir",
                code=ErrorCodes.EXCEL_READ_ERROR,
            )

        # Paso 3: Obtener la hoja de trabajo
        if self.HOJA_TRABAJO not in wb.sheetnames:
            raise TemplateError(
                message=f"Hoja '{self.HOJA_TRABAJO}' no encontrada en el Excel",
                template_name=str(file_path),
                code=ErrorCodes.TEMPLATE_CORRUPTED,
            )

        ws = wb[self.HOJA_TRABAJO]

        # Paso 4: Extraer parámetros globales
        parametros = self._extraer_parametros(ws)

        # Paso 5: Extraer productos
        productos = self._extraer_productos(ws)

        # Paso 6: Extraer datos del negocio y buyer persona
        datos_negocio = self._extraer_seccion(ws, self.CELDAS_DATOS_NEGOCIO, ["capacidad_diaria"])
        buyer_persona = self._extraer_seccion(ws, self.CELDAS_BUYER_PERSONA, [])

        # Paso 7: Validar campos obligatorios
        self._validar_campos_obligatorios(parametros)

        # Paso 8: Cerrar el libro
        wb.close()

        return {
            "parametros_globales": parametros,
            "productos": productos,
            "datos_negocio": datos_negocio,
            "buyer_persona": buyer_persona,
        }

    def _extraer_parametros(self, ws: Worksheet) -> Dict[str, Any]:
        """
        Extrae parámetros globales de celdas específicas.

        Args:
            ws: Worksheet de openpyxl

        Returns:
            Dict con parámetros extraídos
        """
        parametros = {}

        for campo, celda in self.CELDAS_PARAMETROS.items():
            valor = ws[celda].value

            # Convertir a tipo apropiado
            if campo in ["tipo_cambio", "inflacion", "impuesto_iue", "impuesto_it"]:
                # Números decimales
                parametros[campo] = float(valor) if valor is not None else None
            elif campo in ["horizonte", "anio_base", "anio_inicio"]:
                # Enteros
                parametros[campo] = int(valor) if valor is not None else None
            else:
                # Texto
                parametros[campo] = str(valor).strip() if valor is not None else None

        return parametros

    def _extraer_productos(self, ws: Worksheet) -> List[Dict[str, Any]]:
        """
        Extrae productos de la hoja de trabajo (filas 20-29).

        Args:
            ws: Worksheet de openpyxl

        Returns:
            Lista de productos encontrados
        """
        productos = []

        for fila in range(self.FILAS_PRODUCTOS_INICIO, self.FILAS_PRODUCTOS_FIN + 1):
            nombre = ws[f"{self.COLUMNAS_PRODUCTOS['nombre']}{fila}"].value
            unidad = ws[f"{self.COLUMNAS_PRODUCTOS['unidad']}{fila}"].value
            peso = ws[f"{self.COLUMNAS_PRODUCTOS['peso']}{fila}"].value

            # Solo agregar si tiene nombre (producto válido)
            if nombre is not None and str(nombre).strip():
                producto = {
                    "numero": fila - self.FILAS_PRODUCTOS_INICIO + 1,
                    "nombre": str(nombre).strip(),
                    "unidad_medida": str(unidad).strip() if unidad else "Gramos",
                    "peso_volumen": float(peso) if peso else 125.0,
                }
                productos.append(producto)

        return productos

    def _extraer_seccion(
        self,
        ws: Worksheet,
        celdas: Dict[str, str],
        campos_entero: list,
    ) -> Dict[str, Any]:
        """
        Extrae datos de una sección de celdas arbitraria.

        Args:
            ws: Worksheet de openpyxl
            celdas: Mapeo {campo: celda} a leer
            campos_entero: Lista de campos a convertir a int

        Returns:
            Dict con los valores extraídos (solo los no-None)
        """
        datos = {}
        for campo, celda in celdas.items():
            valor = ws[celda].value
            if valor is None:
                datos[campo] = None
                continue
            if campo in campos_entero:
                try:
                    datos[campo] = int(valor)
                except (ValueError, TypeError):
                    datos[campo] = None
            else:
                datos[campo] = str(valor).strip() if valor is not None else None
        return datos

    def _validar_campos_obligatorios(self, parametros: Dict[str, Any]) -> None:
        """
        Valida que los campos obligatorios estén presentes.

        Args:
            parametros: Dict con parámetros extraídos

        Raises:
            ValidationError: Si faltan campos obligatorios
        """
        errores = []

        for campo in self.CAMPOS_OBLIGATORIOS:
            if campo not in parametros or parametros[campo] is None:
                errores.append(f"Campo obligatorio faltante: {campo}")

        if errores:
            raise ValidationError(
                message="Faltan campos obligatorios en el Excel",
                field="parametros_globales",
                code=ErrorCodes.MISSING_FIELD,
                details={"errores": errores},
            )

    async def guardar_en_bd(self, datos: Dict[str, Any]) -> Plan:
        """
        Guarda los datos en la base de datos.

        Completa los campos faltantes con defaults del config.

        Args:
            datos: Datos estructurados del Excel

        Returns:
            Plan creado en la BD

        Raises:
            DatabaseError: Si hay error al guardar
        """
        parametros = datos["parametros_globales"]
        productos = datos["productos"]
        datos_negocio_raw = datos.get("datos_negocio", {}) or {}
        buyer_persona_raw = datos.get("buyer_persona", {}) or {}

        with self.db.get_session() as session:
            # Crear Plan
            plan = Plan(
                nombre=parametros.get("nombre"),
                rubro=parametros.get("rubro"),
                ciudad=parametros.get("ciudad"),
                departamento=parametros.get("departamento", "Sin especificar"),
                estado=EstadoPlan.BORRADOR,
            )
            session.add(plan)
            session.commit()
            session.refresh(plan)

            # Obtener defaults del config
            config_data = self.config.get_all()

            # Crear Parámetros Globales (completados con defaults)
            parametros_bd = ParametrosGlobales(
                plan_id=plan.id,
                pais=parametros.get("pais")
                or config_data.get("pais", {}).get("nombre", "Bolivia"),
                moneda_codigo=parametros.get("moneda")
                or config_data.get("moneda", {}).get("codigo", "Bs"),
                tipo_cambio_usd=parametros.get("tipo_cambio")
                or config_data.get("moneda", {}).get("tipo_cambio_usd", 6.96),
                tasa_inflacion_anual=parametros.get("inflacion")
                or config_data.get("indicadores", {}).get("tasa_inflacion_anual", 0.02),
                tasa_interes_promedio=config_data.get("indicadores", {}).get(
                    "tasa_interes_promedio", 8.5
                ),
                horizonte_anios=parametros.get("horizonte")
                or config_data.get("proyeccion", {}).get("horizonte_anios", 5),
                anio_base=parametros.get("anio_base")
                or config_data.get("proyeccion", {}).get("anio_base", 2025),
                anio_inicio_operaciones=parametros.get("anio_inicio")
                or config_data.get("proyeccion", {}).get(
                    "anio_inicio_operaciones", 2026
                ),
                impuesto_iue=parametros.get("impuesto_iue")
                or config_data.get("impuestos", {})
                .get("iue", {})
                .get("porcentaje", 0.25),
                impuesto_it=parametros.get("impuesto_it")
                or config_data.get("impuestos", {})
                .get("it", {})
                .get("porcentaje", 0.03),
                formato_fecha=config_data.get("formato", {}).get("fecha", "%d/%m/%Y"),
                decimales_monetarios=config_data.get("formato", {}).get(
                    "decimales_monetarios", 2
                ),
            )
            session.add(parametros_bd)

            # Crear Productos
            for prod_data in productos:
                producto = Producto(
                    plan_id=plan.id,
                    numero=prod_data["numero"],
                    nombre=prod_data["nombre"],
                    unidad_medida=prod_data.get("unidad_medida", "Gramos"),
                    peso_volumen=prod_data.get("peso_volumen", 125.0),
                )
                session.add(producto)

            # Crear Datos del Negocio
            if any(v for v in datos_negocio_raw.values() if v is not None):
                datos_negocio_bd = DatosNegocio(
                    plan_id=plan.id,
                    horario_atencion=datos_negocio_raw.get("horario_atencion"),
                    zona_direccion=datos_negocio_raw.get("zona_direccion"),
                    canal_venta=datos_negocio_raw.get("canal_venta"),
                    capacidad_diaria=datos_negocio_raw.get("capacidad_diaria"),
                )
                session.add(datos_negocio_bd)

            # Crear Buyer Persona
            if any(v for v in buyer_persona_raw.values() if v is not None):
                buyer_persona_bd = BuyerPersona(
                    plan_id=plan.id,
                    edad_objetivo=buyer_persona_raw.get("edad_objetivo"),
                    genero_objetivo=buyer_persona_raw.get("genero_objetivo"),
                    ocupacion_principal=buyer_persona_raw.get("ocupacion_principal"),
                    zona_residencia_objetivo=buyer_persona_raw.get("zona_residencia_objetivo"),
                    motivaciones_compra=buyer_persona_raw.get("motivaciones_compra"),
                    canal_informacion=buyer_persona_raw.get("canal_informacion"),
                    nivel_socioeconomico=buyer_persona_raw.get("nivel_socioeconomico"),
                )
                session.add(buyer_persona_bd)

            session.commit()

            return plan

    def generar_plantilla_maestra(
        self,
        plan: Plan,
        parametros: ParametrosGlobales,
        productos: List[Producto],
        output_path: Path,
        datos_negocio=None,
        buyer_persona=None,
    ) -> Path:
        """
        Genera la plantilla Excel maestra con todos los datos.

        Usa la misma estructura que plantilla_1.xlsx

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
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = self.HOJA_TRABAJO

            # ============================================
            # ESCRIBIR PARÁMETROS GLOBALES
            # ============================================

            # Título
            ws["A1"] = "PLAN DE NEGOCIO"
            ws["A3"] = "PARÁMETROS GLOBALES"

            # Escribir etiquetas (columna A) y valores (columna B)
            parametros_data = [
                ("Nombre del Proyecto", plan.nombre, "B4"),
                ("Rubro / Sector", plan.rubro, "B5"),
                ("Ciudad", plan.ciudad, "B6"),
                ("Departamento", plan.departamento, "B7"),
                ("País", parametros.pais, "B8"),
                ("Moneda", parametros.moneda_codigo, "B9"),
                ("Tipo de Cambio (Bs/$us)", parametros.tipo_cambio_usd, "B10"),
                ("Tasa de Inflación Anual", parametros.tasa_inflacion_anual, "B11"),
                ("Horizonte de Proyección (años)", parametros.horizonte_anios, "B12"),
                ("Año Base (Año 0)", parametros.anio_base, "B13"),
                ("Año Inicio Operaciones", parametros.anio_inicio_operaciones, "B14"),
                ("Impuesto IUE (%)", parametros.impuesto_iue, "B15"),
                ("Impuesto IT (%)", parametros.impuesto_it, "B16"),
            ]

            for i, (etiqueta, valor, celda) in enumerate(parametros_data):
                # Etiqueta en columna A (filas 4-16)
                ws[f"A{4 + i}"] = etiqueta
                # Valor en columna B
                ws[celda] = valor

            # ============================================
            # ESCRIBIR PRODUCTOS / SERVICIOS
            # ============================================

            ws["A18"] = "PRODUCTOS / SERVICIOS"

            # Encabezados
            ws["A19"] = "N°"
            ws["B19"] = "Nombre del Producto"
            ws["C19"] = "Unidad de Medida"
            ws["D19"] = "Peso/Vol por Unidad"

            # Productos (filas 20-29)
            for i, prod in enumerate(productos):
                fila = 20 + i
                ws[f"A{fila}"] = prod.numero
                ws[f"B{fila}"] = prod.nombre
                ws[f"C{fila}"] = prod.unidad_medida
                ws[f"D{fila}"] = prod.peso_volumen

            # ============================================
            # ESCRIBIR DATOS DEL NEGOCIO (filas 31-35)
            # ============================================
            ws["A31"] = "DATOS DEL NEGOCIO"
            negocio_data = [
                ("Horario de Atención",        "B32", getattr(datos_negocio, "horario_atencion", None)),
                ("Zona / Dirección",            "B33", getattr(datos_negocio, "zona_direccion", None)),
                ("Canal de Venta",              "B34", getattr(datos_negocio, "canal_venta", None)),
                ("Capacidad Diaria (unidades)", "B35", getattr(datos_negocio, "capacidad_diaria", None)),
            ]
            for i, (etiqueta, celda, valor) in enumerate(negocio_data):
                ws[f"A{32 + i}"] = etiqueta
                ws[celda] = valor

            # ============================================
            # ESCRIBIR BUYER PERSONA (filas 37-44)
            # ============================================
            ws["A37"] = "BUYER PERSONA / SEGMENTACIÓN"
            persona_data = [
                ("Edad Objetivo (rango)",          "B38", getattr(buyer_persona, "edad_objetivo", None)),
                ("Género Objetivo",                 "B39", getattr(buyer_persona, "genero_objetivo", None)),
                ("Ocupación Principal",             "B40", getattr(buyer_persona, "ocupacion_principal", None)),
                ("Zona de Residencia Objetivo",    "B41", getattr(buyer_persona, "zona_residencia_objetivo", None)),
                ("Motivaciones de Compra",          "B42", getattr(buyer_persona, "motivaciones_compra", None)),
                ("Canal de Información Preferido", "B43", getattr(buyer_persona, "canal_informacion", None)),
                ("Nivel Socioeconómico (NSE)",     "B44", getattr(buyer_persona, "nivel_socioeconomico", None)),
            ]
            for i, (etiqueta, celda, valor) in enumerate(persona_data):
                ws[f"A{38 + i}"] = etiqueta
                ws[celda] = valor

            # Guardar archivo
            wb.save(output_path)

            return output_path

        except Exception as e:
            raise TemplateError(
                message=f"Error al generar plantilla maestra: {str(e)}",
                template_name=str(output_path),
                code=ErrorCodes.EXCEL_WRITE_ERROR,
            )
