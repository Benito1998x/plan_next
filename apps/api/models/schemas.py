"""
Pydantic Schemas for BPAE API.

Define modelos para requests y responses.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================
# PLAN DATA SCHEMAS (Input 1 pipeline — Sprint 1)
# ============================================================


class ProductoData(BaseModel):
    numero: int
    nombre: str
    tipo: Optional[str] = None          # "Producto" or "Servicio"
    unidad_medida: Optional[str] = None
    precio_bs: Optional[float] = None


class ParametrosData(BaseModel):
    nombre_proyecto: str
    rubro_sector: Optional[str] = None
    ciudad: Optional[str] = None
    departamento: Optional[str] = None
    pais: str = "Bolivia"
    moneda: str = "Bs"
    tipo_cambio: Optional[float] = None
    fecha_elaboracion: Optional[str] = None
    horizonte_anios: Optional[int] = None
    nombre_responsable: Optional[str] = None
    anio_base: Optional[int] = None
    anio_inicio_operaciones: Optional[int] = None
    num_productos_servicios: Optional[int] = None


class DatosNegocioData(BaseModel):
    horario_atencion: Optional[str] = None
    dias_laborales_semana: Optional[int] = None
    semanas_laborales_anio: Optional[int] = 50
    horas_laborales_dia: Optional[int] = 8
    zona_direccion: Optional[str] = None
    canal_venta: Optional[str] = None
    capacidad_diaria_unidades: Optional[int] = None
    num_socios_fundadores: Optional[int] = None


class BuyerPersonaData(BaseModel):
    edad_objetivo: Optional[str] = None
    genero_objetivo: Optional[str] = None
    ocupacion_principal: Optional[str] = None
    zona_residencia_objetivo: Optional[str] = None
    motivaciones_compra: Optional[str] = None
    canal_informacion_preferido: Optional[str] = None
    nivel_socioeconomico: Optional[str] = None
    problema_que_resuelve: Optional[str] = None


class ConfigMetodologicaData(BaseModel):
    precision_muestra: Optional[str] = None
    tipo_mercado: Optional[str] = None
    metodo_proyeccion_ventas: Optional[str] = None
    evolucion_precios: Optional[str] = None
    metodo_depreciacion: Optional[str] = None
    meses_capital_trabajo: Optional[int] = 2
    necesita_financiamiento: Optional[str] = None
    forma_pago: Optional[str] = None
    frecuencia_pago: Optional[str] = None


class PlanData(BaseModel):
    parametros: ParametrosData
    productos: List[ProductoData] = []
    datos_negocio: DatosNegocioData = DatosNegocioData()
    buyer_persona: BuyerPersonaData = BuyerPersonaData()
    config_metodologica: ConfigMetodologicaData = ConfigMetodologicaData()


# ============================================================
# REQUEST SCHEMAS
# ============================================================


class UploadExcelRequest(BaseModel):
    """Request para subir archivo Excel."""

    filename: str = Field(..., description="Nombre del archivo")
    version: str = Field(default="v1", description="Versión de plantilla")


class ParametrosGlobalesInput(BaseModel):
    """Input para parámetros globales."""

    nombre: Optional[str] = Field(None, description="Nombre del proyecto")
    rubro: Optional[str] = Field(None, description="Rubro o sector")
    ciudad: Optional[str] = Field(None, description="Ciudad")
    departamento: Optional[str] = Field(None, description="Departamento")
    pais: Optional[str] = Field(default="Bolivia", description="País")
    moneda: Optional[str] = Field(default="Bs", description="Moneda")
    tipo_cambio: Optional[float] = Field(default=6.96, description="Tipo de cambio")
    inflacion: Optional[float] = Field(default=0.02, description="Tasa de inflación")
    horizonte: Optional[int] = Field(default=5, description="Horizonte en años")
    anio_base: Optional[int] = Field(default=2025, description="Año base")
    anio_inicio: Optional[int] = Field(default=2026, description="Año inicio")
    impuesto_iue: Optional[float] = Field(default=0.25, description="Impuesto IUE")
    impuesto_it: Optional[float] = Field(default=0.03, description="Impuesto IT")


class ProductoInput(BaseModel):
    """Input para un producto/servicio."""

    numero: Optional[int] = Field(None, description="Número de producto")
    nombre: str = Field(..., description="Nombre del producto")
    unidad_medida: Optional[str] = Field(
        default="Gramos", description="Unidad de medida"
    )
    peso_volumen: Optional[float] = Field(default=125.0, description="Peso o volumen")


class PlanCreateRequest(BaseModel):
    """Request para crear un plan desde datos extraídos."""

    parametros_globales: ParametrosGlobalesInput = Field(
        ..., description="Parámetros globales"
    )
    productos: List[ProductoInput] = Field(
        default_factory=list, description="Lista de productos"
    )


# ============================================================
# RESPONSE SCHEMAS
# ============================================================


class APIResponse(BaseModel):
    """Response estándar de la API."""

    data: Optional[Any] = Field(None, description="Datos de respuesta")
    error: Optional[str] = Field(None, description="Código de error si aplica")
    message: Optional[str] = Field(None, description="Mensaje descriptivo")


class ParametrosGlobalesOutput(BaseModel):
    """Output para parámetros globales."""

    nombre: str
    rubro: str
    ciudad: str
    departamento: Optional[str] = None
    pais: str
    moneda: str
    tipo_cambio: float
    inflacion: float
    horizonte: int
    anio_base: int
    anio_inicio: int
    impuesto_iue: float
    impuesto_it: float


class ProductoOutput(BaseModel):
    """Output para un producto."""

    numero: int
    nombre: str
    unidad_medida: str
    peso_volumen: float


class PlanOutput(BaseModel):
    """Output para un plan completo."""

    id: int
    nombre: str
    rubro: str
    ciudad: str
    estado: str
    parametros: Optional[ParametrosGlobalesOutput] = None
    productos: List[ProductoOutput] = []
    created_at: datetime
    updated_at: Optional[datetime] = None


class UploadExcelResponse(BaseModel):
    """Response para upload de Excel."""

    plan_id: int = Field(..., description="ID del plan creado")
    nombre: str = Field(..., description="Nombre del proyecto")
    parametros: ParametrosGlobalesOutput = Field(
        ..., description="Parámetros extraídos"
    )
    productos: List[ProductoOutput] = Field(..., description="Productos extraídos")
    campos_faltantes: List[str] = Field(
        default_factory=list, description="Campos que faltan"
    )
    advertencias: List[str] = Field(default_factory=list, description="Advertencias")


class GenerateWordResponse(BaseModel):
    """Response para generación de Word."""

    plan_id: int = Field(..., description="ID del plan")
    word_url: str = Field(..., description="URL para descargar el Word")
    excel_url: str = Field(..., description="URL para descargar el Excel")
    generated_at: datetime = Field(..., description="Fecha de generación")


# ============================================================
# VALIDATION SCHEMAS
# ============================================================


class ValidationError(BaseModel):
    """Error de validación."""

    field: str = Field(..., description="Campo con error")
    message: str = Field(..., description="Mensaje de error")
    value: Optional[Any] = Field(None, description="Valor que causó el error")


class ValidationResult(BaseModel):
    """Resultado de validación."""

    is_valid: bool = Field(..., description="Si la validación pasó")
    errors: List[ValidationError] = Field(
        default_factory=list, description="Lista de errores"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Lista de advertencias"
    )


# ============================================================
# INTERNAL SCHEMAS
# ============================================================


class ExtractedData(BaseModel):
    """Datos extraídos del Excel."""

    parametros_globales: Dict[str, Any] = Field(default_factory=dict)
    productos: List[Dict[str, Any]] = Field(default_factory=list)
    sections_found: List[str] = Field(
        default_factory=list, description="Secciones detectadas"
    )
    detection_info: Dict[str, Any] = Field(
        default_factory=dict, description="Info de detección"
    )
