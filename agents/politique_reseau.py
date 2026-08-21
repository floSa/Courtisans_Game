"""Le collage : une `Politique` a partir d'un reseau. **Ce module voit un `State`.**

Il faut bien que quelqu'un traduise. Comme `agents/politique.py` pour le greedy, ce module ne
decide **rien** : il observe, puis delegue. Toute la decision est dans `agents/reseau.py`, qui
ne recoit qu'un vecteur de flottants et une liste d'indices.

L'observation est construite AVANT la decision, et hors d'elle
---------------------------------------------------------------
C'est la meme discipline que `perception.percevoir`, et pour la meme raison : c'est ce qui rend
la preuve P2 possible. Pendant tout l'appel a `reseau.choisir`, `State.vue_privilegiee` peut
etre remplacee par une fonction qui **leve** -- si le reseau y touchait, la partie s'arreterait.
Si l'observation se construisait paresseusement, la preuve n'aurait plus aucun sens.

`tenseur` plutot que `Perception`, et pourquoi ce n'est pas un relachement
---------------------------------------------------------------------------
Le greedy recoit une `Perception`, un objet dont chaque champ a du etre justifie. Le reseau
recoit `infoset.tenseur(etat, joueur)` -- l'observation **officielle** du moteur, paragraphe 4.2
de la specification, tenue par l'invariant I7 et par
`tests/infoset/test_vue_du_joueur.py`, qui permute l'identite des dos adverses et exige que le
tenseur ne bouge pas.

Les deux partent du **meme** predicat : `vue_du_joueur`. Reconstruire un tenseur depuis une
`Perception` dupliquerait l'encodage, ce que le paragraphe 2 des conventions interdit -- deux
definitions finissent par ne plus etre d'accord.

`etat.current_player()` et le piege que la phase 3 a ferme
-----------------------------------------------------------
Cette fonction ecrit `tenseur(etat, etat.current_player())`. **C'est exactement la ligne que
l'obstacle A rendait dangereuse** : sur un nœud de distribution, `current_player()` rend
`JOUEUR_HASARD`, qui vaut **-1**, et `tenseur(etat, -1)` rendait 205 flottants qui n'etaient le
tenseur d'aucun siege, sans rien lever. Un agent se serait entraine sur le tenseur de personne.

Depuis le 20/08/2026, `vue_du_joueur` appelle `State._joueur_observe` et **leve** en nommant la
cause. Cette ligne est donc sure, et elle l'est par une parade du moteur, pas par une precaution
ecrite ici.
"""

from __future__ import annotations

import random
from collections.abc import Callable

import torch

from agents import reseau as reseau_module
from courtisans.engine import State
from courtisans.infoset import tenseur

#: Meme signature que `mesure.partie.Politique` et que `agents.politique.Politique` : un etat,
#: une action. Les trois se substituent l'une a l'autre dans n'importe quelle campagne.
Politique = Callable[[State], int]


def politique_reseau(
    modele: reseau_module.ReseauPolitiqueValeur, alea: random.Random
) -> Politique:
    """La politique d'un reseau : echantillonnee dans la loi masquee.

    `alea` est l'aleatoire de **tirage**, distinct de celui de la donne et de celui d'un
    eventuel adversaire. Sans cette separation, on ne saurait pas laquelle des trois fait varier
    un chiffre -- c'est la lecon de l'instrument de la phase 1, et c'est la meme regle que pour
    le departage du greedy.
    """

    def politique(etat: State) -> int:
        observation = tenseur(etat, etat.current_player())
        actions = etat.legal_actions()
        indice = reseau_module.choisir(modele, observation, actions, alea)
        return indice

    return politique


def politique_reseau_deterministe(
    modele: reseau_module.ReseauPolitiqueValeur,
) -> Politique:
    """La variante deterministe : l'action la plus probable.

    **Biaisee**, et son seul usage est d'etre rapportee a cote de la mesure de reference --
    exactement le statut de `agents.politique.politique_greedy_deterministe`.
    """

    def politique(etat: State) -> int:
        observation = tenseur(etat, etat.current_player())
        return reseau_module.choisir_le_plus_probable(
            modele, observation, etat.legal_actions()
        )

    return politique


def charger(chemin: str, taille_observation: int, nb_actions: int, **forme: int):
    """Relit un checkpoint et rend un reseau **en mode evaluation**.

    `eval()` est appele ici et non chez l'appelant : un reseau relu puis laisse en mode
    entrainement mesurerait autre chose que ce qu'il a appris si une couche de normalisation
    ou de `dropout` etait ajoutee plus tard. Le faire au seul endroit qui relit est la parade ;
    le rappeler dans une docstring ne l'est pas.
    """
    modele = reseau_module.ReseauPolitiqueValeur(taille_observation, nb_actions, **forme)
    modele.load_state_dict(torch.load(chemin, map_location="cpu", weights_only=True))
    modele.eval()
    return modele


__all__ = ["Politique", "charger", "politique_reseau", "politique_reseau_deterministe"]
