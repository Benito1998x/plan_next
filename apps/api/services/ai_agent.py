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
from typing import Optional
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


def get_ai_agent() -> AIAgent:
    return AIAgent()
