"""
CAPA INDICADORES (Sprint 3) — KPIs de mercado desde datos Gold

Responsabilidades:
- Derivar indicadores cuantitativos de mercado desde la capa Gold
- Mapear cada pregunta de la encuesta a un indicador de negocio
- Retornar un dict estructurado listo para generar Excel y Word

Indicadores calculados (basados en encuesta de 16 preguntas):
  Q1  → Segmento Etario Principal
  Q2  → Género Dominante
  Q3  → Ocupación Top
  Q4  → Zona de Mayor Concentración
  Q7  → Tasa de Aceptación del Producto
  Q8  → Frecuencia de Consumo Modal
  Q9  → Momento de Consumo Preferido
  Q10 → Disposición a Pagar (precio top)
  Q11 → Gasto Promedio Actual
  Q13 → Satisfacción del Mercado Actual
  Q14 → Atributo Más Valorado
  Q15 → Canal de Venta Preferido
  Q16 → Medio de Comunicación Principal
"""

from typing import Dict, Any, Optional, List


# Mapeo de número de pregunta → nombre del indicador
_Q_INDICADOR = {
    1:  "Segmento Etario Principal",
    2:  "Género Dominante",
    3:  "Ocupación Principal del Target",
    4:  "Zona de Mayor Concentración",
    7:  "Tasa de Aceptación del Producto",
    8:  "Frecuencia de Consumo Modal",
    9:  "Momento de Consumo Preferido",
    10: "Disposición a Pagar (rango top)",
    11: "Gasto Promedio Actual",
    13: "Satisfacción con la Oferta Actual",
    14: "Atributo Más Valorado por el Cliente",
    15: "Canal de Adquisición Preferido",
    16: "Medio de Comunicación Principal",
}

# Preguntas donde la "tasa de aceptación" se calcula sumando las dos
# primeras opciones favorables (ej: "Muy probable" + "Probable")
_Q_ACEPTACION = {7}


def build_indicators(gold: Dict[int, Dict]) -> List[Dict[str, Any]]:
    """
    Deriva indicadores de mercado desde el layer Gold.

    Args:
        gold: salida de gold.build_gold()
              {q_num: {"variable": str, "options": [...], "total": int}}

    Returns:
        Lista de indicadores ordenados:
        [
            {
                "indicador"  : "Tasa de Aceptación del Producto",
                "valor"      : "78.5%",
                "detalle"    : "250 de 320 encuestados",
                "pregunta"   : 7,
                "variable"   : "Aceptación",
                "calculo"    : "Suma de opciones 1 y 2 (Muy probable + Probable)",
            },
            ...
        ]
    """
    indicadores: List[Dict[str, Any]] = []

    for q_num, nombre_indicador in _Q_INDICADOR.items():
        if q_num not in gold:
            continue

        q_data  = gold[q_num]
        variable = q_data["variable"]
        options  = q_data["options"]   # [{"label", "freq", "pct"}, ...]
        total    = q_data["total"]

        if not options:
            continue

        if q_num in _Q_ACEPTACION:
            # Tasa de aceptación = suma de las dos primeras opciones favorables
            top2_freq = sum(o["freq"] for o in options[:2])
            top2_pct  = (top2_freq / total * 100) if total > 0 else 0.0
            top_label = " + ".join(o["label"] for o in options[:2])
            indicadores.append({
                "indicador": nombre_indicador,
                "valor":     f"{top2_pct:.1f}%",
                "detalle":   f"{top2_freq} de {total} encuestados",
                "pregunta":  q_num,
                "variable":  variable,
                "calculo":   f"Suma de opciones positivas: {top_label}",
            })
        else:
            # Top 1: opción con mayor frecuencia
            top = max(options, key=lambda o: o["freq"])
            pct  = top["pct"] * 100
            indicadores.append({
                "indicador": nombre_indicador,
                "valor":     top["label"],
                "detalle":   f"{top['freq']} de {total} ({pct:.1f}%)",
                "pregunta":  q_num,
                "variable":  variable,
                "calculo":   "Moda (opción más frecuente)",
            })

    return indicadores


def build_indicators_summary(indicadores: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Construye un resumen ejecutivo de los indicadores.

    Útil para el encabezado del reporte Word/Excel.

    Returns:
        {
            "total_indicadores": 13,
            "tasa_aceptacion": "78.5%",   # de Q7 si existe
            "segmento_principal": "18 a 30 Años",
            "canal_preferido": "Delivery",
            "precio_aceptable": "Bs 21 a 30",
        }
    """
    summary: Dict[str, Any] = {"total_indicadores": len(indicadores)}

    for ind in indicadores:
        q = ind["pregunta"]
        if q == 7:
            summary["tasa_aceptacion"] = ind["valor"]
        elif q == 1:
            summary["segmento_etario_principal"] = ind["valor"]
        elif q == 15:
            summary["canal_preferido"] = ind["valor"]
        elif q == 10:
            summary["precio_aceptable"] = ind["valor"]
        elif q == 16:
            summary["medio_comunicacion"] = ind["valor"]

    return summary
