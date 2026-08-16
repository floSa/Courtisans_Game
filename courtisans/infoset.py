"""La vue d'un joueur : chaine et tenseur.

Ecrit d'apres le paragraphe 4.2 de `03_specification_moteur.md`, dont les quatre regles
non negociables corrigent chacune un defaut trouve par audit. C'est l'etape ou la
tentative precedente s'est fracassee.

Une seule observation, deux rendus
----------------------------------
`chaine` et `tenseur` sont deux serialisations **de la meme liste de blocs**. Aucune des
deux ne peut donc contenir ce que l'autre ignore : l'injectivite de l'encodage (C16, I8)
est vraie par construction, pas par vigilance. La disposition ne depend que de la
configuration, donc la taille du tenseur est constante.

Ce qu'un joueur sait, et rien de plus
--------------------------------------
Tout part de `_vue_du_joueur` : les cartes dont il connait l'identite -- les faces
visibles, plus ses propres Espions -- et les dos adverses, dont il ne connait que la
position et le poseur. **Aucune autre fonction de ce module ne touche au plateau reel.**

Trois pieges, dans l'ordre ou ils mordent :

1. **« visible » et « mes Espions » restent separes.** Fusionner les deux rend la vue
   publique non reconstructible : le joueur ne saurait plus ce que les autres voient,
   donc ne pourrait pas distinguer un piege arme d'une alliance declaree.
2. **Le residu exclut les cartes mortes.** La defausse est publique, donc
   `paquet - connues - ma main - morts` est exact. Oublier les morts surestime le residu
   de jusqu'a 20 % du paquet, et fait defendre des familles deja hors d'atteinte.
3. **La phase et la zone de l'Assassin en cours sont encodees.** Sans elles, deux poses
   differentes donnent le meme tenseur avec des cibles totalement differentes, et la
   phase de ciblage n'est pas jouable.

Un quatrieme, que la specification ne mentionne pas
----------------------------------------------------
**Le score provisoire ne peut pas etre le vrai score.** Les Espions adverses poses dans
un domaine comptent au decompte, mais leur famille est inconnue : mettre `scores()` dans
le tenseur ferait fuiter exactement ce que l'invariant I7 interdit. Ce module encode donc
un score **visible**, calcule sur les seules cartes dont le joueur connait la famille.

Canonicalisation : non implementee
-----------------------------------
Voir la note en fin de module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from courtisans import rules
from courtisans.cards import ROLES_CACHES, CartePosee, GenreZone, Position, Role
from courtisans.config import GameConfig

if TYPE_CHECKING:  # pragma: no cover - uniquement pour le typage
    from courtisans.engine import State

#: Phases encodees dans le vecteur global. `CHANCE` et `TERMINAL` n'ouvrent pas de
#: decision de joueur : elles n'ont pas de case.
PHASES_DE_DECISION: tuple[str, ...] = ("POSE", "CIBLAGE")


@dataclass(frozen=True)
class Bloc:
    """Un morceau nomme de l'observation, rendu tel quel dans la chaine et le tenseur."""

    nom: str
    valeurs: tuple[int, ...]


@dataclass(frozen=True)
class VueDuJoueur:
    """Ce qu'un joueur sait du plateau, et rien de plus.

    Attributes:
        connues: cartes posees dont il connait l'identite -- faces visibles et ses propres
            Espions.
        dos_adverses: cartes posees face cachee par quelqu'un d'autre. Position et poseur
            connus, identite inconnue.
    """

    connues: tuple[CartePosee, ...]
    dos_adverses: tuple[CartePosee, ...]


def _vue_du_joueur(etat: State, joueur: int) -> VueDuJoueur:
    """Separe les cartes posees selon ce que `joueur` en sait."""
    vue = etat.vue_privilegiee()
    connues = []
    dos = []
    for posee in vue.posees:
        if posee.carte.role in ROLES_CACHES and posee.poseur != joueur:
            dos.append(posee)
        else:
            connues.append(posee)
    return VueDuJoueur(tuple(connues), tuple(dos))


def _relatif(autre: int, joueur: int, joueurs: int) -> int:
    """Indexation relative : 0 c'est moi, 1 le suivant, 2 celui d'apres."""
    return (autre - joueur) % joueurs


def _compte(cartes: Any, config: GameConfig) -> dict[tuple[int, Role], int]:
    """Compte des cartes par (famille, role)."""
    comptes = {
        (famille, role): 0 for famille in range(config.familles) for role in config.roles
    }
    for carte in cartes:
        comptes[(carte.famille, carte.role)] += 1
    return comptes


def _roles_visibles(config: GameConfig) -> tuple[Role, ...]:
    """Les roles poses face visible, dans l'ordre canonique.

    Calcule depuis la configuration : une categorie ecrite en dur -- « attaquable, Garde »
    -- serait fausse des qu'un role est absent de l'instance.
    """
    return tuple(role for role in config.roles if role not in ROLES_CACHES)


def _blocs(etat: State, joueur: int) -> tuple[Bloc, ...]:
    """L'observation complete de `joueur`, bloc par bloc.

    L'ordre et la longueur de chaque bloc ne dependent que de la configuration.
    """
    config = etat.config
    vue = etat.vue_privilegiee()
    su = _vue_du_joueur(etat, joueur)
    familles = range(config.familles)
    roles = config.roles
    roles_visibles = _roles_visibles(config)
    joueurs = config.joueurs

    main = vue.mains[joueur]
    compte_main = _compte(main, config)
    compte_morts = _compte((posee.carte for posee in vue.defausse), config)
    compte_connues = _compte((posee.carte for posee in su.connues), config)

    # --- matrice familles x colonnes ---------------------------------------------
    ma_main: list[int] = []
    banquet_visible: list[int] = []
    banquet_prive: list[int] = []
    domaine_visible: list[int] = []
    domaine_prive: list[int] = []
    residu: list[int] = []
    morts: list[int] = []

    for famille in familles:
        for role in roles:
            ma_main.append(compte_main[(famille, role)])
            morts.append(compte_morts[(famille, role)])
            # Regle 2 : le residu retranche les morts. Ce qui reste est ce qui circule
            # encore : pioche, mains adverses, dos adverses.
            residu.append(
                config.exemplaires
                - compte_connues[(famille, role)]
                - compte_main[(famille, role)]
                - compte_morts[(famille, role)]
            )
        for role in roles_visibles:
            for position in Position:
                banquet_visible.append(
                    _compter(
                        su.connues,
                        famille=famille,
                        role=role,
                        genre=GenreZone.BANQUET,
                        position=position,
                    )
                )
            for autre in range(joueurs):
                domaine_visible.append(
                    _compter(
                        su.connues,
                        famille=famille,
                        role=role,
                        genre=GenreZone.DOMAINE,
                        proprietaire=(joueur + autre) % joueurs,
                    )
                )
        # Regle 1 : mes propres Espions ont leurs colonnes a eux, jamais fusionnees avec
        # les faces visibles -- sinon la vue publique n'est plus reconstructible.
        for position in Position:
            banquet_prive.append(
                _compter(
                    su.connues,
                    famille=famille,
                    caches=True,
                    poseur=joueur,
                    genre=GenreZone.BANQUET,
                    position=position,
                )
            )
        for autre in range(joueurs):
            domaine_prive.append(
                _compter(
                    su.connues,
                    famille=famille,
                    caches=True,
                    poseur=joueur,
                    genre=GenreZone.DOMAINE,
                    proprietaire=(joueur + autre) % joueurs,
                )
            )

    marges = _marges(etat, joueur, su, compte_main, config)

    # --- vecteur global -----------------------------------------------------------
    dos_banquet: list[int] = []
    dos_domaine: list[int] = []
    for autre in range(1, joueurs):
        poseur = (joueur + autre) % joueurs
        for position in Position:
            dos_banquet.append(
                sum(
                    1
                    for posee in su.dos_adverses
                    if posee.poseur == poseur
                    and posee.zone.genre is GenreZone.BANQUET
                    and posee.zone.position is position
                )
            )
        for domaine in range(joueurs):
            proprietaire = (joueur + domaine) % joueurs
            dos_domaine.append(
                sum(
                    1
                    for posee in su.dos_adverses
                    if posee.poseur == poseur
                    and posee.zone.genre is GenreZone.DOMAINE
                    and posee.zone.proprietaire == proprietaire
                )
            )

    tours_restants = [
        etat.tours_restants((joueur + autre) % joueurs) for autre in range(joueurs)
    ]
    scores_visibles = _scores_visibles(su, joueur, config)
    ecart = scores_visibles[0] - max(scores_visibles[1:], default=0)

    assassin = etat.assassin_en_resolution()
    return (
        Bloc("main", tuple(ma_main)),
        Bloc("banquet_visible", tuple(banquet_visible)),
        Bloc("banquet_prive", tuple(banquet_prive)),
        Bloc("domaine_visible", tuple(domaine_visible)),
        Bloc("domaine_prive", tuple(domaine_prive)),
        Bloc("residu", tuple(residu)),
        Bloc("morts", tuple(morts)),
        Bloc("marges", marges),
        Bloc("dos_adverses_banquet", tuple(dos_banquet)),
        Bloc("dos_adverses_domaine", tuple(dos_domaine)),
        Bloc("tours_restants", tuple(tours_restants)),
        Bloc("pioche", (len(vue.pioche),)),
        Bloc("morts_total", (len(vue.defausse),)),
        Bloc("phase", _phase_one_hot(etat)),
        Bloc("assassin", _assassin_one_hot(assassin, joueur, config)),
        Bloc("assassins_restants", (_assassins_restants(etat),)),
        Bloc("scores_visibles", tuple(scores_visibles)),
        Bloc("ecart", (ecart,)),
    )


def _compter(
    posees: tuple[CartePosee, ...],
    *,
    famille: int,
    genre: GenreZone,
    role: Role | None = None,
    caches: bool = False,
    poseur: int | None = None,
    position: Position | None = None,
    proprietaire: int | None = None,
) -> int:
    """Compte les cartes posees qui correspondent a tous les criteres fournis."""
    total = 0
    for posee in posees:
        if posee.carte.famille != famille or posee.zone.genre is not genre:
            continue
        if role is not None and posee.carte.role is not role:
            continue
        if caches and posee.carte.role not in ROLES_CACHES:
            continue
        if poseur is not None and posee.poseur != poseur:
            continue
        if position is not None and posee.zone.position is not position:
            continue
        if proprietaire is not None and posee.zone.proprietaire != proprietaire:
            continue
        total += 1
    return total


def _marges(
    etat: State,
    joueur: int,
    su: VueDuJoueur,
    compte_main: dict[tuple[int, Role], int],
    config: GameConfig,
) -> tuple[int, ...]:
    """Les quatre grandeurs derivees du paragraphe 2.6 des regles, par famille.

    Marge visible, marge pire cas, marge meilleur cas, cartes de la famille encore
    posables au banquet.

    Un dos adverse est toujours un Espion, donc de valeur 1, et sa famille est inconnue :
    il peut donc faire varier `d` de -1 s'il est en Disgrace, de +1 s'il est en Estime.
    L'encadrement est une borne, pas une distribution : c'est au reseau d'apprendre a
    l'affiner.
    """
    visible = rules.influence(su.connues, config.familles)
    dos_estime = sum(
        1
        for posee in su.dos_adverses
        if posee.zone.genre is GenreZone.BANQUET and posee.zone.position is Position.ESTIME
    )
    dos_disgrace = sum(
        1
        for posee in su.dos_adverses
        if posee.zone.genre is GenreZone.BANQUET
        and posee.zone.position is Position.DISGRACE
    )
    poses_restantes = sum(
        etat.tours_restants(autre) for autre in range(config.joueurs)
    )
    compte_connues = _compte((posee.carte for posee in su.connues), config)
    compte_morts = _compte(
        (posee.carte for posee in etat.vue_privilegiee().defausse), config
    )

    valeurs: list[int] = []
    for famille in range(config.familles):
        en_circulation = sum(
            config.exemplaires
            - compte_connues[(famille, role)]
            - compte_main[(famille, role)]
            - compte_morts[(famille, role)]
            for role in config.roles
        )
        en_main = sum(compte_main[(famille, role)] for role in config.roles)
        valeurs.extend(
            (
                visible[famille],
                visible[famille] - dos_disgrace,
                visible[famille] + dos_estime,
                min(en_main + en_circulation, poses_restantes),
            )
        )
    return tuple(valeurs)


def _scores_visibles(su: VueDuJoueur, joueur: int, config: GameConfig) -> list[int]:
    """Le score provisoire calcule sur les seules cartes dont le joueur connait la famille.

    Ce n'est **pas** `etat.scores()` : le vrai score depend des Espions adverses poses
    dans les domaines, dont la famille est cachee. L'y mettre violerait l'invariant I7.
    """
    statuts = rules.statuts(su.connues, config.familles)
    absolus = rules.points(su.connues, statuts, config.joueurs)
    return [absolus[(joueur + autre) % config.joueurs] for autre in range(config.joueurs)]


def _phase_one_hot(etat: State) -> tuple[int, ...]:
    """La phase courante. Sans elle, deux etats aux cibles differentes se confondent."""
    courante = etat.phase().name
    return tuple(1 if nom == courante else 0 for nom in PHASES_DE_DECISION)


def _assassin_one_hot(
    assassin: CartePosee | None, joueur: int, config: GameConfig
) -> tuple[int, ...]:
    """La zone de l'Assassin en cours de resolution : genre, position, domaine relatif.

    Tout a zero hors phase de ciblage. La famille et le role de l'Assassin ne sont pas
    encodes : il est toujours visible, donc deja compte dans les blocs de zone.
    """
    genre = [0] * len(GenreZone)
    position = [0] * len(Position)
    domaine = [0] * config.joueurs
    if assassin is not None:
        genre[int(assassin.zone.genre)] = 1
        if assassin.zone.position is not None:
            position[int(assassin.zone.position)] = 1
        if assassin.zone.proprietaire is not None:
            domaine[_relatif(assassin.zone.proprietaire, joueur, config.joueurs)] = 1
    return (*genre, *position, *domaine)


def _assassins_restants(etat: State) -> int:
    """Combien d'Assassins attendent encore leur decision, celui en cours compris."""
    return len(etat.assassins_en_attente())


def chaine(etat: State, joueur: int) -> str:
    """La vue de `joueur`, sous forme de chaine -- l'identifiant de son info-set.

    Serialisation sans perte des memes blocs que `tenseur`, dans le meme ordre.
    """
    return "|".join(
        f"{bloc.nom}={','.join(str(valeur) for valeur in bloc.valeurs)}"
        for bloc in _blocs(etat, joueur)
    )


def tenseur(etat: State, joueur: int) -> list[float]:
    """La vue de `joueur`, sous forme de vecteur de longueur constante."""
    return [
        float(valeur) for bloc in _blocs(etat, joueur) for valeur in bloc.valeurs
    ]


def disposition(etat: State, joueur: int) -> tuple[tuple[str, int], ...]:
    """Le nom et la longueur de chaque bloc, pour lire un tenseur sans le deviner."""
    return tuple((bloc.nom, len(bloc.valeurs)) for bloc in _blocs(etat, joueur))


# ---------------------------------------------------------------------------------
# Canonicalisation par permutation des familles -- NON IMPLEMENTEE
#
# Le paragraphe 4.2 impose un ordre de composition : canonicaliser les familles d'abord,
# trier la main ensuite. Cet ordre a une consequence que la specification n'ecrit pas :
# permuter les familles reordonne la main triee, donc **change la carte que chaque action
# de pose designe**. Canonicaliser l'observation sans traduire aussi l'espace d'actions
# produirait un agent qui croit poser une carte et en pose une autre -- un defaut qui ne
# se voit dans aucune metrique, exactement celui que le paragraphe 4.2 signale.
#
# La traduction demande une API que le paragraphe 4 de la specification ne definit pas :
# une action canonique, et son image dans l'espace du moteur. Elle n'est donc pas ecrite
# ici, et aucun test ne la couvre. C'est un point d'arbitrage, remonte dans le compte
# rendu de l'etape 6.
# ---------------------------------------------------------------------------------
