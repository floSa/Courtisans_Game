"""Le collage : une `Politique` pour `mesure.partie.observer`, a partir d'un agent.

Ce module voit un `State` -- il faut bien que quelqu'un le traduise. Il ne decide **rien** :
il percoit, puis delegue. Toute la decision est dans `agents/greedy.py`, qui ne recoit que la
`Perception`.

`percevoir` est appelee **avant** `choisir`, et son resultat est complet : c'est ce qui rend la
preuve P2 possible. Pendant tout l'appel a `choisir`, `State.vue_privilegiee` peut etre
remplacee par une fonction qui leve -- si le greedy y touchait, la partie s'arreterait.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from agents import greedy
from agents.perception import percevoir
from courtisans.engine import State

#: Meme signature que `mesure.partie.Politique` : un etat, une action.
Politique = Callable[[State], int]


def politique_greedy(alea: random.Random) -> Politique:
    """Le greedy de reference : departage uniforme dans l'ensemble des argmax.

    `alea` est l'aleatoire de **departage**, distinct de celui de la donne et de celui d'une
    eventuelle politique aleatoire adverse. Sans cette separation, on ne saurait pas laquelle
    des trois fait varier un chiffre -- c'est la lecon de l'instrument de la phase 1.
    """

    def politique(etat: State) -> int:
        perception = percevoir(etat, etat.current_player())
        return greedy.choisir(perception, alea)

    return politique


def politique_greedy_deterministe() -> Politique:
    """La variante de robustesse : departage par plus petit indice.

    **Biaisee** (voir `greedy.choisir_par_plus_petit_indice`). Son seul usage est de rapporter
    M3 sous un departage deterministe, a cote de M3 de reference.
    """

    def politique(etat: State) -> int:
        perception = percevoir(etat, etat.current_player())
        return greedy.choisir_par_plus_petit_indice(perception)

    return politique
