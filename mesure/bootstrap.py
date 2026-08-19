"""Le bootstrap **par donne**, et l'effet de plan qu'il chiffre.

Les 6 replicats d'une meme donne partagent la pioche : les parties d'une donne ne sont **pas
independantes**, donc la formule iid `SE = sqrt(p(1-p)/n)` n'est pas exacte. **Le sens de
l'ecart n'est pas suppose ici** -- dans un plan apparie, la correlation intra-donne reduit la
variance d'un contraste entre sieges autant qu'elle peut gonfler celle d'un taux marginal. On
le mesure, on ne l'annonce pas.

Ce qui est publie, pour chaque statistique et chaque campagne :

| Chiffre | Definition |
|---|---|
| `variance_bootstrap` | variance de la statistique sur les rechantillons |
| `variance_iid` | la meme sous l'hypothese d'independance des parties |
| **`effet`** | `variance_bootstrap / variance_iid` -- un rapport, sans signe suppose |
| **`n_effectif`** | `n / effet` |

Le rechantillonnage tire des **donnes** avec remise, chacune entrant avec **tous ses
replicats**. Tirer des parties detruirait exactement la structure qu'on veut mesurer.

Ce module ne joue aucune partie : il prend des observations deja produites.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import fmean, variance


@dataclass(frozen=True)
class EffetDePlan:
    """Ce qu'un bootstrap par donne rend sur une statistique.

    Attributes:
        moyenne: la statistique sur l'echantillon observe -- la moyenne de toutes les parties.
        nb_donnes: nombre de donnes rechantillonnees.
        nb_parties: nombre total de parties.
        variance_bootstrap: variance de la moyenne sur les rechantillons.
        variance_iid: variance de la moyenne sous independance, `s^2 / n`.
        effet: `variance_bootstrap / variance_iid`. **Sans signe suppose.**
        n_effectif: `nb_parties / effet`.
        intervalle: intervalle de percentiles du bootstrap, au niveau demande.
    """

    moyenne: float
    nb_donnes: int
    nb_parties: int
    variance_bootstrap: float
    variance_iid: float
    effet: float
    n_effectif: float
    intervalle: tuple[float, float]

    def erreur_type_bootstrap(self) -> float:
        """L'ecart-type de la statistique, version bootstrap."""
        return self.variance_bootstrap**0.5

    def erreur_type_iid(self) -> float:
        """L'ecart-type de la statistique, version iid -- celle des seuils du plan."""
        return self.variance_iid**0.5


def correlation_intra_donne(observations: Sequence[Sequence[float]]) -> float | None:
    """La correlation intra-donne, par decomposition de variance a un facteur.

    `rho = variance inter-donnes / variance totale`, estimee par le rapport de correlation
    intraclasse d'une analyse de variance a un facteur, sur des groupes de taille egale :

        rho = (CM_inter - CM_intra) / (CM_inter + (m - 1) CM_intra)

    ou `m` est le nombre de replicats par donne. C'est **la** quantite qui dit de combien un
    plan apparie reduit le nombre de parties necessaires : la variance d'un contraste apparie
    vaut `2 sigma^2 (1 - rho)` contre `2 sigma^2` sans appariement, donc le gain est un facteur
    `1 / (1 - rho)`.

    Le paragraphe 1 du protocole affirme que l'appariement « divise par cinq a dix » le nombre
    de parties, ce qui implique `rho` dans `[0,8 ; 0,9]`. **Cette affirmation n'est appuyee par
    aucune mesure du depot** : c'est le cinquieme trou signale, et le seul qui soit un chiffre.

    Rend `None` s'il y a moins de deux donnes ou moins de deux replicats -- `rho` n'y est pas
    defini, et rendre 0 ferait lire « aucune correlation ».

    Raises:
        ValueError: si les donnes n'ont pas toutes le meme nombre de replicats. La formule
            ci-dessus suppose des groupes equilibres ; l'appliquer a des groupes inegaux
            rendrait un nombre sans le signaler.
    """
    if len(observations) < 2:
        return None
    tailles = {len(groupe) for groupe in observations}
    if len(tailles) != 1:
        raise ValueError(
            f"le rapport intraclasse suppose des donnes de meme taille, tailles vues : "
            f"{sorted(tailles)}"
        )
    replicats = tailles.pop()
    if replicats < 2:
        return None
    toutes = [valeur for groupe in observations for valeur in groupe]
    grande_moyenne = fmean(toutes)
    moyennes = [fmean(groupe) for groupe in observations]
    nb_donnes = len(observations)

    carres_inter = replicats * sum((m - grande_moyenne) ** 2 for m in moyennes)
    carres_intra = sum(
        (valeur - moyennes[indice]) ** 2
        for indice, groupe in enumerate(observations)
        for valeur in groupe
    )
    cm_inter = carres_inter / (nb_donnes - 1)
    cm_intra = carres_intra / (nb_donnes * (replicats - 1))
    denominateur = cm_inter + (replicats - 1) * cm_intra
    if denominateur == 0:
        return None
    return (cm_inter - cm_intra) / denominateur


def bootstrap_par_donne(
    observations: Sequence[Sequence[float]],
    repetitions: int,
    alea: random.Random,
    risque: float = 0.01,
) -> EffetDePlan:
    """Rechantillonne les **donnes** avec remise et chiffre l'effet de plan.

    Args:
        observations: une liste par donne, contenant la valeur de chaque partie de cette donne.
        repetitions: nombre de rechantillons.
        alea: le generateur, passe explicitement -- aucun appel a `random` global (paragraphe 5
            des conventions).
        risque: niveau de l'intervalle de percentiles. `0.01` donne un intervalle a 99 %.

    Raises:
        ValueError: si les observations sont vides, si `repetitions < 2`, ou si `risque` sort
            de `]0, 1[`.
    """
    if not observations or not any(observations):
        raise ValueError("aucune observation : un bootstrap ne se fait pas sur du vide")
    if repetitions < 2:
        raise ValueError(f"il faut au moins 2 rechantillons, {repetitions} demande(s)")
    if not 0 < risque < 1:
        raise ValueError(f"un risque vaut strictement entre 0 et 1, {risque} recu")

    toutes = [valeur for groupe in observations for valeur in groupe]
    nb_parties = len(toutes)
    nb_donnes = len(observations)
    moyenne = fmean(toutes)
    variance_iid = (
        variance(toutes) / nb_parties if nb_parties > 1 else 0.0
    )

    # Rechantillonner en reconstruisant la liste des parties couterait
    # `repetitions x nb_parties` operations -- 100 millions au plan de la phase 2. La moyenne
    # d'un rechantillon ne depend que de la **somme** et du **compte** de chaque donne tiree :
    # on precalcule les deux, et le cout retombe a `repetitions x nb_donnes`. Le resultat est
    # **exact**, pas approche -- c'est la meme moyenne, calculee autrement.
    sommes = [math.fsum(groupe) for groupe in observations]
    comptes = [len(groupe) for groupe in observations]
    indices = range(nb_donnes)
    moyennes: list[float] = []
    for _ in range(repetitions):
        tires = [alea.choice(indices) for _ in indices]
        total = math.fsum(sommes[indice] for indice in tires)
        effectif = sum(comptes[indice] for indice in tires)
        moyennes.append(total / effectif)
    variance_bootstrap = variance(moyennes)

    moyennes.sort()
    bas = int(risque / 2 * repetitions)
    haut = min(repetitions - 1, int((1 - risque / 2) * repetitions))
    effet = variance_bootstrap / variance_iid if variance_iid > 0 else float("inf")
    return EffetDePlan(
        moyenne=moyenne,
        nb_donnes=nb_donnes,
        nb_parties=nb_parties,
        variance_bootstrap=variance_bootstrap,
        variance_iid=variance_iid,
        effet=effet,
        n_effectif=nb_parties / effet if effet > 0 else float("inf"),
        intervalle=(moyennes[bas], moyennes[haut]),
    )
