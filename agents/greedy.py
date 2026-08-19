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

Le ciblage se decide SANS les Assassins en attente -- et la specification le disait mal
--------------------------------------------------------------------------------------
**Defaut majeur releve par l'audit croise, corrige dans la description et non dans le code.**
L'arbitrage G-combine ci-dessus decrit la **pose** : `_valeur_de_pose` resout conjointement tous
les Assassins du bloc. Mais les **ciblages** se decident ensuite **un nœud a la fois**, et
`Perception` ne porte pas les Assassins encore en attente (voir ses attributs : `assassin` est
celui qui se resout, il n'y a pas de liste des suivants). La politique ne PEUT donc pas regarder
plus loin que le nœud courant.

**L'incoherence est structurelle, pas un accident de code.** L'action de pose de l'adaptateur est
**atomique** -- un identifiant d'action encode le bloc de trois cartes entier, fait etabli en
phase 0 --, donc le bloc est choisi d'un coup sous une evaluation conjointe, pendant que le
ciblage se decide apres, nœud par nœud, sans memoire de ce que le bloc contenait.

Combien. MESURE sur la campagne B entiere -- 10 002 parties, siege du greedy, intervalles de
Clopper-Pearson **exacts** a 99 % bilateral. Le denominateur est ecrit a chaque ligne, parce que la
question admet deux lectures et qu'un taux dont on ne sait pas de quoi il est la part n'est pas
auditable :

  - **4,23 %** (172/4063), IC [3,46 ; 5,11] -- des nœuds de ciblage ou **au moins un Assassin du
    meme bloc reste en attente**, l'argmax myope et l'argmax coherent ne coincident pas ;
  - **3,13 %** (127/4063), IC [2,47 ; 3,90] -- de ces memes nœuds, l'argmax myope contient une
    action que l'argmax coherent **rejette**. C'est la part qui **coute** : le departage uniforme
    peut y tirer une action coherentement dominee ;
  - **0,72 %** (172/23991), IC [0,58 ; 0,87] -- de **tous** les nœuds de ciblage.

Le module `mesure/coherence_greedy.py` rend ces trois chiffres, et
`uv run python -m mesure.coherence_greedy --donnes 200` les recalcule en une minute sur le prefixe
de la campagne B.

**Le sens du biais, et il n'est pas le meme pour M3 et pour M4.**

- **M3 : plancher.** Un agent plus myope que sa specification est plus **faible**, donc
  `+0,7978` de gain moyen et `86,52 %` de part de victoire sont un **plancher** du greedy, pas
  une estimation de ce qu'un G-combine complet obtiendrait. Un plancher place la barre de la
  phase 3 plus bas, jamais plus haut.
- **M4 : aucun sens determine, et QUATRE compteurs sont tautologiques.** `B4-strict`,
  `B4-departage`, `B4-contre-nature` et **`B4-meurtre-couteux`** sont juges **par
  `evaluer_actions`**, c'est-a-dire par l'evaluation myope elle-meme -- les quatre lisent
  `decision.valeurs`. Le zero de `B4-contre-nature` ne dit donc **pas** que le greedy n'a jamais
  commis de refus contre-productif, et le zero de `B4-meurtre-couteux` ne dit **pas** qu'il n'a
  jamais commis de meurtre contre-productif : les deux disent qu'il n'a jamais **contredit sa
  propre evaluation**. Deux enonces differents a chaque fois, et seul le second est vrai. **Les
  deux zeros absolus sont tous les deux dans ce lot.** Les denominateurs de `B4-strict` et
  `B4-departage` sortent du meme argmax, donc la meme lecture s'applique aux quatre.

**Ce qui tient ce comportement** : `tests/agents/test_greedy.py`, sur une position construite a
la main ou l'argmax myope est a egalite et l'argmax coherent strictement meilleur de 2 points. Un
« correctif » futur casserait ce test bruyamment -- ce qui est le but : la ligne de base de toutes
les phases suivantes est celle de **cet** agent, myope au ciblage, et corriger le code
invaliderait M3 et M4 entiers.

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

from agents.perception import CibleVue, Perception
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


def _plateau_apres_ciblage(
    connues: Sequence[CartePosee], cibles: Sequence[CibleVue], action: int
) -> list[CartePosee]:
    """Le plateau du decideur apres l'action de ciblage `action`, refus compris.

    **Tuer un dos ne change rien** : un dos vaut zero dans la vue du decideur, donc il n'est
    pas dans `connues` et son retrait est sans effet. Cette action laisse donc exactement le
    plateau du refus -- c'est ce qui impose a B4 de publier le refus strict et le refus par
    departage separement (paragraphe 6.4 du document d'instrument).

    Ecrit une fois pour les deux evaluations, myope et coherente : les recopier ferait deux
    endroits ou la designation d'une cible pourrait deriver.
    """
    plateau = list(connues)
    if action >= len(cibles):
        return plateau
    cible = cibles[action]
    if cible.carte is None:
        return plateau
    # Une cible se designe par sa carte **et sa zone**. La carte seule suffirait dans une
    # partie legale -- une `Carte` porte son exemplaire, donc elle est unique -- mais s'en
    # contenter faisait retirer la mauvaise carte sur un plateau de test mal construit, sans
    # rien signaler. On designe ce qu'on veut retirer.
    indice = next(
        rang
        for rang, posee in enumerate(plateau)
        if posee.carte == cible.carte and posee.zone == cible.zone
    )
    return _sans(plateau, indice)


def _valeur_de_ciblage(perception: Perception, action: int) -> int:
    """L'ecart apres avoir tue la cible d'indice `action`, ou apres avoir refuse.

    **Myope par construction** : elle ne regarde pas les Assassins du meme bloc encore en
    attente, parce que `Perception` ne les porte pas. C'est le comportement de l'agent, decrit
    en tete de module, et `evaluer_ciblages_coherents` existe pour le **mesurer**, pas pour le
    remplacer.
    """
    plateau = _plateau_apres_ciblage(perception.connues, perception.cibles, action)
    return evaluer(plateau, perception.moi, perception.config)


def evaluer_ciblages_coherents(
    connues: Sequence[CartePosee],
    cibles: Sequence[CibleVue],
    actions_legales: Sequence[int],
    en_attente: Sequence[CartePosee],
    moi: int,
    config: GameConfig,
) -> dict[int, int]:
    """Ce que chaque ciblage vaudrait si les Assassins **en attente** etaient pris en compte.

    **Ce n'est pas la politique, et l'agent ne l'appelle jamais.** C'est l'instrument qui mesure
    l'ecart entre ce que le greedy fait et ce que sa specification laissait croire : la pose est
    evaluee conjointement, le ciblage non. Voir la section correspondante en tete de module.

    Prend ses arguments **explicitement** plutot qu'une `Perception` : une `Perception` ne porte
    pas les Assassins en attente, et en fabriquer une qui pretende le contraire ferait mentir le
    type sur lequel repose toute la preuve d'aveuglement.

    `en_attente` vide rend exactement `evaluer_actions` sur les memes ciblages -- c'est teste,
    parce que sans cette egalite l'ecart mesure melangerait l'incoherence avec une divergence de
    calcul.
    """
    return {
        action: _meilleur_apres_assassins(
            _plateau_apres_ciblage(connues, cibles, action), en_attente, moi, config
        )
        for action in actions_legales
    }


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
