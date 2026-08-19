"""Le journal d'une partie, vu par l'**analyste**, pas par un joueur.

Distinction centrale, et elle n'est pas negociable dans les deux sens :

  - une **politique** ne voit que `audit.phase2.vue.VueLegale`. Si elle voit plus, elle
    triche, et tout ce qu'on mesure sur elle est faux ;
  - un **compteur de comportement** voit tout. Demander a l'analyste de compter a
    l'aveugle serait absurde : « la famille a-t-elle bascule » est une question sur le
    plateau reel, pas sur la croyance d'un siege.

Ce module produit donc une trace omnisciente, et chaque grandeur derivee y est calculee
**a l'instant de la decision**, pas reconstruite apres coup : un `d` recalcule en fin de
partie repondrait a une autre question que celle qu'on pose.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from courtisans.cards import Carte, CartePosee, GenreZone, Position
from courtisans.engine import Engine, Phase, State
from courtisans.rules import ROLES_IMMUNISES_CONTRE_ASSASSIN

from audit.phase2.decompte import (
    LUMIERE,
    OBSCURITE,
    ecart,
    gains,
    influences,
    scores,
    statut,
    statuts,
    valeur,
)
from audit.phase2.vue import vue_legale


class Politique(Protocol):
    """Tout ce qu'un agent doit offrir : une action legale a chaque noeud."""

    def action(self, etat: State) -> int:  # pragma: no cover - protocole
        ...


@dataclass(frozen=True)
class EvenementPose:
    """Une pose : les trois cartes, et l'etat du plateau a l'instant du choix.

    Attributes:
        index: rang global de l'evenement dans la partie, strictement croissant.
        tour: numero du tour de table, a partir de 0.
        joueur: qui pose.
        destinataire: l'adversaire qui recoit la troisieme carte.
        banquet, propre, adverse: les trois cartes posees, avec leur zone.
        d_avant: `d` par famille, plateau reel, **avant** la pose.
        d_visible_avant: `d` par famille tel que `joueur` peut le calculer.
        dos_adverses_banquet: dos adverses au banquet, vus par `joueur`, avant la pose.
        expose_avant: familles dont `joueur` a une carte vivante dans son propre domaine,
            vue analyste. `expose_visible_avant` est la meme chose vue du siege : elle
            ignore les Espions adverses poses dans son domaine, dont il ne connait pas la
            famille. L'ecart entre les deux chiffre ce que la definition coute.
        imprenables_avant: familles hors d'atteinte avant la pose -- voir `_imprenables`.
    """

    index: int
    tour: int
    joueur: int
    destinataire: int
    banquet: CartePosee
    propre: CartePosee
    adverse: CartePosee
    d_avant: Mapping[int, int]
    d_visible_avant: Mapping[int, int]
    dos_adverses_banquet: int
    expose_avant: frozenset[int]
    expose_visible_avant: frozenset[int]
    imprenables_avant: frozenset[int]


@dataclass(frozen=True)
class EvenementCiblage:
    """Un noeud de ciblage : les cibles offertes, le choix, et ce qu'il valait.

    Attributes:
        cibles: les cartes que cet Assassin pouvait tuer. Vide = aucune decision.
        victime: la carte tuee, ou `None` si refus.
        refus: vrai si le joueur a refuse de tuer.
        ecart_si_refus: ecart reel du tueur, partie arretee, s'il refuse.
        ecarts_si_meurtre: ecart reel apres chaque meurtre possible, meme ordre que
            `cibles`.
    """

    index: int
    tour: int
    joueur: int
    assassin: CartePosee
    cibles: tuple[CartePosee, ...]
    victime: CartePosee | None
    refus: bool
    ecart_si_refus: int
    ecarts_si_meurtre: tuple[int, ...]
    d_avant: Mapping[int, int]


@dataclass
class Trace:
    """Une partie entiere : ses evenements, et son issue."""

    seed: int
    config_familles: int
    joueurs: int
    tours: int
    poses: list[EvenementPose] = field(default_factory=list)
    ciblages: list[EvenementCiblage] = field(default_factory=list)
    statuts_finaux: dict[int, int] = field(default_factory=dict)
    scores_finaux: list[int] = field(default_factory=list)
    gains_finaux: list[float] = field(default_factory=list)

    @property
    def vainqueurs(self) -> tuple[int, ...]:
        """Les sieges au score maximum. Plusieurs en cas d'ex aequo (paragraphe 5.1)."""
        meilleur = max(self.scores_finaux)
        return tuple(j for j, s in enumerate(self.scores_finaux) if s == meilleur)


def _expose(posees: Sequence[CartePosee], joueur: int) -> frozenset[int]:
    """Les familles dont `joueur` a une carte vivante dans **son propre** domaine.

    C'est la definition de « etre expose sur une famille » : ce sont ces cartes-la qui
    rapportent ou coutent a `joueur` selon le statut final de leur famille (paragraphe 5).
    """
    return frozenset(
        posee.carte.famille
        for posee in posees
        if posee.zone.genre is GenreZone.DOMAINE and posee.zone.proprietaire == joueur
    )


def _circulantes(etat: State) -> tuple[Carte, ...]:
    """Les cartes qui peuvent encore etre posees : pioche et mains.

    Vue analyste. Une carte morte n'y est pas, une carte posee non plus.
    """
    dieu = etat.vue_privilegiee()
    return (*dieu.pioche, *(carte for main in dieu.mains for carte in main))


def _imprenables(etat: State) -> frozenset[int]:
    """Les familles dont le statut ne peut plus changer, borne genereusement.

    Paragraphe 2.6 : « un joueur fort sait quand une famille est hors d'atteinte ». La
    borne se compose de deux leviers, les deux du paragraphe 2.2 :

      - **poser** des cartes de la famille du cote defavorable. Au plus une carte par pose
        au banquet, donc au plus `occasions` cartes, et on prend les plus lourdes ;
      - **tuer** les cartes de la famille deja au banquet du cote favorable, Gardes exclus
        (paragraphe 4.3).

    La borne **ignore** la disponibilite des Assassins et le fait qu'un joueur adverse
    n'aurait aucun interet a jouer ainsi. C'est deliberement genereux : declarer une
    famille imprenable est alors une affirmation prudente, et le compteur B7 ne peut pas
    surestimer le gaspillage.
    """
    config = etat.config
    posees = etat.vue_privilegiee().posees
    d = influences(posees, config.familles)
    occasions = sum(etat.tours_restants(j) for j in range(config.joueurs))
    circulantes = _circulantes(etat)

    resultat: set[int] = set()
    for famille in range(config.familles):
        courant = statut(d[famille])
        if courant == 0:
            continue  # Indifferente : la moindre carte la fait bouger.
        valeurs = sorted(
            (valeur(c.role) for c in circulantes if c.famille == famille), reverse=True
        )
        posable = sum(valeurs[:occasions])
        cote = Position.ESTIME if courant == LUMIERE else Position.DISGRACE
        tuable = sum(
            valeur(posee.carte.role)
            for posee in posees
            if posee.carte.famille == famille
            and posee.zone.genre is GenreZone.BANQUET
            and posee.zone.position is cote
            and posee.carte.role not in ROLES_IMMUNISES_CONTRE_ASSASSIN
        )
        amplitude = posable + tuable
        if courant == LUMIERE and d[famille] - amplitude >= 1:
            resultat.add(famille)
        elif courant == OBSCURITE and d[famille] + amplitude <= -1:
            resultat.add(famille)
    return frozenset(resultat)


def _d_visible(etat: State, joueur: int) -> dict[int, int]:
    """`d` par famille tel que `joueur` peut le calculer : ses connues seulement."""
    vue = vue_legale(etat, joueur)
    return influences(vue.connues, etat.config.familles)


def _dos_banquet(etat: State, joueur: int) -> int:
    """Combien de dos adverses `joueur` voit au banquet."""
    return sum(
        1 for dos in vue_legale(etat, joueur).dos if dos.zone.genre is GenreZone.BANQUET
    )


def jouer(
    engine: Engine,
    seed: int,
    politiques: Sequence[Politique],
) -> Trace:
    """Joue une partie et rend sa trace. `politiques[i]` occupe le siege `i`."""
    config = engine.config
    if len(politiques) != config.joueurs:
        raise ValueError(
            f"{len(politiques)} politiques pour {config.joueurs} sieges"
        )
    etat = engine.reset(seed)
    trace = Trace(
        seed=seed,
        config_familles=config.familles,
        joueurs=config.joueurs,
        tours=config.tours,
    )
    index = 0
    tour = 0
    poses_du_tour = 0
    while not etat.is_terminal():
        joueur = etat.current_player()
        dieu = etat.vue_privilegiee()
        if etat.phase() is Phase.POSE:
            avant = dict(influences(dieu.posees, config.familles))
            visible = _d_visible(etat, joueur)
            dos = _dos_banquet(etat, joueur)
            expose = _expose(dieu.posees, joueur)
            expose_visible = _expose(vue_legale(etat, joueur).connues, joueur)
            imprenables = _imprenables(etat)
            action = politiques[joueur].action(etat)
            etat.apply(action)
            nouvelles = etat.vue_privilegiee().posees[len(dieu.posees) :]
            banquet = next(
                p for p in nouvelles if p.zone.genre is GenreZone.BANQUET
            )
            propre = next(
                p
                for p in nouvelles
                if p.zone.genre is GenreZone.DOMAINE
                and p.zone.proprietaire == joueur
            )
            adverse = next(
                p
                for p in nouvelles
                if p.zone.genre is GenreZone.DOMAINE
                and p.zone.proprietaire != joueur
            )
            trace.poses.append(
                EvenementPose(
                    index=index,
                    tour=tour,
                    joueur=joueur,
                    destinataire=adverse.zone.proprietaire,
                    banquet=banquet,
                    propre=propre,
                    adverse=adverse,
                    d_avant=avant,
                    d_visible_avant=visible,
                    dos_adverses_banquet=dos,
                    expose_avant=expose,
                    expose_visible_avant=expose_visible,
                    imprenables_avant=imprenables,
                )
            )
            poses_du_tour += 1
            if poses_du_tour == config.joueurs:
                poses_du_tour = 0
                tour += 1
        else:
            assassin = etat.assassin_en_resolution()
            cibles = etat.cibles_courantes()
            avant = dict(influences(dieu.posees, config.familles))
            refus_index = len(cibles)
            ecart_refus = _ecart_apres(etat, refus_index, joueur)
            ecarts = tuple(_ecart_apres(etat, i, joueur) for i in range(len(cibles)))
            action = politiques[joueur].action(etat)
            etat.apply(action)
            trace.ciblages.append(
                EvenementCiblage(
                    index=index,
                    tour=tour,
                    joueur=joueur,
                    assassin=assassin,
                    cibles=cibles,
                    victime=None if action == refus_index else cibles[action],
                    refus=action == refus_index,
                    ecart_si_refus=ecart_refus,
                    ecarts_si_meurtre=ecarts,
                    d_avant=avant,
                )
            )
        index += 1

    finales = etat.vue_privilegiee().posees
    trace.statuts_finaux = statuts(finales, config.familles)
    trace.scores_finaux = scores(finales, config.familles, config.joueurs)
    trace.gains_finaux = gains(trace.scores_finaux)
    return trace


def _ecart_apres(etat: State, action: int, joueur: int) -> int:
    """L'ecart **reel** du joueur si cette action de ciblage etait jouee.

    Vue analyste : tous les Espions comptent, y compris ceux que le tueur ne voit pas.
    C'est ce qui permet de dire si un refus etait justifie, et non seulement s'il etait
    coherent avec la croyance du tueur.
    """
    suivant = etat.clone()
    suivant.apply(action)
    posees = suivant.vue_privilegiee().posees
    bruts = scores(posees, etat.config.familles, etat.config.joueurs)
    return ecart(bruts, joueur)


def restreindre(trace: Trace, sieges: Sequence[int]) -> Trace:
    """La meme trace, reduite aux decisions de `sieges`.

    Indispensable des qu'une table est mixte : « la frequence de B4 chez le greedy » ne
    veut rien dire si le denominateur compte aussi les noeuds de ciblage de ses
    adversaires. L'issue de la partie -- statuts, scores, gains -- est conservee telle
    quelle : elle appartient a la partie, pas a un siege.
    """
    retenus = set(sieges)
    for siege in retenus:
        if not 0 <= siege < trace.joueurs:
            raise ValueError(f"siege {siege} inexistant")
    reduite = Trace(
        seed=trace.seed,
        config_familles=trace.config_familles,
        joueurs=trace.joueurs,
        tours=trace.tours,
        poses=[p for p in trace.poses if p.joueur in retenus],
        ciblages=[c for c in trace.ciblages if c.joueur in retenus],
    )
    reduite.statuts_finaux = dict(trace.statuts_finaux)
    reduite.scores_finaux = list(trace.scores_finaux)
    reduite.gains_finaux = list(trace.gains_finaux)
    return reduite
