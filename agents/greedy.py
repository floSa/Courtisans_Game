"""Le greedy : maximiser l'ecart de score obtenu sur le tour en cours.

Sa regle est celle du paragraphe 7.1 des regles, et rien d'autre :

> Maximiser l'**ecart de score obtenu sur le tour en cours**, comme si la partie s'arretait la.

**Ce module ne voit jamais un `State`.** Il decide a partir d'une `Perception`, donc de ce que
le decideur sait -- faces visibles et ses propres Espions. Il n'a aucun moyen de lire la
pioche, une main adverse ou l'identite d'un dos : ce n'est pas une precaution, c'est sa
signature. Voir `agents/perception.py` et `tests/agents/test_aveuglement.py`.

Ce qu'il ne fait pas, et c'est voulu
------------------------------------
Le paragraphe 7.1 des regles enumere ses angles morts. Ils sont **reproduits ici a
l'identique**, parce qu'un greedy qui les corrigerait ne serait plus la ligne de base que la
phase 2 doit etablir :

- il n'anticipe aucun retournement : il evalue les signes actuels comme definitifs ;
- il ne calcule pas sa marge : ni residu, ni tours restants, ni poids de bascule ;
- il ne raisonne pas sur les Espions adverses : **un dos vaut zero**, il est absent de son
  decompte, exactement comme le dit le paragraphe 7.1 -- « il traite une carte cachee comme
  neutre » ;
- il ne construit aucune alliance : il ne modelise pas l'interet qu'il cree en donnant ;
- il ne planifie pas sur plusieurs tours : son horizon est **un tour**.

**Consequence a ne jamais oublier en lisant ses chiffres** : un motif de planification observe
chez lui est une **coincidence**, pas un plan. Paragraphe 7 du document d'instrument.

L'arbitrage du tour : G-combine
-------------------------------
« Le tour en cours » inclut la resolution des Assassins qu'il vient de poser. Trois raisons :

1. le paragraphe 2.3 des regles : les trois cartes et l'effet de l'Assassin « forment un seul
   coup », et « poser une carte chez un adversaire sans avoir decide ce que fera l'Assassin du
   meme tour n'a aucun sens » ;
2. le paragraphe 7.1 enumere ce qu'il ne fait pas, et **combiner a l'interieur d'un tour n'y
   figure pas** ;
3. l'action de pose du moteur **est atomique** : `legal_actions()` rend des blocs de trois
   cartes, pas trois placements. Un G-naif devrait decomposer une action que l'espace
   d'action n'expose pas.

Le risque de ce choix est unidirectionnel : un greedy plus fort place la barre de la phase 3
plus haut. `M3(G-naif)` est rapporte sur les memes donnes pour que l'ecart soit un chiffre.

Le departage
------------
`choisir` tire **uniformement** dans l'ensemble des argmax. Prendre le plus petit indice serait
deterministe et **biaise** : l'indice d'une action de pose encode l'assignation, la position au
banquet et l'adversaire vise (`rules.decoder_action_pose`, base mixte, l'adversaire variant le
plus vite), donc une preference stable pour l'indice 0 fabriquerait un artefact directement
dans B2, B3 et B6. `choisir_par_plus_petit_indice` existe comme variante de robustesse, et son
seul usage est un report a cote de M3.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from agents.perception import Perception
from courtisans import rules
from courtisans.cards import CartePosee, Zone
from courtisans.config import GameConfig
from courtisans.engine import Phase


def evaluer(
    connues: Sequence[CartePosee], moi: int, config: GameConfig
) -> int:
    """L'ecart de score de `moi`, decompte comme si la partie s'arretait maintenant.

    `points(connues)[moi] - max_{j != moi} points(connues)[j]`, calcule par
    `rules.statuts` et `rules.points` -- jamais par un decompte reecrit ici. Le paragraphe 2
    des conventions l'impose : le greedy n'a aucune logique de regle a lui.

    `connues` est ce que le decideur connait, **pas le plateau reel**. Les Espions adverses
    n'y figurent pas, donc valent zero. C'est la regle du greedy, pas une approximation.
    """
    statuts = rules.statuts(connues, config.familles)
    points = rules.points(connues, statuts, config.joueurs)
    return points[moi] - max(
        points[siege] for siege in range(config.joueurs) if siege != moi
    )


def _sans(plateau: Sequence[CartePosee], indice: int) -> list[CartePosee]:
    """Le plateau prive de sa carte d'indice `indice`.

    Retire **par position** et non par egalite : deux `CartePosee` de meme carte, meme zone
    et meme poseur seraient egales, et un retrait par valeur en enleverait deux.
    """
    return [posee for rang, posee in enumerate(plateau) if rang != indice]


def _meilleur_apres_assassins(
    plateau: Sequence[CartePosee],
    assassins: Sequence[CartePosee],
    moi: int,
    config: GameConfig,
) -> int:
    """Le meilleur ecart atteignable en resolvant `assassins` dans l'ordre, refus compris.

    Recursion sur la liste des Assassins encore a resoudre, dans l'ordre du paragraphe 3.2 :
    banquet, domaine propre, domaine adverse. A chaque niveau, le refus est une branche a
    part entiere -- jamais un cas degenere.

    Un Assassin de ce tour ne peut pas tuer ses compagnons de tour, les trois zones etant
    disjointes (paragraphe 3.2). Le filtrage de `restants` couvre le cas general ou une cible
    serait un Assassin **d'un tour anterieur** encore en attente, qui ne peut pas arriver
    dans cette configuration mais qui ne coute rien a tenir.
    """
    if not assassins:
        return evaluer(plateau, moi, config)
    assassin, restants = assassins[0], assassins[1:]
    meilleur = _meilleur_apres_assassins(plateau, restants, moi, config)
    cibles = rules.cibles_valides(plateau, assassin)
    for cible in cibles:
        indice = next(
            rang for rang, posee in enumerate(plateau) if posee is cible or posee == cible
        )
        apres = _sans(plateau, indice)
        survivants = [reste for reste in restants if reste != cible]
        meilleur = max(
            meilleur, _meilleur_apres_assassins(apres, survivants, moi, config)
        )
    return meilleur


def _valeur_de_pose(perception: Perception, action: int) -> int:
    """L'ecart atteignable si `action` est jouee, ses propres Assassins resolus au mieux.

    Reconstruit les trois cartes posees avec `rules.decoder_action_pose` et
    `rules.destinataire` : le decodage est une regle publique, connue de tous les joueurs, et
    il n'est pas reecrit ici.
    """
    config = perception.config
    pose = rules.decoder_action_pose(action, config)
    adversaire = rules.destinataire(perception.moi, pose.adversaire_relatif, config.joueurs)
    zones = (
        Zone.banquet(pose.position),
        Zone.domaine(perception.moi),
        Zone.domaine(adversaire),
    )
    posees = [
        CartePosee(perception.main[indice], zone, perception.moi)
        for indice, zone in zip(pose.indices_main, zones, strict=True)
    ]
    plateau = list(perception.connues) + posees
    # L'ordre de cette liste EST l'ordre de resolution du paragraphe 3.2, parce que `zones`
    # est deja dans cet ordre.
    assassins = [posee for posee in posees if posee.carte.role in rules.ROLES_ASSASSINS]
    return _meilleur_apres_assassins(plateau, assassins, moi=perception.moi, config=config)


def _valeur_de_ciblage(perception: Perception, action: int) -> int:
    """L'ecart apres avoir tue la cible d'indice `action`, ou apres avoir refuse.

    **Tuer un dos ne change rien** : un dos vaut zero dans la vue du decideur, donc il n'est
    pas dans `connues` et son retrait est sans effet. Cette action a donc exactement la
    valeur du refus -- c'est ce qui impose a B4 de publier le refus strict et le refus par
    departage separement (paragraphe 6.4 du document d'instrument).
    """
    config = perception.config
    plateau = list(perception.connues)
    if action >= len(perception.cibles):
        return evaluer(plateau, perception.moi, config)
    cible = perception.cibles[action]
    if cible.carte is None:
        return evaluer(plateau, perception.moi, config)
    # Une cible se designe par sa carte **et sa zone**. La carte seule suffirait dans une
    # partie legale -- une `Carte` porte son exemplaire, donc elle est unique -- mais s'en
    # contenter faisait retirer la mauvaise carte sur un plateau de test mal construit, sans
    # rien signaler. On designe ce qu'on veut retirer.
    indice = next(
        rang
        for rang, posee in enumerate(plateau)
        if posee.carte == cible.carte and posee.zone == cible.zone
    )
    return evaluer(_sans(plateau, indice), perception.moi, config)


def evaluer_actions(perception: Perception) -> dict[int, int]:
    """L'ecart atteignable par chaque action legale. La brique des compteurs de B4.

    Rendue publique pour que `mesure/comportements.py` puisse dire si un refus etait
    strictement meilleur que tout meurtre, ou seulement a egalite -- sans reecrire
    l'evaluation, ce qui la ferait deriver de celle de l'agent mesure.

    Raises:
        ValueError: si la phase n'est ni POSE ni CIBLAGE.
    """
    if perception.phase is Phase.POSE:
        return {
            action: _valeur_de_pose(perception, action)
            for action in perception.actions_legales
        }
    if perception.phase is Phase.CIBLAGE:
        return {
            action: _valeur_de_ciblage(perception, action)
            for action in perception.actions_legales
        }
    raise ValueError(f"le greedy ne decide pas en phase {perception.phase.name}")


def _argmax(valeurs: dict[int, int]) -> list[int]:
    """Toutes les actions qui atteignent le maximum, triees. Jamais une seule d'office."""
    if not valeurs:
        raise ValueError(
            "aucune action legale a evaluer : une Perception sans action ne se decide pas"
        )
    meilleur = max(valeurs.values())
    return sorted(action for action, valeur in valeurs.items() if valeur == meilleur)


def choisir(perception: Perception, alea: random.Random) -> int:
    """L'action du greedy : un tirage uniforme dans l'ensemble des argmax.

    `alea` est **obligatoire et positionnel** : un defaut le rendrait facultatif, et
    l'oublier ferait retomber silencieusement sur un departage biaise.
    """
    return alea.choice(_argmax(evaluer_actions(perception)))


def choisir_par_plus_petit_indice(perception: Perception) -> int:
    """La variante de robustesse : le plus petit indice parmi les argmax.

    **Biaisee, et c'est pour ca qu'elle n'est pas la reference.** L'indice d'une pose encode
    l'assignation, la position au banquet et l'adversaire vise ; preferer le plus petit
    fabrique une preference stable, donc un artefact dans B2, B3 et B6. Son seul usage est
    de rapporter M3 sous un departage deterministe, a cote de M3 de reference.
    """
    return _argmax(evaluer_actions(perception))[0]
