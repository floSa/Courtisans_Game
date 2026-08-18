"""Fabrique de `Perception` **ecrites a la main**, pour les positions ou la regle tranche.

Le greedy ne recoit jamais un `State` : sa decision est une fonction d'une `Perception`
(paragraphe 5.5 de `mesure/phase2_hypothese_et_instrument.md`). Une position ou son coup est
determine par sa regle s'ecrit donc directement comme une `Perception`, sans faire tourner le
moteur -- ce qui est le seul moyen de controler exactement ce qu'il voit, et de calculer son
ecart de tete.

Un test d'integration a travers une vraie partie existe par ailleurs
(`test_perception.py`) : celui-la verifie que `percevoir` construit bien une `Perception`
conforme depuis un `State`. Les deux sont necessaires et ne se remplacent pas.
"""

from __future__ import annotations

from collections.abc import Sequence

from courtisans.cards import Carte, CartePosee, Position, Role, Zone
from courtisans.config import GameConfig
from courtisans.engine import Phase
from mesure.instance import ENTRAINEMENT_3J


def carte(famille: int, role: Role, exemplaire: int = 0) -> Carte:
    """Raccourci de lecture, pour que les positions construites tiennent sur une ligne."""
    return Carte(famille, role, exemplaire)


def au_banquet(
    famille: int, role: Role, position: Position, poseur: int, exemplaire: int = 0
) -> CartePosee:
    """Une carte posee au banquet, en Estime ou en Disgrace.

    `exemplaire` distingue deux cartes de meme famille et meme role. L'omettre sur deux
    cartes identiques construit un plateau **impossible**, que `perception_de_ciblage`
    refuse.
    """
    return CartePosee(carte(famille, role, exemplaire), Zone.banquet(position), poseur)


def au_domaine(
    famille: int, role: Role, proprietaire: int, poseur: int, exemplaire: int = 0
) -> CartePosee:
    """Une carte posee dans un domaine. Le proprietaire encaisse, le poseur non."""
    return CartePosee(carte(famille, role, exemplaire), Zone.domaine(proprietaire), poseur)


def perception_de_ciblage(
    connues: Sequence[CartePosee],
    assassin: CartePosee,
    cibles_connues: Sequence[CartePosee],
    dos_cibles: int = 0,
    moi: int = 0,
    config: GameConfig = ENTRAINEMENT_3J,
):
    """Une `Perception` en phase CIBLAGE, coherente par construction.

    `cibles_connues` sont les cibles dont le greedy connait l'identite ; `dos_cibles` en
    ajoute autant de dos qu'on veut, qu'il ne peut pas identifier. Les actions legales sont
    `0 … nb_cibles - 1` pour tuer, puis `nb_cibles` pour refuser -- exactement ce que rend
    `State.legal_actions()` en ciblage (controle C15).

    Import differe de `agents` : tant que le paquet n'existe pas, chaque test echoue
    individuellement au lieu d'empecher la collecte de toute la suite (principe 1 de
    `tests/outils.py`).

    Raises:
        ValueError: si deux cartes du plateau sont **la meme carte**. Une `Carte` porte son
            exemplaire, donc elle est unique dans une partie : un plateau qui la contient
            deux fois est impossible, et ce garde-fou existe parce que son absence a produit
            une position illegale sur laquelle un attendu calcule a la main etait faux.
    """
    from agents.perception import CibleVue, Perception

    identites = [posee.carte for posee in connues]
    doublons = {carte for carte in identites if identites.count(carte) > 1}
    if doublons:
        raise ValueError(
            f"plateau impossible : {sorted(doublons)} apparaissent deux fois. Une Carte "
            f"porte son exemplaire et n'existe qu'une fois par partie -- varier "
            f"`exemplaire` distingue deux cartes de meme famille et meme role."
        )

    cibles: list[CibleVue] = []
    for indice, cible in enumerate(cibles_connues):
        cibles.append(
            CibleVue(indice=indice, carte=cible.carte, zone=cible.zone, rang_public=indice + 1)
        )
    for numero in range(dos_cibles):
        cibles.append(
            CibleVue(
                indice=len(cibles),
                carte=None,
                zone=assassin.zone,
                rang_public=numero + 1,
            )
        )
    return Perception(
        config=config,
        moi=moi,
        phase=Phase.CIBLAGE,
        connues=tuple(connues),
        dos_par_zone={},
        main=(),
        tours_restants=tuple(config.tours for _ in range(config.joueurs)),
        actions_legales=tuple(range(len(cibles) + 1)),
        assassin=assassin,
        cibles=tuple(cibles),
    )
