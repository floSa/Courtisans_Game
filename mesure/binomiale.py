"""La loi binomiale exacte : queue, intervalle de Clopper-Pearson, masse complete.

Extrait de `rapport.py`, ou ces fonctions etaient privees, parce que la phase 2 en a
besoin pour arbitrer un desaccord entre deux approximations normales. Les dupliquer aurait
viole le paragraphe 2 des conventions ; les importer par leur nom prive aurait fait pire.

**Deux implementations volontaires, et un controle qui les tient ensemble.**

`queue_superieure` somme `exp(log_binomiale)` terme par terme. C'est la forme dont l'audit
de la phase 1 a valide l'exactitude sur 820 couples `(k, n, alpha)` a 2,5e-12 pres, et elle
ne change pas : l'intervalle de Clopper-Pearson continue de passer par elle.

`masse_binomiale` rend la loi entiere par recurrence sur le rapport de deux termes
consecutifs. Les calculs de puissance de la phase 2 en ont besoin pour des `n` de l'ordre de
10 000 et des centaines de `n` successifs : la forme en `lgamma` y coute une minute la ou
celle-ci coute une seconde.

Deux routines numeriques pour la meme loi peuvent deriver en silence. `tests/mesure/
test_binomiale.py` les compare donc sur un balayage de `(n, k, p)` et exige un accord a
1e-12 : c'est le motif que l'audit de la phase 1 a impose, quatre calculs independants qui
doivent tomber sur le meme nombre.

La recurrence part du **mode** et non de `k = 0`. Partir de zero fait passer par des termes
de l'ordre de `(1 - p)^n`, soit `1e-1760` pour `n = 10 000` et `p = 1/3` : ils valent zero
en flottant, et toute la loi se retrouve normalisee a partir de rien.
"""

from __future__ import annotations

from collections.abc import Callable
from math import exp, lgamma, log, log1p


def log_binomiale(n: int, k: int, p: float) -> float:
    """Log de `C(n, k) p^k (1-p)^(n-k)`, en passant par lgamma pour ne pas deborder."""
    return (
        lgamma(n + 1)
        - lgamma(k + 1)
        - lgamma(n - k + 1)
        + k * log(p)
        + (n - k) * log1p(-p)
    )


def queue_superieure(k: int, n: int, p: float) -> float:
    """`P(X >= k)` pour `X ~ Binomiale(n, p)`."""
    if p <= 0.0:
        return 1.0 if k == 0 else 0.0
    if p >= 1.0:
        return 1.0
    return sum(exp(log_binomiale(n, i, p)) for i in range(k, n + 1))


def masse_binomiale(n: int, p: float) -> list[float]:
    """La loi complete `[P(X = 0), …, P(X = n)]`, par recurrence depuis le mode.

    `P(X = k+1) / P(X = k) = ((n - k) / (k + 1)) * (p / (1 - p))`. On pose 1 au mode, on
    remonte et on redescend par ce rapport, puis on normalise par la somme.

    Raises:
        ValueError: si `n < 0` ou si `p` n'est pas strictement entre 0 et 1 -- les cas
            degeneres ont une reponse, mais pas celle-ci, et les traiter ici masquerait un
            appel qui n'a pas de sens.
    """
    if n < 0:
        raise ValueError(f"une loi binomiale demande n >= 0, {n} recu")
    if not 0.0 < p < 1.0:
        raise ValueError(f"la recurrence demande 0 < p < 1, {p} recu")
    cote = p / (1.0 - p)
    mode = min(n, max(0, int((n + 1) * p)))
    termes = [0.0] * (n + 1)
    termes[mode] = 1.0
    for k in range(mode, n):
        termes[k + 1] = termes[k] * (n - k) / (k + 1) * cote
    for k in range(mode, 0, -1):
        termes[k - 1] = termes[k] * k / (n - k + 1) / cote
    total = sum(termes)
    return [terme / total for terme in termes]


def bissection(fonction: Callable[[float], float], iterations: int = 200) -> float:
    """Le zero d'une fonction **croissante** sur [0, 1].

    Rend `basse` et non le milieu du dernier encadrement : c'est la forme exacte que
    l'audit de la phase 1 a validee sur 820 couples `(k, n, alpha)`. L'ecart serait de
    l'ordre de `2^-200`, donc invisible -- mais un chiffre valide ne se modifie pas au
    passage d'un deplacement de fichier.
    """
    basse, haute = 0.0, 1.0
    for _ in range(iterations):
        milieu = (basse + haute) / 2
        if fonction(milieu) < 0:
            basse = milieu
        else:
            haute = milieu
    return basse


def intervalle_clopper_pearson(k: int, n: int, alpha: float = 0.01) -> tuple[float, float]:
    """L'intervalle exact de Clopper-Pearson, a `1 - alpha`.

    Exact au sens ou il ne suppose pas la normalite : a 1 000 parties l'approximation
    normale serait suffisante, mais elle ne le serait plus sur les sous-populations.
    """
    if n <= 0:
        raise ValueError(
            f"une proportion sur {n} parties n'existe pas : il en faut au moins une"
        )
    if not 0 <= k <= n:
        raise ValueError(f"{k} succes sur {n} parties : impossible")
    # Borne basse : le `p` tel que `P(X >= k) = alpha/2`.
    # Borne haute : le `p` tel que `P(X <= k) = alpha/2`, ecrit `P(X >= k+1) = 1 - alpha/2`
    # pour que les deux fonctions soient croissantes en `p` et se cherchent pareil. Ecrire
    # la seconde sous la forme `1 - P(X >= k+1) - alpha/2` la rendrait decroissante, et la
    # bissection rendrait la mauvaise borne sans rien signaler.
    basse = 0.0 if k == 0 else bissection(lambda p: queue_superieure(k, n, p) - alpha / 2)
    haute = (
        1.0
        if k == n
        else bissection(lambda p: queue_superieure(k + 1, n, p) - (1.0 - alpha / 2))
    )
    return basse, haute
