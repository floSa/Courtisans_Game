"""Mon greedy, ecrit depuis le seul paragraphe 7.1 des regles.

Le texte, mot a mot : « **maximiser l'ecart de score obtenu sur le tour en cours**, comme
si la partie s'arretait la ». Trois consequences, chacune tiree d'une ligne du meme
paragraphe :

1. **L'objectif est un ecart, pas un score.** `mes points - le meilleur des autres`, sur
   le plateau tel qu'il serait si la partie s'arretait immediatement.
2. **Une carte cachee est traitee comme neutre.** Ligne « Raisonner sur les Espions
   adverses : il traite une carte cachee comme neutre, au lieu de raisonner sur le pire
   cas ». Le greedy evalue donc sur les seules cartes dont il connait la famille -- ce que
   `VueLegale.connues` contient exactement. Il n'echantillonne aucune determinisation :
   le paragraphe dit qu'il ignore l'incertitude, pas qu'il l'integre.
3. **L'horizon est d'un tour.** Ligne « Planifier sur plusieurs tours : son horizon est
   d'un tour, par construction ». Aucun deroulement au-dela du tour courant.

L'unite « tour » -- l'arbitrage, et sa concurrente
--------------------------------------------------
Le paragraphe 3.2 fait d'un tour une pose **puis** la resolution des Assassins poses, et
le paragraphe 2.3 dit que « les trois cartes et l'effet de l'Assassin forment un seul
coup ». La lecture retenue, `HORIZON_TOUR`, evalue donc une pose par l'ecart atteint
**apres** que ses propres Assassins ont choisi, chacun au mieux de ce meme critere.

La lecture concurrente, `HORIZON_NOEUD`, evalue chaque noeud de decision isolement : la
pose sur l'ecart immediat, puis chaque ciblage sur le sien. Elle est defendable -- le
moteur expose bien deux noeuds distincts -- et elle change B2 et B4. Les deux sont
implementees et **les deux sont mesurees** : l'ecart entre elles chiffre ce que le choix
de lecture coute, au lieu de le trancher en silence.

Le departage des ex aequo
--------------------------
Il n'est dans aucune regle : c'est un choix d'implementation. `plus_petit_indice` est
deterministe et n'utilise aucune information cachee. Il est **parametre**, et non fixe,
parce qu'un greedy souvent indifferent mesurerait sa regle de departage plutot que sa
politique -- ce que cet audit verifie explicitement.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from courtisans.cards import ROLES_CACHES, CartePosee
from courtisans.engine import Phase, State

from audit.phase2.decompte import ecart, scores
from audit.phase2.vue import vue_legale

HORIZON_TOUR = "tour"
HORIZON_NOEUD = "noeud"


def ecart_visible(etat: State, moi: int) -> int:
    """L'ecart de score **tel que ce siege peut le calculer**, partie arretee ici.

    Calcule sur `VueLegale.connues` : les faces visibles et mes propres Espions. Les dos
    adverses n'y sont pas, donc ils pesent zero -- « il traite une carte cachee comme
    neutre » (paragraphe 7.1).
    """
    vue = vue_legale(etat, moi)
    bruts = scores(vue.connues, vue.config.familles, vue.config.joueurs)
    return ecart(bruts, moi)


def _premier(indices: Sequence[int], _rng: random.Random | None) -> int:
    """Departage par le plus petit indice d'action. Deterministe."""
    return indices[0]


def _tire_au_sort(indices: Sequence[int], rng: random.Random | None) -> int:
    """Departage uniforme parmi les ex aequo. Demande un generateur."""
    if rng is None:
        raise ValueError("le departage au sort exige un generateur")
    return rng.choice(list(indices))


DEPARTAGES: dict[str, Callable[[Sequence[int], random.Random | None], int]] = {
    "plus_petit_indice": _premier,
    "au_sort": _tire_au_sort,
}


@dataclass
class Greedy:
    """La politique du paragraphe 7.1. Ne lit l'etat que par `VueLegale`.

    Attributes:
        horizon: `HORIZON_TOUR` (pose evaluee Assassins resolus) ou `HORIZON_NOEUD`.
        departage: cle de `DEPARTAGES`.
        rng: generateur, requis pour `au_sort` seulement.
    """

    horizon: str = HORIZON_TOUR
    departage: str = "plus_petit_indice"
    rng: random.Random | None = None

    def __post_init__(self) -> None:
        if self.horizon not in (HORIZON_TOUR, HORIZON_NOEUD):
            raise ValueError(f"horizon inconnu : {self.horizon!r}")
        if self.departage not in DEPARTAGES:
            raise ValueError(f"departage inconnu : {self.departage!r}")

    # -- l'interface d'une politique ------------------------------------------------

    def action(self, etat: State) -> int:
        """L'action choisie a ce noeud. `etat` n'est lu que par `VueLegale`."""
        moi = etat.current_player()
        legales = etat.legal_actions()
        if len(legales) == 1:
            return legales[0]
        valeurs = [self._valeur(etat, moi, action) for action in legales]
        meilleure = max(valeurs)
        exaequo = [a for a, v in zip(legales, valeurs, strict=True) if v == meilleure]
        return DEPARTAGES[self.departage](exaequo, self.rng)

    def multiplicite_exaequo(self, etat: State) -> tuple[int, int]:
        """`(ex aequo au sommet, actions legales)` a ce noeud.

        Sert a mesurer si la politique decide, ou si c'est son departage qui decide.
        """
        moi = etat.current_player()
        legales = etat.legal_actions()
        valeurs = [self._valeur(etat, moi, action) for action in legales]
        return sum(1 for v in valeurs if v == max(valeurs)), len(legales)

    # -- l'evaluation ----------------------------------------------------------------

    def _valeur(self, etat: State, moi: int, action: int) -> int:
        """L'ecart visible atteint apres cette action, selon l'horizon retenu."""
        suivant = etat.clone()
        suivant.apply(action)
        if self.horizon == HORIZON_NOEUD:
            return ecart_visible(suivant, moi)
        # HORIZON_TOUR : les Assassins du meme tour font partie du coup (paragraphe 2.3).
        while suivant.phase() is Phase.CIBLAGE and suivant.current_player() == moi:
            suivant.apply(self._meilleur_ciblage(suivant, moi))
        return ecart_visible(suivant, moi)

    def _meilleur_ciblage(self, etat: State, moi: int) -> int:
        """Le ciblage qui maximise l'ecart visible. Ne lit jamais l'identite d'un dos."""
        meilleures: list[int] = []
        meilleure_valeur: int | None = None
        for action in etat.legal_actions():
            suivant = etat.clone()
            suivant.apply(action)
            valeur = ecart_visible(suivant, moi)
            if meilleure_valeur is None or valeur > meilleure_valeur:
                meilleure_valeur, meilleures = valeur, [action]
            elif valeur == meilleure_valeur:
                meilleures.append(action)
        return DEPARTAGES[self.departage](meilleures, self.rng)


@dataclass
class Aleatoire:
    """La politique uniforme sur `legal_actions()`. Le plancher absolu du protocole."""

    rng: random.Random

    def action(self, etat: State) -> int:
        """Une action legale tiree uniformement."""
        return self.rng.choice(etat.legal_actions())


def est_un_dos(cible: CartePosee, moi: int) -> bool:
    """Vrai si `cible` est un Espion adverse -- l'information que nul ne doit lire."""
    return cible.carte.role in ROLES_CACHES and cible.poseur != moi
