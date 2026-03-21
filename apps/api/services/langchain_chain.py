"""
Input1EnrichmentChain — uses LangChain to map and normalize raw Excel data.

One chain call per upload. Uses get_openai_callback() for token tracking.
Run name is "input1_enrichment" so LangSmith traces are identifiable.
"""

import os
import json

from langchain_openai import ChatOpenAI
from langchain_community.callbacks import get_openai_callback
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from models.schemas import PlanData


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Eres un asistente especializado en planes de negocio bolivianos.
Recibirás datos crudos extraídos de un Excel de planificación empresarial.
Tu tarea es mapear esos datos al schema PlanData y normalizar los valores.

Reglas:
- Si un campo requerido está vacío, usa el default de Bolivia
- Normaliza fechas al formato DD/MM/YYYY
- Normaliza porcentajes como float (25 → 25.0)
- Si el departamento falta pero hay ciudad, infiere el departamento boliviano correcto
- moneda solo puede ser "Bs" o "USD"
- horizonte_anios solo puede ser 3, 4 o 5; si no se especifica usa 5
- Si num_productos_servicios está vacío, cuenta los productos de la lista de productos
- No inventes valores para campos que no puedas inferir con seguridad: déjalos en null
- Para campos de texto libre (motivaciones, problema_que_resuelve), transcribe
  el valor original sin modificarlo
- El campo nombre_proyecto es REQUERIDO; si no aparece, usa "Sin nombre"
"""

USER_PROMPT = """Datos crudos extraídos del Excel (secciones del plan de negocio):

{raw_data}

Mapea estos datos al schema PlanData y devuelve un JSON válido.
{format_instructions}"""


# ---------------------------------------------------------------------------
# Chain
# ---------------------------------------------------------------------------


class Input1EnrichmentChain:
    """
    Wraps a LangChain pipeline: raw dict → PlanData + token metadata.

    Usage:
        chain = Input1EnrichmentChain()
        plan_data, token_info = chain.enrich(raw_dict)

    token_info keys: tokens_prompt, tokens_completion, costo_usd
    """

    def __init__(self):
        model_name = os.getenv("OPENAI_MODEL") or os.getenv("AI_MODEL", "gpt-4o-mini")
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0,
        )
        self.parser = PydanticOutputParser(pydantic_object=PlanData)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("human", USER_PROMPT),
            ]
        )
        # Chain: prompt → LLM → structured Pydantic output
        self.chain = self.prompt | self.llm | self.parser

    def enrich(self, raw_data: dict) -> tuple[PlanData, dict]:
        """
        Calls the LangChain chain with get_openai_callback() active.

        Args:
            raw_data: Dict produced by Input1Reader.read()

        Returns:
            (PlanData, token_info)
            token_info: {tokens_prompt, tokens_completion, costo_usd}
        """
        with get_openai_callback() as cb:
            result: PlanData = self.chain.invoke(
                {
                    "raw_data": json.dumps(
                        raw_data, ensure_ascii=False, default=str, indent=2
                    ),
                    "format_instructions": self.parser.get_format_instructions(),
                },
                config={"run_name": "input1_enrichment"},
            )

        token_info = {
            "tokens_prompt": cb.prompt_tokens,
            "tokens_completion": cb.completion_tokens,
            "costo_usd": cb.total_cost,
        }
        return result, token_info
