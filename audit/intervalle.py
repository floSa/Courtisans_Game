"""Intervalle de Clopper-Pearson, reimplemente par l'auditeur.

Ecrit AVANT toute lecture du code du constructeur. Trois routes independantes, qui
doivent donner le meme chiffre :

  1. `par_quantile_beta`  -- la forme fermee : les bornes sont des quantiles de lois
     Beta (scipy, algorithme sans rapport avec une bissection).
  2. `par_queue_binomiale` -- la DEFINITION : la borne basse est le plus petit p tel
     que P(X >= x | n, p) >= alpha/2, la borne haute le plus grand p tel que
     P(X <= x | n, p) >= alpha/2. Resolu par bissection ecrite ici, sur une CDF
     binomiale calculee a la main via lgamma.
  3. `par_scipy_binomtest` -- l'implementation de reference de scipy.

Convention : intervalle bilateral, chaque queue vaut alpha/2 (IC99 -> 0.005 par
queue). Bornes degenerees : x = 0 -> borne basse 0 ; x = n -> borne haute 1.
"""

from __future__ import annotations

import math

from scipy.stats import beta, binomtest


def _log_binom(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def cdf_binomiale(x: int, n: int, p: float) -> float:
    """P(X <= x) pour X ~ Binomiale(n, p). Somme explicite, sans scipy."""
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 1.0 if x >= n else 0.0
    total = 0.0
    for k in range(0, x + 1):
        total += math.exp(_log_binom(n, k) + k * math.log(p) + (n - k) * math.log1p(-p))
    return min(1.0, total)


def survie_binomiale(x: int, n: int, p: float) -> float:
    """P(X >= x) pour X ~ Binomiale(n, p)."""
    if x <= 0:
        return 1.0
    return 1.0 - cdf_binomiale(x - 1, n, p)


def par_quantile_beta(x: int, n: int, confiance: float = 0.99) -> tuple[float, float]:
    """Forme fermee de Clopper-Pearson : quantiles de lois Beta."""
    _valide(x, n, confiance)
    alpha = 1.0 - confiance
    basse = 0.0 if x == 0 else float(beta.ppf(alpha / 2.0, x, n - x + 1))
    haute = 1.0 if x == n else float(beta.ppf(1.0 - alpha / 2.0, x + 1, n - x))
    return basse, haute


def par_queue_binomiale(
    x: int, n: int, confiance: float = 0.99, tours: int = 200
) -> tuple[float, float]:
    """Definition exacte, resolue par bissection sur les queues binomiales.

    Borne basse : plus petit p avec P(X >= x | p) >= alpha/2. La fonction
    p -> P(X >= x | p) est croissante, donc on bissecte sur [0, x/n].
    Borne haute : plus grand p avec P(X <= x | p) >= alpha/2. La fonction
    p -> P(X <= x | p) est decroissante, donc on bissecte sur [x/n, 1].
    """
    _valide(x, n, confiance)
    seuil = (1.0 - confiance) / 2.0

    if x == 0:
        basse = 0.0
    else:
        lo, hi = 0.0, x / n
        for _ in range(tours):
            mid = 0.5 * (lo + hi)
            if survie_binomiale(x, n, mid) >= seuil:
                hi = mid
            else:
                lo = mid
        basse = 0.5 * (lo + hi)

    if x == n:
        haute = 1.0
    else:
        lo, hi = x / n, 1.0
        for _ in range(tours):
            mid = 0.5 * (lo + hi)
            if cdf_binomiale(x, n, mid) >= seuil:
                lo = mid
            else:
                hi = mid
        haute = 0.5 * (lo + hi)

    return basse, haute


def par_scipy_binomtest(x: int, n: int, confiance: float = 0.99) -> tuple[float, float]:
    """L'implementation de reference de scipy, comme troisieme temoin."""
    _valide(x, n, confiance)
    ic = binomtest(x, n).proportion_ci(confidence_level=confiance, method="exact")
    return float(ic.low), float(ic.high)


def _valide(x: int, n: int, confiance: float) -> None:
    if n <= 0:
        raise ValueError(f"n doit etre strictement positif, recu {n}")
    if not 0 <= x <= n:
        raise ValueError(f"x doit etre dans [0, {n}], recu {x}")
    if not 0.0 < confiance < 1.0:
        raise ValueError(f"confiance doit etre dans ]0, 1[, recu {confiance}")
