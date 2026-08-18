"""Statut d'une famille, recalcule par l'auditeur depuis le texte des regles.

**N'appelle ni `rules.influence` ni `rules.statuts`.** C'est tout l'objet de ce fichier :
si le constructeur et moi lisions le paragraphe 2.2 de la meme facon fausse, aucune
mutation du moteur ne le verrait, puisque son test et son rapport tomberaient ensemble.
Ce module est donc une deuxieme lecture, ecrite a la main.

Ce que dit le texte, et que je transcris ligne par ligne :

  - paragraphe 2.2 : « `d = (somme des valeurs en Estime) - (somme des valeurs en
    Disgrace)`, sur les cartes **vivantes** ». « Un Noble au banquet pese 2, tous les
    autres roles pesent 1. »
  - paragraphe 5.1 : le calcul porte sur les cartes vivantes **au banquet**. « Une famille
    dont aucune carte vivante n'est au banquet [...] est Indifferente (`d = 0`). »
  - seuils : Lumiere si `d >= 1`, Obscurite si `d <= -1`, Indifferente si `d == 0`.
  - paragraphe 2.6 : un joueur connait toutes les cartes face visible, et « l'identite des
    Espions qu'il a lui-meme poses » ; des Espions adverses il ne voit qu'un dos, dont
    « la position est connue » mais pas la famille.

D'ou les deux grains, volontairement distincts :

  - `VERITE` (`observateur=None`) : toutes les cartes vivantes du banquet, dos resolus.
    C'est ce grain, et lui seul, qui decide les points (paragraphe 5).
  - vue du siege `j` (`observateur=j`) : les cartes face visible, plus les Espions que `j`
    a lui-meme poses. Un dos adverse ne contribue **rien** -- pas meme son signe : `j`
    ignore de quelle famille il est.

La vue de siege n'est donc pas « la verite amputee des dos » : les trois vues peuvent
differer entre elles autant qu'elles different de la verite. Elle n'est pas non plus la
« marge pire cas » du paragraphe 2.7, qui est une borne de raisonnement et pas un statut.
"""

from __future__ import annotations

from collections.abc import Iterable

from courtisans.cards import CartePosee, GenreZone, Position, Role

#: Ce que pese une carte, paragraphe 4 des regles : le Noble 2, tous les autres 1.
#: Retranscrit ici, et non importe de `cards.VALEURS`, pour que la table du moteur et
#: celle de l'audit soient deux lectures et non une seule.
VALEUR_AUDIT: dict[Role, int] = {
    Role.ASSASSIN: 1,
    Role.GARDE: 1,
    Role.NOBLE: 2,
    Role.ESPION: 1,
    Role.NEUTRE: 1,
}

#: Les roles poses face cachee, paragraphe 4.2 : l'Espion, et lui seul.
CACHES_AUDIT: frozenset[Role] = frozenset({Role.ESPION})

LUMIERE = 1
INDIFFERENTE = 0
OBSCURITE = -1

NOM_STATUT = {LUMIERE: "Lumiere", INDIFFERENTE: "Indifferente", OBSCURITE: "Obscurite"}


def connue_de(posee: CartePosee, observateur: int | None) -> bool:
    """La famille de cette carte est-elle connue de `observateur` ?

    `None` designe la verite : tout est connu. Pour un siege, une carte face visible est
    connue de tous ; un Espion n'est connu que de son poseur (paragraphe 2.6).
    """
    if observateur is None:
        return True
    if posee.carte.role not in CACHES_AUDIT:
        return True
    return posee.poseur == observateur


def influence_par_famille(
    vivantes: Iterable[CartePosee], familles: int, observateur: int | None = None
) -> dict[int, int]:
    """`d` par famille, dans le grain demande.

    Ne comptent que les cartes **vivantes** (celles qu'on me passe), **au banquet**, et
    dont la famille est connue du grain. Une famille sans carte comptee vaut `d = 0`,
    donc Indifferente.
    """
    d = {famille: 0 for famille in range(familles)}
    for posee in vivantes:
        if posee.zone.genre is not GenreZone.BANQUET:
            continue
        if not connue_de(posee, observateur):
            continue
        if posee.zone.position is Position.ESTIME:
            signe = 1
        elif posee.zone.position is Position.DISGRACE:
            signe = -1
        else:  # pragma: no cover - une zone de banquet a toujours une position
            raise ValueError(f"carte au banquet sans position : {posee}")
        d[posee.carte.famille] += signe * VALEUR_AUDIT[posee.carte.role]
    return d


def statut_de(d: int) -> int:
    """Lumiere si `d >= 1`, Obscurite si `d <= -1`, Indifferente si `d == 0`."""
    if d >= 1:
        return LUMIERE
    if d <= -1:
        return OBSCURITE
    return INDIFFERENTE


def statuts_par_famille(
    vivantes: Iterable[CartePosee], familles: int, observateur: int | None = None
) -> dict[int, int]:
    """Le statut de chaque famille, dans le grain demande."""
    return {
        famille: statut_de(d)
        for famille, d in influence_par_famille(vivantes, familles, observateur).items()
    }


def points_par_joueur(
    vivantes: Iterable[CartePosee], familles: int, joueurs: int
) -> list[int]:
    """Les points de chaque joueur, paragraphe 5, recalcules a la main.

    Le **proprietaire du domaine** encaisse, jamais le poseur. Les cartes du banquet ne
    rapportent rien. Une carte tuee ne compte nulle part -- elle n'est pas dans
    `vivantes`. Le statut est celui de la **verite** : le decompte ne connait pas les
    vues de siege, et tous les Espions sont retournes avant le decompte (paragraphe 4.2).
    """
    statuts = statuts_par_famille(vivantes, familles, observateur=None)
    totaux = [0] * joueurs
    for posee in vivantes:
        if posee.zone.genre is not GenreZone.DOMAINE:
            continue
        proprietaire = posee.zone.proprietaire
        if proprietaire is None:  # pragma: no cover - un domaine a un proprietaire
            raise ValueError(f"domaine sans proprietaire : {posee}")
        totaux[proprietaire] += statuts[posee.carte.famille] * VALEUR_AUDIT[posee.carte.role]
    return totaux
