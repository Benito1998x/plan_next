"""
Indicadores de Mercado v2 — Pipeline Estadístico Completo (Sprint 3)

Reemplaza indicators.py (que solo calculaba la moda) con un análisis
estadístico completo y dinámico:

  - Nominal / Ordinal       → distribución completa de probabilidades
  - Ordinal Likert          → distribución + score ponderado + TOP/BOTTOM-2 Box
  - Cuantitativa Convertible → μ, σ, IC-95%, P(X ≤ x), P(X ≥ x)

El pipeline acepta:
  1. Gold data (de toda la encuesta)
  2. Clasificación de variables (del AIAgent via variable_classifier)
  3. Opcionalmente: filtros de segmento (buyer persona)

Retorna la estructura completa lista para generar Excel y Word.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

from services.pipeline.quantitative_transform import (
    compute_weighted_stats,
    compute_likert_stats,
    build_probability_points,
    cumulative_probability,
    survival_probability,
)

logger = logging.getLogger(__name__)


def build_indicators_v2(
    gold: Dict[int, Dict],
    classification: Dict[int, Dict[str, Any]],
    n_total: int,
    n_segmento: Optional[int] = None,
    filtros_aplicados: Optional[Dict] = None,
    advertencias: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Genera indicadores estadísticos completos para todas las variables del Gold.

    Args:
        gold            : salida de build_gold() — {q_num: {variable, options, total}}
        classification  : salida de classify_variables() — {q_num: {tipo, conversiones, ...}}
        n_total         : n total de la encuesta (sin filtros)
        n_segmento      : n del segmento filtrado (None si no hay filtros)
        filtros_aplicados: descripción de los filtros usados
        advertencias    : advertencias estadísticas del filtrado

    Returns:
        {
            "metadata": {
                "n_total"          : int,
                "n_segmento"       : int | None,
                "filtros_aplicados": dict | None,
                "advertencias"     : [str],
                "n_indicadores"    : int,
            },
            "indicadores": [
                {
                    # Campos comunes
                    "pregunta"      : int,
                    "variable"      : str,
                    "tipo"          : str,   # nominal/ordinal/ordinal_likert/cuantitativa
                    "interpretacion": str,
                    "n_pregunta"    : int,   # respondentes que contestaron esta pregunta
                    "nota"          : str | None,  # ej: "skip-logic aplicado"

                    # Para nominal y ordinal
                    "distribucion"  : [{label, freq, pct, pct_acumulado?}],
                    "moda"          : str,
                    "p_moda"        : float,

                    # Adicional para ordinal
                    "p_acumulados"  : [{label, p_acumulado}],

                    # Para ordinal_likert
                    "score_ponderado"  : float,  # μ en escala original
                    "score_100"        : float,  # normalizado 0-100
                    "top2_box"         : float,  # porcentaje
                    "bottom2_box"      : float,
                    "mu"               : float,
                    "sigma"            : float,

                    # Para cuantitativa
                    "mu"               : float,
                    "sigma"            : float,
                    "unidad"           : str,
                    "ic_95_lower"      : float,
                    "ic_95_upper"      : float,
                    "puntos_probabilidad": [{"x", "label", "p_at_most", "p_at_least"}],
                }
            ]
        }
    """
    indicadores: List[Dict] = []

    for q_num in sorted(gold.keys()):
        q_data = gold[q_num]
        cls    = classification.get(q_num, {})

        variable     = cls.get("variable") or q_data.get("variable", f"Variable {q_num}")
        tipo         = cls.get("tipo", "nominal")
        conversiones = cls.get("conversiones") or {}
        unidad       = cls.get("unidad") or ""
        interpretacion = cls.get("interpretacion", "")

        options  = q_data["options"]   # [{label, freq, pct}]
        n_preg   = q_data["total"]     # n que respondió esta pregunta

        # Nota de skip-logic
        nota = None
        if n_segmento is None and n_preg < n_total:
            nota = f"Skip-logic: pregunta respondida por {n_preg}/{n_total} encuestados."

        try:
            ind = _build_single_indicator(
                q_num=q_num,
                variable=variable,
                tipo=tipo,
                conversiones=conversiones,
                unidad=unidad,
                interpretacion=interpretacion,
                options=options,
                n_preg=n_preg,
                nota=nota,
            )
            indicadores.append(ind)
        except Exception as exc:
            logger.warning(f"[indicators_v2] Error en Q{q_num} ({variable}): {exc}")
            # Incluir indicador básico aunque falle el análisis avanzado
            indicadores.append(_fallback_indicator(q_num, variable, tipo, options, n_preg, nota))

    return {
        "metadata": {
            "n_total":           n_total,
            "n_segmento":        n_segmento,
            "filtros_aplicados": filtros_aplicados,
            "advertencias":      advertencias or [],
            "n_indicadores":     len(indicadores),
        },
        "indicadores": indicadores,
    }


# ── Construcción de indicador individual ──────────────────────────────────────

def _build_single_indicator(
    q_num: int,
    variable: str,
    tipo: str,
    conversiones: Dict[str, float],
    unidad: str,
    interpretacion: str,
    options: List[Dict],
    n_preg: int,
    nota: Optional[str],
) -> Dict[str, Any]:
    """Construye el indicador completo para una variable según su tipo."""

    base = {
        "pregunta":      q_num,
        "variable":      variable,
        "tipo":          tipo,
        "interpretacion": interpretacion,
        "n_pregunta":    n_preg,
        "nota":          nota,
    }

    if tipo == "cuantitativa":
        return {**base, **_build_cuantitativa(options, conversiones, unidad, n_preg)}

    elif tipo == "ordinal_likert":
        return {**base, **_build_likert(options, conversiones, unidad, n_preg)}

    elif tipo == "ordinal":
        return {**base, **_build_ordinal(options, n_preg)}

    else:  # nominal
        return {**base, **_build_nominal(options, n_preg)}


def _build_cuantitativa(
    options: List[Dict],
    conversiones: Dict[str, float],
    unidad: str,
    n: int,
) -> Dict[str, Any]:
    stats = compute_weighted_stats(options, conversiones, n)
    mu    = stats["mu"]
    sigma = stats["sigma"]

    puntos = []
    if mu is not None and sigma is not None:
        puntos = build_probability_points(mu, sigma, stats["options_with_value"], unidad)

    # Distribución con valores numéricos
    distribucion = [
        {
            "label": opt["label"],
            "value": opt.get("value"),
            "freq":  opt["freq"],
            "pct":   round(opt["pct"] * 100, 2),
        }
        for opt in _enrich_with_values(options, conversiones)
    ]

    # Moda (opción más frecuente)
    moda_opt = max(options, key=lambda o: o["freq"]) if options else {}

    return {
        "distribucion":        distribucion,
        "moda":                moda_opt.get("label", ""),
        "p_moda":              round(moda_opt.get("pct", 0) * 100, 2),
        "mu":                  mu,
        "sigma":               sigma,
        "unidad":              unidad,
        "ic_95_lower":         stats["ic_95_lower"],
        "ic_95_upper":         stats["ic_95_upper"],
        "puntos_probabilidad": puntos,
    }


def _build_likert(
    options: List[Dict],
    conversiones: Dict[str, float],
    unidad: str,
    n: int,
) -> Dict[str, Any]:
    stats = compute_likert_stats(options, conversiones, n)
    mu    = stats["mu"]
    sigma = stats["sigma"]

    puntos = []
    if mu is not None and sigma is not None and sigma > 0:
        puntos = build_probability_points(mu, sigma, stats["options_with_value"], unidad)

    distribucion = [
        {
            "label":  opt["label"],
            "value":  conversiones.get(opt["label"]),
            "freq":   opt["freq"],
            "pct":    round(opt["pct"] * 100, 2),
        }
        for opt in options
    ]

    moda_opt = max(options, key=lambda o: o["freq"]) if options else {}

    return {
        "distribucion":    distribucion,
        "moda":            moda_opt.get("label", ""),
        "p_moda":          round(moda_opt.get("pct", 0) * 100, 2),
        "mu":              mu,
        "sigma":           sigma,
        "unidad":          unidad,
        "score_ponderado": mu,
        "score_100":       stats.get("score_100"),
        "top2_box":        stats.get("top2_box"),
        "bottom2_box":     stats.get("bottom2_box"),
        "ic_95_lower":     stats.get("ic_95_lower"),
        "ic_95_upper":     stats.get("ic_95_upper"),
        "puntos_probabilidad": puntos,
    }


def _build_ordinal(options: List[Dict], n: int) -> Dict[str, Any]:
    """Ordinal: distribución completa + probabilidades acumuladas."""
    distribucion = []
    p_acumulado  = 0.0
    p_acumulados = []

    for opt in options:
        pct = round(opt["pct"] * 100, 2)
        p_acumulado = round(p_acumulado + opt["pct"] * 100, 2)
        distribucion.append({
            "label": opt["label"],
            "freq":  opt["freq"],
            "pct":   pct,
            "pct_acumulado": p_acumulado,
        })
        p_acumulados.append({"label": opt["label"], "p_acumulado": p_acumulado})

    moda_opt = max(options, key=lambda o: o["freq"]) if options else {}

    return {
        "distribucion": distribucion,
        "moda":         moda_opt.get("label", ""),
        "p_moda":       round(moda_opt.get("pct", 0) * 100, 2),
        "p_acumulados": p_acumulados,
    }


def _build_nominal(options: List[Dict], n: int) -> Dict[str, Any]:
    """Nominal: distribución completa de probabilidades."""
    distribucion = [
        {
            "label": opt["label"],
            "freq":  opt["freq"],
            "pct":   round(opt["pct"] * 100, 2),
        }
        for opt in options
    ]
    moda_opt = max(options, key=lambda o: o["freq"]) if options else {}

    # Índice de diversidad de Shannon (entropía normalizada)
    import math
    h = 0.0
    n_opts = len(options)
    for opt in options:
        p = opt["pct"]
        if p > 0:
            h -= p * math.log(p)
    h_max = math.log(n_opts) if n_opts > 1 else 1
    diversidad = round(h / h_max, 4) if h_max > 0 else 0.0

    return {
        "distribucion":      distribucion,
        "moda":              moda_opt.get("label", ""),
        "p_moda":            round(moda_opt.get("pct", 0) * 100, 2),
        "indice_diversidad": diversidad,
    }


def _fallback_indicator(q_num, variable, tipo, options, n_preg, nota) -> Dict:
    moda_opt = max(options, key=lambda o: o["freq"]) if options else {}
    return {
        "pregunta":     q_num,
        "variable":     variable,
        "tipo":         tipo,
        "interpretacion": "",
        "n_pregunta":   n_preg,
        "nota":         nota,
        "distribucion": [{"label": o["label"], "freq": o["freq"], "pct": round(o["pct"]*100,2)} for o in options],
        "moda":         moda_opt.get("label", ""),
        "p_moda":       round(moda_opt.get("pct", 0) * 100, 2),
    }


def _enrich_with_values(
    options: List[Dict],
    conversiones: Dict[str, float],
) -> List[Dict]:
    """Agrega el campo 'value' a cada opción usando las conversiones."""
    from services.pipeline.quantitative_transform import _find_conversion
    enriched = []
    for opt in options:
        val = _find_conversion(opt["label"], conversiones)
        enriched.append({**opt, "value": val})
    return enriched
