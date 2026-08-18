"""Outillage de l'auditeur pour fabriquer une partie a la main.

`reset_depuis_pioche` exige le paquet **entier**, dans l'ordre voulu. Ce module traduit
« je veux que J0 ait ces trois cartes au tour 1 » en un ordre de pioche legal, et
« je veux poser cette carte-la au banquet en Disgrace » en un numero d'action.

Rien ici ne calcule un statut : c'est le role de `audit.statut`.
"""

from __future__ import annotations

from collections.abc import Sequence

from courtisans import rules
from courtisans.cards import Carte, Position, Role
from courtisans.config import CARTES_PAR_TOUR, GameConfig
from courtisans.engine import Engine, Phase, State


def carte(famille: int, role: Role, exemplaire: int = 0) -> Carte:
    """Raccourci de lecture pour les cas construits a la main."""
    return Carte(famille, role, exemplaire)


def pioche_avec_debut(config: GameConfig, debut: Sequence[Carte]) -> tuple[Carte, ...]:
    """Le paquet entier, commencant par `debut`, le reste dans l'ordre canonique.

    Les `3` premieres cartes vont a J0, les trois suivantes a J1, etc. (regle R-b du
    moteur). Leve si `debut` contient une carte qui n'est pas dans le paquet, ou deux fois
    la meme : sans ce controle je pourrais fabriquer un etat impossible et le certifier.
    """
    complet = list(rules.paquet(config))
    restant = list(complet)
    for c in debut:
        if c not in restant:
            raise ValueError(f"{c} n'est pas disponible dans le paquet (ou deja utilisee)")
        restant.remove(c)
    return (*debut, *restant)


def action_de_pose(
    etat: State,
    au_banquet: Carte,
    position: Position,
    chez_soi: Carte | None = None,
    chez_adversaire: Carte | None = None,
) -> int:
    """L'action legale qui pose `au_banquet` a la position dite, et rien d'autre d'impose.

    Cherche parmi les actions **legales** celle dont le decodage envoie `au_banquet` au
    banquet a la bonne position -- et, si elles sont donnees, `chez_soi` dans son propre
    domaine et `chez_adversaire` chez l'adversaire. Leve si aucune ne correspond : un cas
    construit dont l'action n'existe pas est un cas mal construit, et il doit echouer
    bruyamment plutot que de mesurer autre chose que ce que j'ai voulu.
    """
    if etat.phase() is not Phase.POSE:
        raise ValueError(f"phase {etat.phase().name}, une pose n'est pas possible ici")
    main = etat.vue_privilegiee().mains[etat.current_player()]
    if len(main) != CARTES_PAR_TOUR:
        raise ValueError(f"main de {len(main)} cartes, {CARTES_PAR_TOUR} attendues")
    for action in etat.legal_actions():
        pose = rules.decoder_action_pose(action, etat.config)
        if pose.position is not position:
            continue
        if main[pose.indices_main[0]] != au_banquet:
            continue
        if chez_soi is not None and main[pose.indices_main[1]] != chez_soi:
            continue
        if chez_adversaire is not None and main[pose.indices_main[2]] != chez_adversaire:
            continue
        return action
    raise ValueError(
        f"aucune action legale ne pose {au_banquet} au banquet en {position.name} "
        f"(main = {list(main)})"
    )


def politique_scriptee(
    scripts: Sequence[tuple],
    cible_a_tuer: dict[int, Carte] | None = None,
) -> object:
    """Une politique qui suit un script de poses, et refuse de tuer sauf ordre contraire.

    Chaque element de `scripts` decrit une pose : `(carte_banquet, position)`, ou
    `(carte_banquet, position, chez_soi)`, ou `(carte_banquet, position, chez_soi,
    chez_adversaire)`. Une fois le script epuise, la premiere action legale est jouee.

    `cible_a_tuer` associe un numero de noeud de ciblage (a partir de 1) a la carte que
    l'Assassin doit tuer. Tout noeud absent de cette table est un refus : c'est le defaut
    volontaire, pour qu'un meurtre non demande ne vienne jamais deplacer un `d`.
    """
    etat_compteurs = {"pose": 0, "ciblage": 0}
    a_tuer = cible_a_tuer or {}

    def choisir(etat: State) -> int:
        if etat.phase() is Phase.CIBLAGE:
            etat_compteurs["ciblage"] += 1
            voulue = a_tuer.get(etat_compteurs["ciblage"])
            if voulue is not None:
                for indice, cible in enumerate(etat.cibles_courantes()):
                    if cible.carte == voulue:
                        return indice
                raise ValueError(
                    f"noeud de ciblage {etat_compteurs['ciblage']} : {voulue} n'est pas "
                    f"une cible valide ({[c.carte for c in etat.cibles_courantes()]})"
                )
            return refus(etat)
        indice = etat_compteurs["pose"]
        etat_compteurs["pose"] += 1
        if indice >= len(scripts):
            return etat.legal_actions()[0]
        return action_de_pose(etat, *scripts[indice])

    return choisir


def refus(etat: State) -> int:
    """L'action « ne pas tuer » : l'indice `len(cibles)` (paragraphe 4.1)."""
    if etat.phase() is not Phase.CIBLAGE:
        raise ValueError(f"phase {etat.phase().name}, aucun Assassin a resoudre")
    return len(etat.cibles_courantes())


def joue_jusqu_a_la_fin(etat: State, engine: Engine) -> None:
    """Termine la partie par la premiere action legale, refus systematique en ciblage.

    Sert a fermer un cas construit une fois l'evenement interessant produit : la partie
    doit aller au bout, parce que le decompte ne se lit qu'a la fin.
    """
    while not etat.is_terminal():
        etat.apply(
            refus(etat) if etat.phase() is Phase.CIBLAGE else etat.legal_actions()[0]
        )
