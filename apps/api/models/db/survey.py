"""
Modelos SQLModel para encuestas de mercado.

Soporta múltiples encuestas (un survey por plan de negocio).
Estructura normalizada: Survey → SurveyResponse + SurveyVariable
"""

from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class Survey(SQLModel, table=True):
    """
    Encuesta de mercado.
    Una por plan de negocio, puede haber muchas encuestas distintas.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True)                    # "Encuesta Shawarma 2024"
    archivo_origen: str = Field()                       # path al .xlsx original
    total_respondentes: int = Field(default=0)
    fecha_carga: datetime = Field(default_factory=datetime.utcnow)

    # Relaciones
    responses: List["SurveyResponse"] = Relationship(back_populates="survey")
    variables: List["SurveyVariable"] = Relationship(back_populates="survey")


class SurveyResponse(SQLModel, table=True):
    """
    Una fila = una respuesta individual (respondente + pregunta + valor).

    Normalización: 320 respondentes × 16 preguntas = 5,120 filas por encuesta.
    Permite consultas tipo: SELECT valor_raw, COUNT(*) FROM surveyresponse
                            WHERE survey_id=1 AND pregunta_num=3
                            GROUP BY valor_raw
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    survey_id: int = Field(foreign_key="survey.id", index=True)
    respondente_num: int = Field()    # fila en el Excel (1-based)
    pregunta_num: int = Field()       # número de pregunta (1-16)
    valor_raw: str = Field()          # valor tal cual, ej: "a) 18 a 30 Años"

    # Relación
    survey: Optional[Survey] = Relationship(back_populates="responses")


class SurveyVariable(SQLModel, table=True):
    """
    Nombre de variable inferido por IA para cada pregunta de la encuesta.

    Permite cachear las inferencias IA y reutilizarlas.
    ej: pregunta_num=1, texto="¿Qué edad tiene?", nombre_variable="Edad"
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    survey_id: int = Field(foreign_key="survey.id", index=True)
    pregunta_num: int = Field()
    texto_pregunta: str = Field()     # texto completo de la pregunta
    nombre_variable: str = Field()    # ej: "Edad", "Género", "Frecuencia de Consumo"

    # Relación
    survey: Optional[Survey] = Relationship(back_populates="variables")
