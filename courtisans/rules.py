"""Les regles, en fonctions pures.

Aucune de ces fonctions ne lit ni ne modifie d'etat : elles prennent ce qu'on leur donne et
rendent un resultat. C'est ce qui permet de les tester sur un cas construit a la main, ou
l'attendu se calcule de tete, sans jouer de partie.

**Aucune heuristique ici, et nulle part ailleurs dans le moteur.** L'ancien `app/jeu.py`
contenait un `_pick_target_heuristic` -- une IA au milieu des regles -- qui ne rendait
`None` que si la liste de cibles etait vide : aucune politique du projet n'a donc jamais
refuse de tuer, alors que le moteur le permettait. Une regle du jeu a ete perdue parce
qu'une IA vivait dans le fichier des regles.

**Tout se compte en valeur, jamais en nombre de cartes** (paragraphe 5.1). Le Noble pese 2,
tous les autres roles pesent 1, au banquet comme dans les domaines.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import IntEnum
from itertools import permutations

from courtisans.cards import Carte, CartePosee, GenreZone, Position, Role
from courtisans.config import CARTES_PAR_TOUR, GameConfig

#: Roles qu'un Assassin ne peut pas tuer (paragraphe 4.3). Le Garde est immunise ; il
#: verrouille donc une valeur d'influence qu'aucun Assassin ne peut retirer.
ROLES_IMMUNISES_CONTRE_ASSASSIN: frozenset[Role] = frozenset({Role.GARDE})

#: Roles qui ouvrent un noeud de ciblage quand ils sont poses (paragraphe 4.1). Ecrit ici
#: et nulle part ailleurs : le moteur ne doit pas avoir sa propre idee de ce qu'est un
#: Assassin.
ROLES_ASSASSINS: frozenset[Role] = frozenset({Role.ASSASSIN})

#: Les `3!` facons d'assigner les trois cartes de la main aux trois zones. L'ordre est
#: celui d'`itertools.permutations`, donc fixe : il fait partie du decodage des actions.
ASSIGNATIONS: tuple[tuple[int, ...], ...] = tuple(permutations(range(CARTES_PAR_TOUR)))


class Statut(IntEnum):
    """Statut d'une famille au decompte (paragraphe 5.1).

    La valeur entiere **est** le signe applique aux points : une carte d'une famille en
    Obscurite retire sa valeur au proprietaire du domaine, une carte d'une famille
    Indifferente ne rapporte rien.
    """

    OBSCURITE = -1
    INDIFFERENTE = 0
    LUMIERE = 1


@dataclass(frozen=True)
class ActionPose:
    """Une action de pose decodee.

    Attributes:
        indices_main: les indices des cartes de la main canonique, dans l'ordre
            banquet, domaine propre, domaine d'un adversaire.
        position: Estime ou Disgrace, pour la carte du banquet.
        adversaire_relatif: qui recoit la troisieme carte, compte a partir du joueur
            suivant. 0 est le joueur suivant, 1 celui d'apres.
    """

    indices_main: tuple[int, ...]
    position: Position
    adversaire_relatif: int


# ---------------------------------------------------------------------------------
# Le paquet et la main
# ---------------------------------------------------------------------------------


def paquet(config: GameConfig) -> tuple[Carte, ...]:
    """Le paquet complet, dans un ordre deterministe (paragraphe 3.1).

    On joue toujours avec toutes les cartes : aucune n'est retiree avant le melange.
    """
    return tuple(
        Carte(famille, role, exemplaire)
        for famille in range(config.familles)
        for role in config.roles
        for exemplaire in range(config.exemplaires)
    )


def main_canonique(cartes: Iterable[Carte]) -> tuple[Carte, ...]:
    """La main triee par (famille, role, exemplaire).

    Sans cet ordre, une action de pose designerait des cartes differentes selon l'etat :
    l'encodage cesserait d'etre markovien et ni CFR ni l'apprentissage par renforcement
    n'auraient plus de garantie (03_specification_moteur.md paragraphe 4.2). L'exemplaire
    ne departage que des cartes interchangeables ; il ne sert qu'au determinisme.
    """
    return tuple(sorted(cartes))


# ---------------------------------------------------------------------------------
# Les actions de pose -- paragraphe 3.2
# ---------------------------------------------------------------------------------


def decoder_action_pose(action: int, config: GameConfig) -> ActionPose:
    """Decode une action de pose en assignation, position au banquet et adversaire.

    Numeration a base mixte : l'adversaire varie le plus vite, puis la position, puis
    l'assignation. La bijection est verifiee par le test de conformite C14.
    """
    if not 0 <= action < config.actions_de_pose:
        raise ValueError(
            f"action de pose {action} hors de l'espace [0, {config.actions_de_pose})"
        )
    reste, adversaire = divmod(action, config.joueurs - 1)
    assignation, position = divmod(reste, len(Position))
    return ActionPose(ASSIGNATIONS[assignation], Position(position), adversaire)


def actions_de_pose_legales(
    main: Sequence[Carte], config: GameConfig
) -> tuple[int, ...]:
    """Les actions de pose qui ne font pas double emploi, pour cette main.

    Deux cartes de meme famille et de meme role sont **interchangeables** : meme valeur,
    meme visibilite, meme effet. Deux actions qui ne different que par laquelle des deux
    va ou posent le meme coup ; l'une des deux est masquee, sinon le test C14 echoue.
    C'est le cas des mains contenant un doublon, environ 7 % des tours a 3 exemplaires.
    """
    if len(main) != CARTES_PAR_TOUR:
        raise ValueError(
            f"une pose consomme {CARTES_PAR_TOUR} cartes, main de {len(main)} recue"
        )
    representantes: dict[tuple, int] = {}
    for action in range(config.actions_de_pose):
        pose = decoder_action_pose(action, config)
        contenu = (
            tuple((main[indice].famille, main[indice].role) for indice in pose.indices_main),
            pose.position,
            pose.adversaire_relatif,
        )
        representantes.setdefault(contenu, action)
    return tuple(sorted(representantes.values()))


def destinataire(joueur: int, adversaire_relatif: int, joueurs: int) -> int:
    """Le joueur qui recoit la carte, a partir d'un indice relatif.

    Indexation relative : 0 est le joueur suivant, 1 celui d'apres. Un joueur ne peut
    jamais se designer lui-meme.
    """
    if not 0 <= adversaire_relatif < joueurs - 1:
        raise ValueError(
            f"adversaire relatif {adversaire_relatif} hors de [0, {joueurs - 1})"
        )
    return (joueur + 1 + adversaire_relatif) % joueurs


# ---------------------------------------------------------------------------------
# L'Assassin -- paragraphe 4.1
# ---------------------------------------------------------------------------------


def cibles_valides(
    cartes_vivantes: Iterable[CartePosee], assassin: CartePosee
) -> tuple[CartePosee, ...]:
    """Les cartes qu'un Assassin peut tuer : sa zone, Gardes exclus, lui-meme exclu.

    Il peut donc tuer un autre Assassin, un Neutre, un Noble, et un Espion visible ou
    cache. Le resultat peut etre vide ; il n'est **jamais** oblige de tuer, meme non vide
    -- le refus est une action a part entiere, gerée par `engine.py`.
    """
    return tuple(
        posee
        for posee in cartes_vivantes
        if posee.zone == assassin.zone
        and posee.carte.role not in ROLES_IMMUNISES_CONTRE_ASSASSIN
        and posee.carte != assassin.carte
    )


# ---------------------------------------------------------------------------------
# Le decompte -- paragraphe 5
# ---------------------------------------------------------------------------------


def influence(cartes_vivantes: Iterable[CartePosee], familles: int) -> dict[int, int]:
    """`d` par famille : valeurs en Estime moins valeurs en Disgrace, au banquet.

    Ne comptent que les cartes **vivantes** et **au banquet** : une carte de domaine ne
    change pas le statut de sa famille, une carte tuee ne compte nulle part.
    """
    influences = dict.fromkeys(range(familles), 0)
    for posee in cartes_vivantes:
        if posee.zone.genre is not GenreZone.BANQUET:
            continue
        signe = 1 if posee.zone.position is Position.ESTIME else -1
        influences[posee.carte.famille] += signe * posee.carte.valeur
    return influences


def statut_depuis_influence(valeur: int) -> Statut:
    """Lumiere si `d >= 1`, Obscurite si `d <= -1`, Indifferente si `d == 0`."""
    if valeur >= 1:
        return Statut.LUMIERE
    if valeur <= -1:
        return Statut.OBSCURITE
    return Statut.INDIFFERENTE


def statuts(cartes_vivantes: Iterable[CartePosee], familles: int) -> dict[int, Statut]:
    """Le statut de chaque famille. Une famille sans carte au banquet est Indifferente."""
    return {
        famille: statut_depuis_influence(valeur)
        for famille, valeur in influence(cartes_vivantes, familles).items()
    }


def points(
    cartes_vivantes: Iterable[CartePosee],
    statuts_par_famille: Mapping[int, Statut],
    joueurs: int,
) -> list[int]:
    """Les points bruts de chaque joueur.

    Le **proprietaire du domaine** est credite, jamais le poseur. Les cartes du banquet ne
    rapportent rien : elles ne servent qu'a determiner le statut des familles.
    """
    totaux = [0] * joueurs
    for posee in cartes_vivantes:
        if posee.zone.genre is not GenreZone.DOMAINE:
            continue
        statut = statuts_par_famille[posee.carte.famille]
        totaux[posee.zone.proprietaire] += int(statut) * posee.carte.valeur
    return totaux


def gains_depuis_scores(scores: Sequence[int]) -> list[float]:
    """La formule de gain du paragraphe 5.2, a somme nulle.

    Vainqueur unique : `+1`. `k` ex aequo : `+(n - k) / (k (n - 1))` chacun. Perdant :
    `-1 / (n - 1)`. Les egalites sont conservees, sans departage.
    """
    nb_joueurs = len(scores)
    if nb_joueurs < 2:
        raise ValueError(f"il faut au moins 2 joueurs, {nb_joueurs} score(s) recu(s)")
    meilleur = max(scores)
    nb_vainqueurs = sum(1 for score in scores if score == meilleur)
    gain = (nb_joueurs - nb_vainqueurs) / (nb_vainqueurs * (nb_joueurs - 1))
    perte = -1 / (nb_joueurs - 1)
    return [gain if score == meilleur else perte for score in scores]


# ---------------------------------------------------------------------------------
# La fin de partie -- paragraphe 3.4
# ---------------------------------------------------------------------------------


def peut_entamer_un_tour_de_table(taille_pioche: int, joueurs: int) -> bool:
    """Vrai s'il reste de quoi faire jouer **tous** les joueurs encore une fois.

    La partie s'arrete a la fin du dernier tour de table complet. Tester la fin joueur par
    joueur -- « le joueur courant a-t-il encore 3 cartes ? » -- est non conforme : les
    premiers de l'ordre joueraient alors un tour de plus.
    """
    return taille_pioche >= CARTES_PAR_TOUR * joueurs
