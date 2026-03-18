"""
AI Agent - Interpreta datos parciales del cliente y devuelve datos estructurados.

Sprint 1: Extracción de datos + completado con defaults.

Providers:
- openai (dev): GPT-4o-mini
- minimax (prod): MiniMax 2.5
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv, find_dotenv

# Busca .env subiendo desde el directorio actual (cubre project root)
load_dotenv(find_dotenv(usecwd=True) or find_dotenv())

# Defaults bolivianos para el plan de negocio
DEFAULT_PARAMS = {
    "pais": "Bolivia",
    "moneda": "Bs",
    "tipo_cambio": 6.96,
    "inflacion": 0.02,
    "horizonte": 5,
    "anio_base": 2025,
    "anio_inicio": 2026,
    "impuesto_iue": 0.25,
    "impuesto_it": 0.03,
    "departamento": "Santa Cruz",
    "ciudad": "Santa Cruz de la Sierra",
}

# Schema de extracción para function calling
EXTRACT_SCHEMA = {
    "name": "extraer_datos_plan",
    "description": "Extrae y estructura los datos del cliente para el plan de negocio.",
    "parameters": {
        "type": "object",
        "properties": {
            "nombre": {
                "type": "string",
                "description": "Nombre del proyecto o emprendimiento",
            },
            "rubro": {
                "type": "string",
                "description": "Rubro o sector del negocio (ej: Gastronomía, Tecnología, Comercio)",
            },
            "ciudad": {
                "type": "string",
                "description": "Ciudad donde opera el negocio",
            },
            "departamento": {
                "type": "string",
                "description": "Departamento de Bolivia (ej: Santa Cruz, La Paz, Cochabamba)",
            },
            "productos": {
                "type": "array",
                "description": "Lista de productos o servicios del negocio",
                "items": {
                    "type": "object",
                    "properties": {
                        "nombre": {"type": "string", "description": "Nombre del producto o servicio"},
                        "unidad_medida": {
                            "type": "string",
                            "description": "Unidad de medida (ej: Unidad, Kg, Litro, Gramos, Porción)",
                        },
                        "peso_volumen": {
                            "type": "number",
                            "description": "Peso o volumen por unidad en la unidad indicada",
                        },
                    },
                    "required": ["nombre"],
                },
            },
        },
        "required": ["nombre", "rubro"],
    },
}

SYSTEM_PROMPT = """Eres un asistente especializado en planes de negocio para Bolivia.
Tu tarea es extraer y estructurar datos del cliente para completar una plantilla de plan de negocio.

Reglas:
- Infiere información razonable cuando no está explícita (ej: si dice "restaurante de comida árabe" → rubro="Gastronomía")
- Si el cliente da un número de productos pero no los detalla, crea nombres genéricos descriptivos
- Para unidad_medida usa: Unidad, Kg, Gramos, Litro, Porción, según el tipo de producto
- Siempre extrae al menos nombre y rubro. Ciudad y departamento son opcionales.
- Responde SOLO usando la función extraer_datos_plan."""

# Schema para inferir nombres de variables estadísticas desde preguntas de encuesta
VARIABLE_SCHEMA = {
    "name": "inferir_variables",
    "description": "Infiere nombres cortos de variables estadísticas desde textos de preguntas de encuesta.",
    "parameters": {
        "type": "object",
        "properties": {
            "variables": {
                "type": "array",
                "description": "Una entrada por pregunta, en el mismo orden recibido",
                "items": {
                    "type": "object",
                    "properties": {
                        "numero": {
                            "type": "integer",
                            "description": "Número de la pregunta"
                        },
                        "variable": {
                            "type": "string",
                            "description": "Nombre corto de la variable (1-3 palabras en español)"
                        }
                    },
                    "required": ["numero", "variable"]
                }
            }
        },
        "required": ["variables"]
    }
}

# ─── Schema para clasificación estadística dinámica de variables ──────────────
ANALYZE_VARIABLES_SCHEMA = {
    "name": "analizar_variables_encuesta",
    "description": (
        "Analiza preguntas de encuesta y determina el tipo estadístico de cada variable "
        "junto con los valores numéricos implícitos en sus opciones. "
        "El sistema es dinámico: no asume qué pregunta es frecuencia o precio."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "variables": {
                "type": "array",
                "description": "Un elemento por pregunta analizada",
                "items": {
                    "type": "object",
                    "properties": {
                        "numero": {
                            "type": "integer",
                            "description": "Número de la pregunta",
                        },
                        "variable": {
                            "type": "string",
                            "description": "Nombre corto de la variable (1-3 palabras)",
                        },
                        "tipo": {
                            "type": "string",
                            "enum": ["nominal", "ordinal", "ordinal_likert", "cuantitativa"],
                            "description": (
                                "nominal: categorías sin orden. "
                                "ordinal: categorías con orden natural. "
                                "ordinal_likert: escala de acuerdo/satisfacción. "
                                "cuantitativa: opciones con valor numérico extraíble (frecuencias temporales, precios, cantidades)."
                            ),
                        },
                        "conversiones": {
                            "type": "object",
                            "description": (
                                "SOLO para tipo cuantitativa u ordinal_likert: "
                                "mapeo {label_opción: valor_numérico}. "
                                "Para frecuencias: convertir a escala anual (Diario→365, Semanal→52, Mensual→12, etc). "
                                "Para precios/montos en intervalos: usar midpoint ((min+max)/2). "
                                "Para intervalos abiertos 'Menos de X': usar X*0.75. "
                                "Para 'Más de X': usar X*1.20. "
                                "Para Likert de N opciones: asignar N, N-1, ..., 1 en orden de positividad. "
                                "null si no aplica (nominal, ordinal)."
                            ),
                            "additionalProperties": {"type": "number"},
                            "nullable": True,
                        },
                        "unidad": {
                            "type": "string",
                            "description": (
                                "Unidad de medida del valor numérico. "
                                "Ejemplos: 'visitas/año', 'Bs.', 'unidades', 'score 1-5'. "
                                "null si no aplica."
                            ),
                            "nullable": True,
                        },
                        "interpretacion": {
                            "type": "string",
                            "description": (
                                "Frase de 1-2 oraciones sobre qué mide esta variable "
                                "y su importancia para un plan de negocio."
                            ),
                        },
                    },
                    "required": ["numero", "variable", "tipo", "interpretacion"],
                },
            }
        },
        "required": ["variables"],
    },
}

ANALYZE_VARIABLES_SYSTEM_PROMPT = """Eres un experto en Business Intelligence y Estadística aplicada a planes de negocio.

Tu tarea es analizar preguntas de una encuesta de mercado e identificar:
1. El tipo estadístico de cada variable (nominal, ordinal, ordinal_likert, cuantitativa)
2. Los valores numéricos implícitos en las opciones de respuesta (para variables cuantitativas)

Reglas críticas:
- Sé DINÁMICO: no asumas que una pregunta es de frecuencia o precio por su número.
  Lee el texto de la pregunta y sus opciones para determinarlo.
- Para FRECUENCIAS TEMPORALES ("Diariamente", "Semanal", etc.): convertir a escala ANUAL.
  Diario=365, 2-3/semana=130, 1/semana=52, 2/mes=24, 1/mes=12, Nunca=0.
- Para INTERVALOS DE PRECIO/MONTO: calcular el midpoint.
  "Bs. 21 a 35" → 28.0. "Menos de X" → X×0.75. "Más de X" → X×1.20.
- Para LIKERT: asignar scores descendentes empezando en N (más positivo) hasta 1 (más negativo).
- "Conocimiento del mercado", "Familiaridad con el producto" → ORDINAL (no cuantitativa).
- En caso de duda → clasificar como NOMINAL (opción conservadora).
- Responde SIEMPRE usando la función analizar_variables_encuesta."""

VARIABLE_SYSTEM_PROMPT = """Eres un experto en investigación de mercado y estadística descriptiva.
Dado el texto de preguntas de una encuesta, infiere el nombre corto de la variable estadística que representa cada pregunta.

Reglas:
- 1 a 3 palabras máximo
- Sustantivos o frases nominales en español
- Sin signos de interrogación ni artículos innecesarios
- Ejemplos: "¿Qué edad tiene?" → "Edad", "¿Cuál es su género?" → "Género",
  "¿Con qué frecuencia consume shawarma?" → "Frecuencia de Consumo",
  "¿Cuánto estaría dispuesto a pagar?" → "Disposición a Pagar"
- Responde SOLO usando la función inferir_variables."""


class AIAgent:
    """
    Agente IA que interpreta datos parciales del cliente.

    Dev → OpenAI (gpt-4o-mini)
    Prod → MiniMax 2.5
    """

    def __init__(self):
        # Compatibilidad con variables del .env del proyecto
        self.provider = (os.getenv("AI_PROVIDER") or os.getenv("LLM_PROVIDER", "openai")).lower()
        self.model = os.getenv("AI_MODEL") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def extract_plan_data(self, client_input: dict) -> dict:
        """
        Toma datos parciales del cliente y devuelve datos completos.

        Args:
            client_input: dict con cualquier combinación de:
                - nombre: str
                - rubro: str
                - ciudad: str
                - num_productos: int (si no se dan productos detallados)
                - productos: list[dict]
                - descripcion: str (texto libre)

        Returns:
            dict con parametros_globales + productos completos
        """
        if self.provider == "openai":
            return self._extract_openai(client_input)
        elif self.provider == "minimax":
            return self._extract_minimax(client_input)
        else:
            return self._extract_fallback(client_input)

    def _build_user_message(self, client_input: dict) -> str:
        parts = []

        if client_input.get("descripcion"):
            parts.append(f"Descripción del negocio: {client_input['descripcion']}")

        if client_input.get("nombre"):
            parts.append(f"Nombre: {client_input['nombre']}")

        if client_input.get("rubro"):
            parts.append(f"Rubro: {client_input['rubro']}")

        if client_input.get("ciudad"):
            parts.append(f"Ciudad: {client_input['ciudad']}")

        if client_input.get("productos"):
            parts.append(f"Productos: {json.dumps(client_input['productos'], ensure_ascii=False)}")
        elif client_input.get("num_productos"):
            parts.append(
                f"Número de productos/servicios: {client_input['num_productos']} "
                f"(crear nombres apropiados según el rubro)"
            )

        return "\n".join(parts) if parts else "Sin datos proporcionados"

    def _extract_openai(self, client_input: dict) -> dict:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            user_message = self._build_user_message(client_input)

            kwargs = dict(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                tools=[{"type": "function", "function": EXTRACT_SCHEMA}],
                tool_choice={"type": "function", "function": {"name": "extraer_datos_plan"}},
            )
            # gpt-5-nano y algunos modelos no soportan temperature
            try:
                response = client.chat.completions.create(**kwargs, temperature=0.2)
            except Exception:
                response = client.chat.completions.create(**kwargs)

            tool_call = response.choices[0].message.tool_calls[0]
            extracted = json.loads(tool_call.function.arguments)
            return self._merge_with_defaults(extracted, client_input)

        except Exception as e:
            return self._extract_fallback(client_input, error=str(e))

    def _extract_minimax(self, client_input: dict) -> dict:
        """MiniMax 2.5 via OpenAI-compatible API."""
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=os.getenv("MINIMAX_API_KEY"),
                base_url="https://api.minimax.chat/v1",
            )
            user_message = self._build_user_message(client_input)

            kwargs = dict(
                model=os.getenv("MINIMAX_MODEL", "MiniMax-Text-01"),
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                tools=[{"type": "function", "function": EXTRACT_SCHEMA}],
                tool_choice={"type": "function", "function": {"name": "extraer_datos_plan"}},
            )
            try:
                response = client.chat.completions.create(**kwargs, temperature=0.2)
            except Exception:
                response = client.chat.completions.create(**kwargs)

            tool_call = response.choices[0].message.tool_calls[0]
            extracted = json.loads(tool_call.function.arguments)
            return self._merge_with_defaults(extracted, client_input)

        except Exception as e:
            return self._extract_fallback(client_input, error=str(e))

    def _merge_with_defaults(self, extracted: dict, client_input: dict) -> dict:
        """
        Combina los datos extraídos por el agente con los defaults bolivianos.
        """
        params = {**DEFAULT_PARAMS}

        # Sobreescribir con lo que el cliente dio directamente (valores numéricos)
        for key in ["tipo_cambio", "inflacion", "horizonte", "anio_base", "anio_inicio",
                    "impuesto_iue", "impuesto_it"]:
            if client_input.get(key) is not None:
                params[key] = client_input[key]

        # Datos del agente (texto)
        params["nombre"] = extracted.get("nombre", client_input.get("nombre", "Sin nombre"))
        params["rubro"] = extracted.get("rubro", client_input.get("rubro", "Sin rubro"))
        params["ciudad"] = extracted.get("ciudad") or client_input.get("ciudad") or DEFAULT_PARAMS["ciudad"]
        params["departamento"] = extracted.get("departamento") or client_input.get("departamento") or DEFAULT_PARAMS["departamento"]

        # Moneda y país no se infieren del cliente (son defaults)
        params["pais"] = DEFAULT_PARAMS["pais"]
        params["moneda"] = DEFAULT_PARAMS["moneda"]

        # Productos del agente
        productos_raw = extracted.get("productos", [])
        productos = []
        for i, p in enumerate(productos_raw, start=1):
            productos.append({
                "numero": i,
                "nombre": p.get("nombre", f"Producto {i}"),
                "unidad_medida": p.get("unidad_medida", "Unidad"),
                "peso_volumen": float(p.get("peso_volumen") or 1.0),
            })

        # Si el agente no devolvió productos pero el cliente dio num_productos
        if not productos and client_input.get("num_productos"):
            rubro = params["rubro"]
            for i in range(1, int(client_input["num_productos"]) + 1):
                productos.append({
                    "numero": i,
                    "nombre": f"Producto {i} - {rubro}",
                    "unidad_medida": "Unidad",
                    "peso_volumen": 1.0,
                })

        return {"parametros_globales": params, "productos": productos}

    def _extract_fallback(self, client_input: dict, error: Optional[str] = None) -> dict:
        """
        Fallback sin IA: usa directamente los datos del cliente + defaults.
        Se activa cuando la API falla o no hay API key.
        """
        params = {**DEFAULT_PARAMS}
        params["nombre"] = client_input.get("nombre", "Sin nombre")
        params["rubro"] = client_input.get("rubro", "Sin rubro")
        params["ciudad"] = client_input.get("ciudad", DEFAULT_PARAMS["ciudad"])
        params["departamento"] = client_input.get("departamento", DEFAULT_PARAMS["departamento"])

        # Override numéricos del cliente
        for key in ["tipo_cambio", "inflacion", "horizonte", "anio_base", "anio_inicio",
                    "impuesto_iue", "impuesto_it"]:
            if client_input.get(key) is not None:
                params[key] = client_input[key]

        productos = []
        if client_input.get("productos"):
            for i, p in enumerate(client_input["productos"], start=1):
                productos.append({
                    "numero": i,
                    "nombre": p.get("nombre", f"Producto {i}"),
                    "unidad_medida": p.get("unidad_medida", "Unidad"),
                    "peso_volumen": float(p.get("peso_volumen") or 1.0),
                })
        elif client_input.get("num_productos"):
            for i in range(1, int(client_input["num_productos"]) + 1):
                productos.append({
                    "numero": i,
                    "nombre": f"Producto {i}",
                    "unidad_medida": "Unidad",
                    "peso_volumen": 1.0,
                })

        result = {"parametros_globales": params, "productos": productos}
        if error:
            result["_agent_error"] = error
        return result

    def analyze_survey_variables(
        self,
        questions: Dict[int, Dict[str, Any]],
    ) -> Dict[int, Dict[str, Any]]:
        """
        Analiza dinámicamente las variables de una encuesta.

        Determina el tipo estadístico de cada variable y extrae los valores
        numéricos implícitos en las opciones (sin mapeos hardcodeados).

        Args:
            questions: {
                q_num: {
                    "texto_pregunta": str,
                    "opciones": [str, ...]   # labels ya limpiados (sin prefijos a)/b))
                }
            }

        Returns:
            {
                q_num: {
                    "variable":      str,   # nombre corto
                    "tipo":          str,   # nominal/ordinal/ordinal_likert/cuantitativa
                    "conversiones":  dict | None,  # {label: float}
                    "unidad":        str | None,
                    "interpretacion": str,
                }
            }
        """
        if not questions:
            return {}

        if self.provider == "openai":
            result = self._analyze_variables_openai(questions)
        elif self.provider == "minimax":
            result = self._analyze_variables_minimax(questions)
        else:
            result = {}

        # Fallback: si el LLM falla o no retorna todas las preguntas
        for q_num in questions:
            if q_num not in result:
                result[q_num] = self._fallback_variable_analysis(
                    q_num, questions[q_num]
                )
        return result

    def _build_analyze_message(self, questions: Dict[int, Dict]) -> str:
        """Construye el mensaje para el análisis de variables."""
        lines = []
        for q_num in sorted(questions.keys()):
            q = questions[q_num]
            texto = q.get("texto_pregunta", f"Pregunta {q_num}")
            opciones = q.get("opciones", [])
            opciones_str = " | ".join(opciones) if opciones else "(sin opciones)"
            lines.append(f"Pregunta {q_num}: {texto}\nOpciones: {opciones_str}")
        return "\n\n".join(lines)

    def _parse_analyze_response(self, tool_call) -> Dict[int, Dict]:
        """Parsea la respuesta de analizar_variables_encuesta."""
        variables_list = json.loads(tool_call.function.arguments).get("variables", [])
        result = {}
        for item in variables_list:
            q_num = item["numero"]
            result[q_num] = {
                "variable":      item.get("variable", f"Variable {q_num}"),
                "tipo":          item.get("tipo", "nominal"),
                "conversiones":  item.get("conversiones"),
                "unidad":        item.get("unidad"),
                "interpretacion": item.get("interpretacion", ""),
            }
        return result

    def _analyze_variables_openai(self, questions: Dict[int, Dict]) -> Dict[int, Dict]:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            kwargs = dict(
                model=self.model,
                messages=[
                    {"role": "system", "content": ANALYZE_VARIABLES_SYSTEM_PROMPT},
                    {"role": "user", "content": self._build_analyze_message(questions)},
                ],
                tools=[{"type": "function", "function": ANALYZE_VARIABLES_SCHEMA}],
                tool_choice={"type": "function", "function": {"name": "analizar_variables_encuesta"}},
            )
            try:
                response = client.chat.completions.create(**kwargs, temperature=0.1)
            except Exception:
                response = client.chat.completions.create(**kwargs)
            return self._parse_analyze_response(response.choices[0].message.tool_calls[0])
        except Exception:
            return {}

    def _analyze_variables_minimax(self, questions: Dict[int, Dict]) -> Dict[int, Dict]:
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=os.getenv("MINIMAX_API_KEY"),
                base_url="https://api.minimax.chat/v1",
            )
            kwargs = dict(
                model=os.getenv("MINIMAX_MODEL", "MiniMax-Text-01"),
                messages=[
                    {"role": "system", "content": ANALYZE_VARIABLES_SYSTEM_PROMPT},
                    {"role": "user", "content": self._build_analyze_message(questions)},
                ],
                tools=[{"type": "function", "function": ANALYZE_VARIABLES_SCHEMA}],
                tool_choice={"type": "function", "function": {"name": "analizar_variables_encuesta"}},
            )
            try:
                response = client.chat.completions.create(**kwargs, temperature=0.1)
            except Exception:
                response = client.chat.completions.create(**kwargs)
            return self._parse_analyze_response(response.choices[0].message.tool_calls[0])
        except Exception:
            return {}

    def _fallback_variable_analysis(
        self, q_num: int, q_data: Dict
    ) -> Dict[str, Any]:
        """
        Fallback sin IA: heurísticas simples basadas en texto de opciones.

        Detecta patrones comunes sin depender del LLM.
        """
        import re
        texto = q_data.get("texto_pregunta", "").lower()
        opciones = q_data.get("opciones", [])

        # Detectar frecuencias temporales
        freq_keywords = ["diario", "semanal", "mensual", "diariamente", "semana", "mes", "vez al"]
        if any(k in " ".join(opciones).lower() for k in freq_keywords):
            conversiones = self._extract_frequency_conversions(opciones)
            return {
                "variable": "Frecuencia",
                "tipo": "cuantitativa",
                "conversiones": conversiones,
                "unidad": "visitas/año",
                "interpretacion": "Intensidad de consumo anualizada.",
            }

        # Detectar precios/montos (busca patrones como "Bs." o "$" + números)
        price_pattern = re.compile(r"(?:bs\.?|\\$|usd)?\s*\d+", re.IGNORECASE)
        if sum(1 for o in opciones if price_pattern.search(o)) >= len(opciones) // 2:
            conversiones = self._extract_midpoint_conversions(opciones)
            moneda = "Bs." if any("bs" in o.lower() for o in opciones) else "unidades"
            return {
                "variable": "Precio" if "pag" in texto or "precio" in texto else "Monto",
                "tipo": "cuantitativa",
                "conversiones": conversiones,
                "unidad": moneda,
                "interpretacion": "Variable monetaria cuantificada por midpoints de intervalos.",
            }

        # Detectar Likert (opciones como excelente/muy bueno/bueno o satisfecho/...)
        likert_keywords = ["excelente", "muy bueno", "satisfecho", "acuerdo", "probable"]
        if any(k in " ".join(opciones).lower() for k in likert_keywords):
            conversiones = {o: len(opciones) - i for i, o in enumerate(opciones)}
            return {
                "variable": "Aceptación" if "acept" in texto else "Satisfacción",
                "tipo": "ordinal_likert",
                "conversiones": conversiones,
                "unidad": f"score 1-{len(opciones)}",
                "interpretacion": "Escala Likert de actitud.",
            }

        # Default: nominal
        return {
            "variable": f"Variable {q_num}",
            "tipo": "nominal",
            "conversiones": None,
            "unidad": None,
            "interpretacion": "Variable categórica nominal.",
        }

    def _extract_frequency_conversions(self, opciones: List[str]) -> Dict[str, float]:
        """Extrae conversiones anuales desde opciones de frecuencia textual."""
        import re
        mapping = {}
        annual_map = [
            (r"diari|todos los d[ií]as", 365),
            (r"2\s*[a-z]*\s*3|dos\s+o\s+tres|2-3", 130),
            (r"una?\s+vez\s+a\s+la\s+semana|semanal(?!mente)|1\s*vez\s*/?\s*semana", 52),
            (r"quincen|cada\s+15|dos\s+veces\s+al\s+mes|2\s*veces\s*al\s*mes", 24),
            (r"una?\s+vez\s+al\s+mes|mensual|1\s*vez\s*/?\s*mes", 12),
            (r"bimestral|cada\s+2\s+meses", 6),
            (r"trimestral|cada\s+3\s+meses", 4),
            (r"semestral|cada\s+6\s+meses", 2),
            (r"anual|una?\s+vez\s+al\s+a[ñn]o", 1),
            (r"nunca|no\s+consumo|no\s+aplica", 0),
        ]
        for opcion in opciones:
            matched = False
            for pattern, value in annual_map:
                if re.search(pattern, opcion.lower()):
                    mapping[opcion] = float(value)
                    matched = True
                    break
            if not matched:
                mapping[opcion] = 0.0
        return mapping

    def _extract_midpoint_conversions(self, opciones: List[str]) -> Dict[str, float]:
        """Extrae midpoints de intervalos numéricos en las opciones."""
        import re
        mapping = {}
        for opcion in opciones:
            # Intervalo cerrado: "21 a 35", "21-35", "21 - 35"
            m = re.search(r"(\d+(?:\.\d+)?)\s*(?:a|al?|-)\s*(\d+(?:\.\d+)?)", opcion)
            if m:
                lo, hi = float(m.group(1)), float(m.group(2))
                mapping[opcion] = (lo + hi) / 2
                continue
            # Abierto inferior: "Menos de X", "< X"
            m = re.search(r"(?:menos\s+de|<)\s*(\d+(?:\.\d+)?)", opcion, re.IGNORECASE)
            if m:
                x = float(m.group(1))
                mapping[opcion] = round(x * 0.75, 2)
                continue
            # Abierto superior: "Más de X", "> X"
            m = re.search(r"(?:m[aá]s\s+de|>)\s*(\d+(?:\.\d+)?)", opcion, re.IGNORECASE)
            if m:
                x = float(m.group(1))
                mapping[opcion] = round(x * 1.20, 2)
                continue
            # Número solo
            m = re.search(r"(\d+(?:\.\d+)?)", opcion)
            if m:
                mapping[opcion] = float(m.group(1))
                continue
            mapping[opcion] = 0.0
        return mapping

    def infer_variable_names(self, question_texts: Dict[int, str]) -> Dict[int, str]:
        """
        Infiere nombres cortos de variables estadísticas desde textos de preguntas.

        Args:
            question_texts: {1: "¿Qué edad tiene?", 2: "¿Cuál es su género?", ...}

        Returns:
            {1: "Edad", 2: "Género", ...}
        """
        if not question_texts:
            return {}
        if self.provider == "openai":
            return self._infer_variables_openai(question_texts)
        elif self.provider == "minimax":
            return self._infer_variables_minimax(question_texts)
        return self._infer_variables_fallback(question_texts)

    def _build_variable_message(self, question_texts: Dict[int, str]) -> str:
        lines = [f"Pregunta {num}: {text}" for num, text in sorted(question_texts.items())]
        return "\n".join(lines)

    def _parse_variable_response(self, tool_call) -> Dict[int, str]:
        variables_list = json.loads(tool_call.function.arguments).get("variables", [])
        return {item["numero"]: item["variable"] for item in variables_list}

    def _infer_variables_openai(self, question_texts: Dict[int, str]) -> Dict[int, str]:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            kwargs = dict(
                model=self.model,
                messages=[
                    {"role": "system", "content": VARIABLE_SYSTEM_PROMPT},
                    {"role": "user", "content": self._build_variable_message(question_texts)},
                ],
                tools=[{"type": "function", "function": VARIABLE_SCHEMA}],
                tool_choice={"type": "function", "function": {"name": "inferir_variables"}},
            )
            try:
                response = client.chat.completions.create(**kwargs, temperature=0.1)
            except Exception:
                response = client.chat.completions.create(**kwargs)
            return self._parse_variable_response(response.choices[0].message.tool_calls[0])
        except Exception:
            return self._infer_variables_fallback(question_texts)

    def _infer_variables_minimax(self, question_texts: Dict[int, str]) -> Dict[int, str]:
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=os.getenv("MINIMAX_API_KEY"),
                base_url="https://api.minimax.chat/v1",
            )
            kwargs = dict(
                model=os.getenv("MINIMAX_MODEL", "MiniMax-Text-01"),
                messages=[
                    {"role": "system", "content": VARIABLE_SYSTEM_PROMPT},
                    {"role": "user", "content": self._build_variable_message(question_texts)},
                ],
                tools=[{"type": "function", "function": VARIABLE_SCHEMA}],
                tool_choice={"type": "function", "function": {"name": "inferir_variables"}},
            )
            try:
                response = client.chat.completions.create(**kwargs, temperature=0.1)
            except Exception:
                response = client.chat.completions.create(**kwargs)
            return self._parse_variable_response(response.choices[0].message.tool_calls[0])
        except Exception:
            return self._infer_variables_fallback(question_texts)

    def _infer_variables_fallback(self, question_texts: Dict[int, str]) -> Dict[int, str]:
        """Fallback sin IA: extrae palabras clave de la pregunta."""
        import re
        stopwords = {
            "qué", "cuál", "cuánto", "cuántos", "cuántas", "es", "su", "de",
            "la", "el", "en", "con", "por", "tiene", "son", "ha", "una", "un",
            "los", "las", "del", "al", "se", "que", "no", "si", "más",
        }
        result = {}
        for num, text in question_texts.items():
            clean = re.sub(r'[¿?¡!,.]', '', text).strip()
            words = [w for w in clean.split() if w.lower() not in stopwords and len(w) > 2]
            variable = " ".join(words[:2]).title() if words else f"Variable {num}"
            result[num] = variable
        return result


def get_ai_agent() -> AIAgent:
    return AIAgent()
