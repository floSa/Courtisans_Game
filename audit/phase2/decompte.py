"""Le decompte, reecrit depuis le texte des regles, sans appeler `courtisans.rules`.

Reimplementation deliberee. Si l'auditeur reutilisait `rules.statuts` et `rules.points`,
une erreur de lecture partagee entre le constructeur et lui passerait les deux fois. Les
deux implementations sont ensuite confrontees sur des dizaines de milliers d'etats.

Le texte suivi, mot a mot :

  - paragraphe 2.2 : `d = (somme des VALEURS en Estime) - (somme des VALEURS en Disgrace)`,
    sur les cartes **vivantes**, au banquet seulement.
  - paragraphe 5 : `d >= 1` Lumiere, `d <= -1` Obscurite, `d == 0` Indifferente. Une
    famille sans carte vivante au banquet est Indifferente.
  - paragraphe 5 : les points vont au **proprietaire du domaine**, jamais au poseur ; les
    cartes du banquet ne rapportent rien ; les cartes tuees ne comptent nulle part.
  - paragraphe 5.2 : gain `+1` au vainqueur unique, `+(n-k)/(k(n-1))` a chacun de `k` ex
    aequo, `-1/(n-1)` aux perdants.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from courtisans.cards import CartePosee, GenreZone, Position, Role

#: Le Noble pese 2, tous les autres roles pesent 1 (paragraphe 4). Retranscrit ici plutot
#: qu'importe de `courtisans.cards` : c'est la table dont depend tout le decompte, et une
#: erreur partagee dessus fausserait les deux calculs de la meme facon.
VALEUR_AUDIT: Mapping[Role, int] = {
    Role.ASSASSIN: 1,
    Role.GARDE: 1,
    Role.NOBLE: 2,
    Role.ESPION: 1,
    Role.NEUTRE: 1,
}

LUMIERE = 1
INDIFFERENTE = 0
OBSCURITE = -1


def valeur(role: Role) -> int:
    """La valeur d'un role, en influence comme en points."""
    return VALEUR_AUDIT[role]


def influences(posees: Iterable[CartePosee], familles: int) -> dict[int, int]:
    """`d` par famille, sur les seules cartes vivantes du banquet."""
    resultat = dict.fromkeys(range(familles), 0)
    for posee in posees:
        if posee.zone.genre is not GenreZone.BANQUET:
            continue
        signe = 1 if posee.zone.position is Position.ESTIME else -1
        resultat[posee.carte.famille] += signe * valeur(posee.carte.role)
    return resultat


def statut(d: int) -> int:
    """Lumiere si `d >= 1`, Obscurite si `d <= -1`, Indifferente si `d == 0`."""
    if d >= 1:
        return LUMIERE
    if d <= -1:
        return OBSCURITE
    return INDIFFERENTE


def statuts(posees: Iterable[CartePosee], familles: int) -> dict[int, int]:
    """Le statut de chaque famille. Sans carte au banquet, Indifferente par `d == 0`."""
    return {f: statut(d) for f, d in influences(posees, familles).items()}


def scores(posees: Iterable[CartePosee], familles: int, joueurs: int) -> list[int]:
    """Les points bruts. Credite le proprietaire du domaine, jamais le poseur."""
    posees = tuple(posees)
    table = statuts(posees, familles)
    totaux = [0] * joueurs
    for posee in posees:
        if posee.zone.genre is not GenreZone.DOMAINE:
            continue
        totaux[posee.zone.proprietaire] += (
            table[posee.carte.famille] * valeur(posee.carte.role)
        )
    return totaux


def gains(scores_finaux: Sequence[int]) -> list[float]:
    """La formule du paragraphe 5.2, a somme nulle, egalites conservees."""
    n = len(scores_finaux)
    if n < 2:
        raise ValueError(f"il faut au moins 2 joueurs, {n} recu(s)")
    meilleur = max(scores_finaux)
    k = sum(1 for s in scores_finaux if s == meilleur)
    gagne = (n - k) / (k * (n - 1))
    perd = -1 / (n - 1)
    return [gagne if s == meilleur else perd for s in scores_finaux]


def ecart(scores_bruts: Sequence[int], moi: int) -> int:
    """Mon score moins le meilleur des autres. L'objectif du greedy (paragraphe 7.1)."""
    autres = [s for j, s in enumerate(scores_bruts) if j != moi]
    return scores_bruts[moi] - max(autres)
