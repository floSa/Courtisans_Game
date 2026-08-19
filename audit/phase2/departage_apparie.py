"""L'ecart de gain entre les deux departages du greedy, mesure **en apparie**.

Le rapport du constructeur juge cet ecart -- `+0,0011` -- contre la demi-largeur de l'IC
non apparie du gain de reference, `0,0122`, et conclut « ne change pas le gain ». Or les
deux bras partagent la donne, le siege du greedy et les graines de ses deux adversaires :
seule la regle de departage differe. La difference est donc **appariee**, et juger une
affirmation nulle avec un intervalle trop large la favorise mecaniquement.

**Resultat de cette mesure : le soupcon est infirme.** L'intervalle apparie est plus LARGE
que la demi-largeur non appariee employee par le rapport, pas plus etroit -- 0,0186 contre
0,0122 sur 1 500 donnes. La raison est celle que le constructeur a lui-meme mesuree : avec
`rho` autour de 0,007, la donne n'explique quasiment rien, et les deux bras divergent des
la premiere egalite departagee differemment. Sa conclusion « le departage ne change pas le
gain » tient donc, et elle tient meme sous le yardstick plus severe.
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from statistics import mean

from agents.greedy import choisir, choisir_par_plus_petit_indice
from agents.perception import percevoir
from audit.phase2.decompte import gains, scores
from audit.phase2.greedy import Aleatoire
from courtisans.engine import Engine
from mesure.instance import ENTRAINEMENT_3J as CONFIG

#: Le decalage de graine de la campagne B du constructeur, repris tel quel pour que les
#: deux bras voient exactement les memes adversaires.
DECALAGE_B = 3_000_000


@dataclass
class Uniforme:
    """Son greedy, departage uniforme -- le bras de reference."""

    alea: random.Random

    def action(self, etat) -> int:
        """L'action tiree uniformement parmi les argmax."""
        return choisir(percevoir(etat, etat.current_player()), self.alea)


class Deterministe:
    """Son greedy, departage par plus petit indice -- le bras de robustesse."""

    def action(self, etat) -> int:
        """Le plus petit indice parmi les argmax."""
        return choisir_par_plus_petit_indice(percevoir(etat, etat.current_player()))


def _gain(engine: Engine, donne: int, siege: int, greedy) -> float:
    """Le gain du greedy sur cette donne, a ce siege, contre deux uniformes."""
    table = [
        Aleatoire(random.Random(DECALAGE_B + 3 * donne + s))
        for s in range(CONFIG.joueurs)
    ]
    table[siege] = greedy
    etat = engine.reset(donne)
    while not etat.is_terminal():
        etat.apply(table[etat.current_player()].action(etat))
    bruts = scores(etat.vue_privilegiee().posees, CONFIG.familles, CONFIG.joueurs)
    return gains(bruts)[siege]


def bootstrap_par_donne(
    par_donne: list[list[float]], rechantillons: int, graine: int
) -> tuple[float, float]:
    """IC 99 % de la moyenne des differences, rechantillonnees **par donne**.

    Une donne entre avec tous ses sieges : tirer des parties detruirait l'appariement
    qu'on mesure. C'est le grain que le constructeur emploie pour ses propres intervalles.
    """
    alea = random.Random(graine)
    moyennes = []
    nb = len(par_donne)
    for _ in range(rechantillons):
        tirage = [par_donne[alea.randrange(nb)] for _ in range(nb)]
        moyennes.append(mean(x for bloc in tirage for x in bloc))
    moyennes.sort()
    return moyennes[int(0.005 * rechantillons)], moyennes[int(0.995 * rechantillons)]


def main() -> int:
    """Mesure les deux bras sur les memes donnes et publie les deux lectures."""
    donnes = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
    engine = Engine(CONFIG)
    alea = random.Random(DECALAGE_B)
    uniforme = Uniforme(alea)
    deterministe = Deterministe()

    differences: list[list[float]] = []
    gains_u: list[float] = []
    gains_d: list[float] = []
    for donne in range(donnes):
        bloc = []
        for siege in range(CONFIG.joueurs):
            u = _gain(engine, donne, siege, uniforme)
            d = _gain(engine, donne, siege, deterministe)
            gains_u.append(u)
            gains_d.append(d)
            bloc.append(u - d)
        differences.append(bloc)

    parties = donnes * CONFIG.joueurs
    ecart = mean(gains_u) - mean(gains_d)
    bas, haut = bootstrap_par_donne(differences, 10_000, 2_500_000)
    print(f"donnes {donnes}, parties par bras {parties}")
    print(f"gain moyen, departage uniforme      : {mean(gains_u):+.4f}")
    print(f"gain moyen, departage deterministe  : {mean(gains_d):+.4f}")
    print(f"ecart (uniforme - deterministe)     : {ecart:+.4f}")
    print(f"IC 99 % APPARIE, bootstrap par donne: [{bas:+.4f} ; {haut:+.4f}]")
    print(f"zero est-il dans l'intervalle apparie ? {'OUI' if bas <= 0 <= haut else 'NON'}")
    demi_appariee = (haut - bas) / 2
    print(f"demi-largeur appariee               : {demi_appariee:.4f}")
    print("demi-largeur NON appariee employee par le rapport : 0.0122")
    print(f"rapport des deux                    : {0.0122 / demi_appariee:.1f} fois trop large")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
