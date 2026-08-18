"""Ce qu'un joueur sait d'un etat, et rien de plus. **Le seul module qui touche un `State`.**

`Perception` est la frontiere. Tout ce qui decide -- `greedy.py` -- n'en recoit que ceci, donc
ne peut pas lire la pioche, les mains adverses, l'identite des Espions adverses, `scores()` ni
`returns()`. L'aveuglement n'est pas une discipline a tenir, c'est une consequence de la
signature.

Ce qui entre, et pourquoi c'est legitime
----------------------------------------
`connues` : les faces visibles, plus ses propres Espions. C'est exactement
`infoset._vue_du_joueur`, le support de `information_state_string`, tenu par l'invariant I7.

`dos_par_zone` : le **nombre** de dos par zone et par poseur, jamais leur identite. « Leur
position est connue » (paragraphe 2.6 des regles).

`main` : la sienne. `tours_restants` : information publique (paragraphe 2.6).

`actions_legales` : savoir commun -- tous les etats d'un meme info-set exposent le meme
ensemble d'actions legales (controle C17).

`assassin` et `cibles` : un Assassin est pose **face visible** et ouvre son noeud
publiquement. Chaque cible porte son apparence **publique** -- `None` pour un dos --, sa zone
et son rang public.

Le rang public d'une cible ne fuite rien : `rules.rang_public_dans_zone` le calcule sur
l'ordre de pose et sur « encore en jeu », tous deux publics, et sa docstring le demontre. C'est
l'arbitrage du 17/08 -- un dos n'est jamais nomme, il est situe et numerote.

Ce qui n'entre pas
------------------
La pioche, les mains adverses, l'identite des dos adverses, `scores()`, `returns()`, et le
resultat brut de `State.cibles_courantes()` -- qui rend de vrais `CartePosee`, identite des dos
comprise. **C'est ici que la redaction a lieu**, et nulle part ailleurs.

Un import prive, assume
-----------------------
`infoset._vue_du_joueur` est prive. L'appeler plutot que de reecrire son predicat est un choix :
« un Espion pose face cachee n'est connu que de son poseur » est une **regle** (paragraphe 4.2),
et la reecrire ici serait exactement la duplication que le paragraphe 2 des conventions
interdit -- deux definitions finissent par ne plus etre d'accord. Le paquet `courtisans` n'est
pas modifie pour rendre ce nom public : ce serait toucher a un module audite deux fois pour la
commodite d'un appelant.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from courtisans.cards import Carte, CartePosee, Zone
from courtisans.config import GameConfig
from courtisans.engine import Phase, State
from courtisans.infoset import _vue_du_joueur


@dataclass(frozen=True)
class CibleVue:
    """Une cible d'Assassin, telle que le decideur la voit.

    Attributes:
        indice: l'indice de l'action qui tue cette cible. `len(cibles)` est le refus.
        carte: son identite si le decideur la connait -- face visible, ou son propre Espion
            --, **`None` pour un dos qu'il ne peut pas identifier**.
        zone: la zone de la cible, donc celle de l'Assassin. Publique.
        rang_public: son rang parmi les cartes de meme apparence de sa zone, a partir de 1.
    """

    indice: int
    carte: Carte | None
    zone: Zone
    rang_public: int


@dataclass(frozen=True)
class Perception:
    """Tout ce que le decideur sait, au moment ou il decide.

    Gele : `greedy` ne doit pas pouvoir la rebrancher sur autre chose. Les deux champs
    associatifs restent des `dict` -- geler la structure interdirait le rebinding, pas la
    mutation, et une copie defensive a chaque decision couterait plus qu'elle ne protege.
    Aucune fonction de `greedy` n'ecrit dedans.

    Attributes:
        config: la configuration de la partie. Publique.
        moi: le siege du decideur.
        phase: POSE ou CIBLAGE.
        connues: les cartes posees **vivantes** dont il connait l'identite.
        dos_par_zone: nombre de dos adverses par `(zone, poseur)`. Le compte est public,
            l'identite non.
        main: sa main, dans l'ordre canonique du decodage d'action (contrat R-b/R-c).
        tours_restants: tours restants de chaque siege, indexe en absolu.
        actions_legales: les actions legales de la phase courante.
        assassin: l'Assassin en resolution, ou `None` hors ciblage. Face visible.
        cibles: ses cibles, redigees. Vide hors ciblage.
    """

    config: GameConfig
    moi: int
    phase: Phase
    connues: tuple[CartePosee, ...]
    main: tuple[Carte, ...]
    tours_restants: tuple[int, ...]
    actions_legales: tuple[int, ...]
    assassin: CartePosee | None = None
    cibles: tuple[CibleVue, ...] = ()
    dos_par_zone: dict[tuple[Zone, int], int] = field(default_factory=dict)


def percevoir(etat: State, joueur: int) -> Perception:
    """Traduit un etat en ce que `joueur` en sait.

    **Appelee AVANT la decision, et hors d'elle** : c'est ce qui permet a la preuve P2 de
    remplacer `State.vue_privilegiee` par une fonction qui leve pendant tout l'appel a
    `greedy.choisir`. Si la perception se construisait paresseusement, la preuve n'aurait
    plus de sens.

    Raises:
        ValueError: si l'etat est terminal ou sur un noeud de chance. Un agent n'y decide
            rien, et rendre une `Perception` vide masquerait un pilote de partie fautif.
    """
    if etat.phase() in (Phase.TERMINAL, Phase.CHANCE):
        raise ValueError(
            f"un agent ne decide pas en phase {etat.phase().name} : "
            f"le pilote de partie ne doit pas l'y appeler"
        )
    vue = _vue_du_joueur(etat, joueur)

    dos: dict[tuple[Zone, int], int] = {}
    for posee in vue.dos_adverses:
        cle = (posee.zone, posee.poseur)
        dos[cle] = dos.get(cle, 0) + 1

    cibles: list[CibleVue] = []
    if etat.phase() is Phase.CIBLAGE:
        for indice, cible in enumerate(etat.cibles_courantes()):
            # La redaction est ici, et nulle part ailleurs : une carte dont le decideur ne
            # connait pas l'identite entre avec `carte=None`.
            #
            # Le predicat porte sur la carte **posee** et non sur son identite : « cette
            # carte-la est-elle dans ce que je connais ». Tester `cible.carte in {identites}`
            # serait equivalent dans une partie legale -- une `Carte` est unique -- mais se
            # laisserait tromper par un plateau contenant deux fois la meme carte, ce qui est
            # exactement ce que le brouilleur de P3 fabriquait par erreur.
            connue = cible in vue.connues
            cibles.append(
                CibleVue(
                    indice=indice,
                    carte=cible.carte if connue else None,
                    zone=cible.zone,
                    rang_public=etat.rang_public_de_cible(cible),
                )
            )

    return Perception(
        config=etat.config,
        moi=joueur,
        phase=etat.phase(),
        connues=vue.connues,
        main=tuple(etat.vue_privilegiee().mains[joueur]),
        tours_restants=tuple(
            etat.tours_restants(siege) for siege in range(etat.config.joueurs)
        ),
        actions_legales=tuple(etat.legal_actions()),
        assassin=etat.assassin_en_resolution(),
        cibles=tuple(cibles),
        dos_par_zone=dos,
    )
