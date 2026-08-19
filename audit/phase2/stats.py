"""Intervalles et pouvoir discriminant, reecrits sans bibliotheque statistique.

Deux fonctions seulement, et la seconde est celle qui manque toujours.

`clopper_pearson` donne l'intervalle exact d'une proportion. Il est calcule par
bissection sur la queue binomiale, en log-gamma pour rester stable a `n = 10 000`. Aucune
dependance : `scipy` est present dans l'environnement, il sert de **second avis** dans les
tests, jamais de source.

`ecart_detectable` et `separable_de_zero` repondent a la question que la phase 1 a ratee
sur son critere D2 : **a partir de quel ecart la mesure tranche-t-elle ?** Un seuil qu'un
echantillon franchit des la douzieme partie ne teste rien ; un compteur dont l'ecart
detectable depasse le taux mesure ne peut separer aucun agent par le bas, pas meme un
agent qui ne manifeste jamais le comportement. Publier le taux sans ces deux chiffres
laisse croire a un test la ou il n'y a qu'un constat.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, lgamma, sqrt


def _log_coef(n: int, k: int) -> float:
    """`log C(n, k)`, par log-gamma : stable la ou `math.comb` deborde en flottant."""
    return lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1)


def binom_queue_basse(k: int, n: int, p: float) -> float:
    """`P(X <= k)` pour `X ~ Binomiale(n, p)`. Somme exacte, terme a terme."""
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 1.0 if k >= n else 0.0
    from math import log, log1p

    total = 0.0
    for i in range(k + 1):
        total += exp(_log_coef(n, i) + i * log(p) + (n - i) * log1p(-p))
    return min(1.0, total)


def binom_queue_haute(k: int, n: int, p: float) -> float:
    """`P(X >= k)`."""
    if k <= 0:
        return 1.0
    return 1.0 - binom_queue_basse(k - 1, n, p)


def _bissection(fonction, cible: float, bas: float, haut: float, tours: int = 200) -> float:
    """Racine de `fonction(p) = cible` sur `[bas, haut]`, fonction monotone."""
    croissante = fonction(haut) > fonction(bas)
    for _ in range(tours):
        milieu = 0.5 * (bas + haut)
        valeur = fonction(milieu)
        if (valeur < cible) == croissante:
            bas = milieu
        else:
            haut = milieu
    return 0.5 * (bas + haut)


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """L'intervalle exact de Clopper-Pearson, au niveau `1 - alpha`.

    Args:
        k: succes observes.
        n: essais. **Doit etre strictement positif** : un intervalle sur zero observation
            n'existe pas, exactement comme un taux sur un denominateur vide.
        alpha: risque total, reparti egalement entre les deux bornes.

    Raises:
        ValueError: si `n <= 0`, si `k` sort de `[0, n]`, ou si `alpha` sort de `]0, 1[`.
    """
    if n <= 0:
        raise ValueError(
            f"n = {n} : un intervalle de confiance sur zero observation n'existe pas"
        )
    if not 0 <= k <= n:
        raise ValueError(f"k = {k} hors de [0, {n}]")
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha = {alpha} hors de ]0, 1[")
    bas = (
        0.0
        if k == 0
        else _bissection(lambda p: binom_queue_haute(k, n, p), alpha / 2, 0.0, 1.0)
    )
    haut = (
        1.0
        if k == n
        else _bissection(lambda p: binom_queue_basse(k, n, p), alpha / 2, 0.0, 1.0)
    )
    return bas, haut


def _phi_inverse(p: float) -> float:
    """Quantile de la loi normale centree reduite, par bissection sur `erf`."""
    if not 0.0 < p < 1.0:
        raise ValueError(f"quantile hors de ]0, 1[ : {p}")
    return _bissection(lambda x: 0.5 * (1 + erf(x / sqrt(2))), p, -12.0, 12.0)


@dataclass(frozen=True)
class PouvoirDiscriminant:
    """Ce qu'un compteur peut trancher au budget d'une phase.

    Attributes:
        taux_mesure: la ligne de base observee.
        ecart_detectable: le plus petit ecart absolu qu'un test bilateral a 95 % detecte
            avec 80 % de puissance, aux effectifs donnes.
        aveugle_par_le_bas: vrai si `ecart_detectable > taux_mesure`. Alors **aucun agent
            ne peut etre separe du greedy par le bas**, pas meme un agent a zero, qui n'est
            distant que du taux mesure lui-meme. Le compteur ne teste rien de ce cote.
        borne_zero: borne haute exacte d'un agent observe a `0 / n_agent`.
        separable_de_zero: vrai si l'intervalle du greedy et celui d'un agent a zero sont
            disjoints. C'est le test exact, sans approximation normale.
    """

    nom: str
    taux_mesure: float
    n_base: int
    n_agent: int
    ecart_detectable: float
    aveugle_par_le_bas: bool
    borne_zero: float
    separable_de_zero: bool


def ecart_detectable(
    p: float, n1: int, n2: int, alpha: float = 0.05, puissance: float = 0.80
) -> float:
    """Le plus petit ecart absolu detectable entre deux proportions.

    Resout `delta = z_alpha sqrt(pbar qbar (1/n1 + 1/n2)) + z_beta sqrt(p q / n1 + p2 q2 /
    n2)` par point fixe, avec `p2 = p - delta` borne a zero. Approximation normale
    assumee : elle sert a dire l'ordre de grandeur d'un seuil, pas a conclure.
    """
    if n1 <= 0 or n2 <= 0:
        raise ValueError(f"effectifs vides : n1 = {n1}, n2 = {n2}")
    z_alpha = _phi_inverse(1 - alpha / 2)
    z_beta = _phi_inverse(puissance)
    delta = 0.0
    for _ in range(200):
        p2 = max(0.0, p - delta)
        moyen = (p * n1 + p2 * n2) / (n1 + n2)
        bruit_nul = sqrt(moyen * (1 - moyen) * (1 / n1 + 1 / n2))
        bruit_alt = sqrt(p * (1 - p) / n1 + p2 * (1 - p2) / n2)
        nouveau = z_alpha * bruit_nul + z_beta * bruit_alt
        if abs(nouveau - delta) < 1e-12:
            break
        delta = nouveau
    return delta


def pouvoir(
    nom: str, k: int, n_base: int, n_agent: int, alpha: float = 0.05
) -> PouvoirDiscriminant:
    """Le pouvoir discriminant d'un compteur, aux effectifs de la phase suivante."""
    if n_base <= 0:
        raise ValueError(
            f"{nom} : denominateur vide, aucun pouvoir discriminant a calculer"
        )
    p = k / n_base
    delta = ecart_detectable(p, n_base, n_agent, alpha)
    bas_greedy, _ = clopper_pearson(k, n_base, alpha)
    _, haut_zero = clopper_pearson(0, n_agent, alpha)
    return PouvoirDiscriminant(
        nom=nom,
        taux_mesure=p,
        n_base=n_base,
        n_agent=n_agent,
        ecart_detectable=delta,
        aveugle_par_le_bas=delta > p,
        borne_zero=haut_zero,
        separable_de_zero=bas_greedy > haut_zero,
    )


def taille_pour_seuil(p0: float, seuil: float, alpha: float = 0.05) -> int:
    """A partir de quelle taille d'echantillon `seuil` devient un test de niveau `alpha`.

    Repond a « ce seuil discrimine-t-il ? ». Si la taille rendue est tres inferieure a
    celle employee, le seuil est franchi mecaniquement et ne teste rien ; si elle est tres
    superieure, le seuil ne sera jamais atteint et ne teste rien non plus.
    """
    if not 0.0 < p0 < 1.0:
        raise ValueError(f"p0 hors de ]0, 1[ : {p0}")
    if seuil == p0:
        raise ValueError("un seuil egal a la valeur nulle ne teste rien")
    z = _phi_inverse(1 - alpha / 2)
    return max(1, int((z * z * p0 * (1 - p0)) / ((seuil - p0) ** 2) + 0.999999))


def ecarts_types_du_seuil(p0: float, seuil: float, n: int) -> float:
    """A combien d'erreurs-type de `p0` se trouve `seuil`, a l'effectif `n`."""
    if n <= 0:
        raise ValueError(f"effectif vide : {n}")
    return abs(seuil - p0) / sqrt(p0 * (1 - p0) / n)
