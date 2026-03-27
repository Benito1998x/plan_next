"""
Transformador Cuantitativo (Sprint 3)

Calcula estadísticas ponderadas para variables cuantitativas y Likert:
  - Media ponderada (μ)
  - Desviación estándar ponderada (σ)
  - Intervalo de confianza al 95%: [μ - 1.96σ/√n, μ + 1.96σ/√n]
  - Probabilidad acumulada P(X ≤ x) usando distribución normal (Z-score)
  - TOP-2 Box / BOTTOM-2 Box para Likert

Las conversiones numéricas son dinámicas: vienen del AIAgent, no están hardcodeadas.

Fuentes:
  Montgomery & Runger — Applied Statistics and Probability for Engineers
  Field — Discovering Statistics Using IBM SPSS
"""

import math
from typing import Dict, Any, List, Optional, Tuple


def compute_weighted_stats(
    options: List[Dict[str, Any]],
    conversiones: Dict[str, float],
    n_total: int,
) -> Dict[str, Any]:
    """
    Calcula estadísticas ponderadas para una variable cuantitativa.

    Args:
        options     : lista de opciones Gold [{label, freq, pct}, ...]
        conversiones: {label: valor_numérico} — del AI agent
        n_total     : n de la pregunta (total de respuestas válidas)

    Returns:
        {
            "mu":       float,   # media ponderada
            "sigma":    float,   # desviación estándar ponderada
            "ic_95":    [lower, upper],
            "options_with_value": [{label, value, freq, pct}, ...],
            "p_at_most": callable(x) → P(X ≤ x),
            "p_at_least": callable(x) → P(X ≥ x),
        }
    """
    # Emparejar opciones con sus valores numéricos
    pairs: List[Tuple[float, int, float]] = []  # (valor, freq, pct)
    options_with_value = []

    for opt in options:
        label = opt["label"]
        freq  = opt["freq"]
        pct   = opt["pct"]  # ya es proporción [0,1]

        # Buscar conversión (coincidencia exacta, luego parcial)
        value = _find_conversion(label, conversiones)
        if value is None:
            continue  # saltar opciones sin conversión conocida

        pairs.append((value, freq, pct))
        options_with_value.append({
            "label": label,
            "value": value,
            "freq":  freq,
            "pct":   pct,
        })

    if not pairs:
        return _empty_stats()

    # Media ponderada: μ = Σ(valor_i × P_i)
    # Usando pct (proporción) como peso, no freq, para ser invariante al n
    mu = sum(v * p for v, _, p in pairs)

    # Varianza ponderada: σ² = Σ(P_i × (valor_i - μ)²)
    variance = sum(p * (v - mu) ** 2 for v, _, p in pairs)
    sigma = math.sqrt(variance) if variance > 0 else 0.0

    # Intervalo de confianza 95%: μ ± 1.96 × σ / √n
    n = n_total
    margin = 1.96 * sigma / math.sqrt(n) if n > 0 and sigma > 0 else 0.0

    return {
        "mu":               round(mu, 4),
        "sigma":            round(sigma, 4),
        "ic_95_lower":      round(mu - margin, 4),
        "ic_95_upper":      round(mu + margin, 4),
        "n":                n,
        "options_with_value": options_with_value,
    }


def cumulative_probability(x: float, mu: float, sigma: float) -> float:
    """
    P(X ≤ x) bajo distribución normal con media μ y desv. estándar σ.

    Usa math.erf (sin scipy) para mayor portabilidad.
    Precisión suficiente para planificación de negocios.
    """
    if sigma <= 0:
        return 1.0 if x >= mu else 0.0
    z = (x - mu) / sigma
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def survival_probability(x: float, mu: float, sigma: float) -> float:
    """P(X ≥ x) = 1 - P(X ≤ x)"""
    return 1.0 - cumulative_probability(x, mu, sigma)


def compute_likert_stats(
    options: List[Dict[str, Any]],
    conversiones: Dict[str, float],
    n_total: int,
) -> Dict[str, Any]:
    """
    Estadísticas especializadas para variables Likert.

    Incluye todo lo de compute_weighted_stats más:
      - TOP-2 Box: suma de las dos opciones más positivas (mayor score)
      - BOTTOM-2 Box: suma de las dos opciones más negativas (menor score)
      - Score ponderado normalizado a [0, 100]

    Args:
        options     : opciones Gold ordenadas como aparecen en la encuesta
        conversiones: {label: score (5→1)}
        n_total     : n de la pregunta

    Returns:
        dict con todos los campos de compute_weighted_stats más top2, bottom2, score_100
    """
    stats = compute_weighted_stats(options, conversiones, n_total)
    if not stats.get("options_with_value"):
        return stats

    # Ordenar por score descendente para TOP/BOTTOM box
    sorted_opts = sorted(stats["options_with_value"], key=lambda o: o["value"], reverse=True)

    top2_pct    = sum(o["pct"] for o in sorted_opts[:2])
    bottom2_pct = sum(o["pct"] for o in sorted_opts[-2:]) if len(sorted_opts) >= 2 else 0.0

    # Score normalizado a 0-100
    max_score = max(conversiones.values()) if conversiones else 5
    min_score = min(conversiones.values()) if conversiones else 1
    score_range = max_score - min_score
    score_100 = ((stats["mu"] - min_score) / score_range * 100) if score_range > 0 else 0.0

    stats["top2_box"]    = round(top2_pct * 100, 1)    # porcentaje
    stats["bottom2_box"] = round(bottom2_pct * 100, 1)
    stats["score_100"]   = round(score_100, 1)
    stats["max_score"]   = max_score
    stats["min_score"]   = min_score

    return stats


def build_probability_points(
    mu: float,
    sigma: float,
    options_with_value: List[Dict],
    unidad: str = "",
) -> List[Dict[str, Any]]:
    """
    Construye puntos de probabilidad acumulada para los valores representativos
    de la variable (los valores de cada opción).

    Útil para la tabla de indicadores:
      P(X ≤ valor_opcion_1), P(X ≤ valor_opcion_2), ...

    Returns:
        [{"x": float, "label": str, "p_at_most": float, "p_at_least": float}, ...]
    """
    if sigma <= 0:
        return []

    points = []
    seen_values = set()
    for opt in sorted(options_with_value, key=lambda o: o["value"]):
        v = opt["value"]
        if v in seen_values:
            continue
        seen_values.add(v)
        p_le = cumulative_probability(v, mu, sigma)
        points.append({
            "x":          v,
            "label":      f"{opt['label']} ({v:.1f} {unidad})".strip(),
            "p_at_most":  round(p_le, 4),
            "p_at_least": round(1 - p_le, 4),
        })
    return points


# ── helpers ───────────────────────────────────────────────────────────────────

def _find_conversion(label: str, conversiones: Dict[str, float]) -> Optional[float]:
    """Busca el valor numérico de una opción en el diccionario de conversiones."""
    # Coincidencia exacta
    if label in conversiones:
        return conversiones[label]
    # Coincidencia case-insensitive
    label_lower = label.lower().strip()
    for key, val in conversiones.items():
        if key.lower().strip() == label_lower:
            return val
    # Coincidencia parcial (el label contiene la clave o viceversa)
    for key, val in conversiones.items():
        if key.lower().strip() in label_lower or label_lower in key.lower().strip():
            return val
    return None


def _empty_stats() -> Dict[str, Any]:
    return {
        "mu": None,
        "sigma": None,
        "ic_95_lower": None,
        "ic_95_upper": None,
        "n": 0,
        "options_with_value": [],
    }
