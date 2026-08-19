"""Fabrique de traces **ecrites a la main**, pour tester les sept compteurs.

Chacun des sept compteurs produit un chiffre qui servira de ligne de base a toutes les phases
suivantes. Un chiffre dont personne ne peut verifier le calcul n'est pas un resultat : c'est la
faute qui a coute trois mois au projet. On teste donc chaque compteur sur une trace dont **on
ecrit soi-meme chaque nœud**, et dont on calcule le resultat de tete, sans faire tourner le
moteur pour obtenir l'attendu.

Pourquoi une trace ecrite et non une partie scriptee. `tests/mesure/scenario.py` sait forcer la
carte du banquet a chaque tour, ce qui suffisait au compteur de retournements de la phase 1.
B1, B3 et B5 ont besoin de forcer aussi **la carte donnee a l'adversaire**, la **main**, et les
**dos deja poses** : le script du banquet ne les atteint pas. Une trace ecrite les fixe tous.

Un test d'integration a travers de vraies parties existe par ailleurs -- il verifie que `tracer`
produit une trace coherente. Les deux sont necessaires et ne se remplacent pas.

**Garde-fou.** `pose` et `ciblage` refusent un plateau contenant deux fois la meme carte. Une
`Carte` porte son exemplaire, donc elle est unique dans une partie ; l'omission de ce controle,
dans les tests du greedy, a produit une position illegale sur laquelle un attendu calcule a la
main etait faux.
"""

from __future__ import annotations

from collections.abc import Sequence

from courtisans.cards import Carte, CartePosee, Position, Role, Zone
from courtisans.config import GameConfig
from courtisans.engine import Phase
from courtisans.rules import Statut, statuts
from mesure.instance import ENTRAINEMENT_3J
from mesure.trace import Decision, TracePartie

CONFIG: GameConfig = ENTRAINEMENT_3J


def carte(famille: int, role: Role, exemplaire: int = 0) -> Carte:
    """Raccourci de lecture."""
    return Carte(famille, role, exemplaire)


def banquet(
    famille: int, role: Role, position: Position, poseur: int, exemplaire: int = 0
) -> CartePosee:
    """Une carte au banquet."""
    return CartePosee(carte(famille, role, exemplaire), Zone.banquet(position), poseur)


def domaine(
    famille: int, role: Role, proprietaire: int, poseur: int, exemplaire: int = 0
) -> CartePosee:
    """Une carte dans un domaine. Le proprietaire encaisse, le poseur non."""
    return CartePosee(carte(famille, role, exemplaire), Zone.domaine(proprietaire), poseur)


def _refuser_les_doublons(*groupes: Sequence[CartePosee]) -> None:
    """Leve si une meme carte apparait deux fois dans l'ensemble des groupes."""
    identites = [posee.carte for groupe in groupes for posee in groupe]
    doublons = sorted({c for c in identites if identites.count(c) > 1})
    if doublons:
        raise ValueError(
            f"plateau impossible : {doublons} apparaissent deux fois. Une Carte porte son "
            f"exemplaire et n'existe qu'une fois par partie."
        )


def pose(
    numero: int,
    joueur: int,
    tour: int,
    cartes: Sequence[CartePosee],
    connues: Sequence[CartePosee] = (),
    posees: Sequence[CartePosee] | None = None,
    main: Sequence[Carte] = (),
    mortes: Sequence[Carte] = (),
    tours_restants: tuple[int, ...] | None = None,
) -> Decision:
    """Un nœud de POSE ecrit a la main.

    `cartes` est dans l'ordre **banquet, domaine propre, domaine adverse** -- l'ordre du
    paragraphe 3.2, qui est aussi celui de resolution des Assassins. `posees` par defaut vaut
    `connues` : la verite et la vue coincident tant qu'on n'ajoute pas de dos.

    `action` vaut `0` : aucun compteur ne le lit, ils lisent `cartes_posees`. Le mettre a une
    valeur plausible ferait croire qu'il porte du sens.
    """
    if len(cartes) != 3:
        raise ValueError(f"une pose place 3 cartes, {len(cartes)} recue(s)")
    verite = tuple(connues) if posees is None else tuple(posees)
    _refuser_les_doublons(verite, cartes)
    return Decision(
        numero=numero,
        joueur=joueur,
        phase=Phase.POSE,
        tour=tour,
        action=0,
        main=tuple(main),
        connues=tuple(connues),
        posees=verite,
        mortes=tuple(mortes),
        tours_restants=tours_restants or (CONFIG.tours,) * CONFIG.joueurs,
        cartes_posees=tuple(cartes),
        destinataire=cartes[2].zone.proprietaire,
    )


def ciblage(
    numero: int,
    joueur: int,
    tour: int,
    cibles_connues: Sequence[CartePosee],
    dos_cibles: int,
    valeurs: dict[int, int],
    action: int,
    connues: Sequence[CartePosee] = (),
    posees: Sequence[CartePosee] | None = None,
    tours_restants: tuple[int, ...] | None = None,
    assassins_en_attente: Sequence[CartePosee] = (),
) -> Decision:
    """Un nœud de CIBLAGE ecrit a la main.

    `valeurs` est l'ecart evalue de chaque action, ecrit a la main : c'est ce que B4 lit pour
    dire si un refus etait strict, a egalite, ou moins bon. Le fixer ici plutot que de le
    calculer rend l'attendu de B4 verifiable sans faire tourner le greedy.

    Les actions `0 .. nb_cibles - 1` tuent, l'action `nb_cibles` refuse (controle C15).

    `assassins_en_attente` sont les Assassins du meme bloc qui se resoudront **apres** celui-ci.
    Le decideur ne les voit pas -- c'est ce qui rend son ciblage myope --, et
    `mesure/coherence_greedy.py` s'en sert pour mesurer cette myopie.
    """
    from agents.perception import CibleVue

    cibles: list[CibleVue] = []
    for indice, cible in enumerate(cibles_connues):
        cibles.append(CibleVue(indice, cible.carte, cible.zone, indice + 1))
    zone = cibles_connues[0].zone if cibles_connues else Zone.banquet(Position.ESTIME)
    for numero_dos in range(dos_cibles):
        cibles.append(CibleVue(len(cibles), None, zone, numero_dos + 1))
    attendues = set(range(len(cibles) + 1))
    if set(valeurs) != attendues:
        raise ValueError(
            f"`valeurs` doit couvrir exactement {sorted(attendues)} -- "
            f"{len(cibles)} cibles plus le refus -- et non {sorted(valeurs)}"
        )
    verite = tuple(connues) if posees is None else tuple(posees)
    _refuser_les_doublons(verite)
    tuee = cibles_connues[action] if action < len(cibles_connues) else None
    return Decision(
        numero=numero,
        joueur=joueur,
        phase=Phase.CIBLAGE,
        tour=tour,
        action=action,
        main=(),
        connues=tuple(connues),
        posees=verite,
        mortes=(),
        tours_restants=tours_restants or (CONFIG.tours,) * CONFIG.joueurs,
        cibles=tuple(cibles),
        assassins_en_attente=tuple(assassins_en_attente),
        tuee=tuee,
        valeurs=dict(valeurs),
    )


def trace(
    decisions: Sequence[Decision],
    posees_finales: Sequence[CartePosee] = (),
    scores: tuple[int, ...] = (0, 0, 0),
    seed: int | None = 0,
    replicat: int = 0,
) -> TracePartie:
    """Une trace de partie ecrite a la main.

    `statuts_finaux` est **calcule** par `rules.statuts` sur `posees_finales`, et non ecrit :
    c'est la seule quantite de cette fabrique qu'on ne veut pas pouvoir se tromper en
    recopiant, puisque B1 en depend. Les tests verifient a cote que le statut vaut bien ce
    qu'ils ont calcule de tete.
    """
    _refuser_les_doublons(posees_finales)
    return TracePartie(
        seed=seed,
        replicat=replicat,
        decisions=tuple(decisions),
        scores=scores,
        gains=(0.0, 0.0, 0.0),
        posees_finales=tuple(posees_finales),
        statuts_finaux=statuts(posees_finales, CONFIG.familles),
        duree_s=0.0,
    )


def statut_de(posees: Sequence[CartePosee], famille: int) -> Statut:
    """Le statut d'une famille sur un plateau, pour que les tests l'assertent explicitement."""
    return statuts(posees, CONFIG.familles)[famille]
