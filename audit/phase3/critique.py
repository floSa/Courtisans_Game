"""Le diagnostic du critique, eprouve -- point d) du prompt d'audit.

Trois mesures, dans l'ordre ou elles doivent etre lues :

1. la variance des retours SUR LES NŒUDS COLLECTES -- le denominateur exact de la MSE
   journalisee, et non celui d'un echantillon de parties ;
2. le PLANCHER de la perte de valeur : `E[Var(R | etat complet)]` sous la politique de
   l'agent, estime par rejeu Monte-Carlo du MEME etat. Aucun critique, meme parfait et
   meme voyant plus que l'info-set, ne peut descendre sous ce nombre ;
3. la meme chose par profondeur de nœud : si la variance residuelle s'effondre en fin de
   partie, une perte plate sur tous les nœuds ne peut pas s'expliquer par « le jeu est
   impredictible ».
"""
from __future__ import annotations
import random, statistics, sys
import torch
from agents import reseau as reseau_module
from agents.politique_reseau import charger
from courtisans.engine import Engine, Phase
from courtisans.infoset import tenseur
from mesure.instance import ENTRAINEMENT_3J

CONFIG = ENTRAINEMENT_3J


def jouer_depuis(etat, modele, alea):
    e = etat.clone()
    while e.phase() is not Phase.TERMINAL:
        if e.phase() is Phase.CHANCE:
            e.apply(e.legal_actions()[0])
            continue
        j = e.current_player()
        e.apply(reseau_module.choisir(modele, tenseur(e, j), e.legal_actions(), alea))
    return e.returns()


def collecter(modele, donnes, graine=700_000):
    """Les nœuds d'un self-play a trois copies : (profondeur, siege, etat clone, retour)."""
    noeuds = []
    for d in donnes:
        etat = Engine(CONFIG).reset(d)
        alea = random.Random(graine + d)
        trace = []
        prof = 0
        while etat.phase() is not Phase.TERMINAL:
            if etat.phase() is Phase.CHANCE:
                etat.apply(etat.legal_actions()[0])
                continue
            j = etat.current_player()
            trace.append((prof, j, etat.clone()))
            etat.apply(reseau_module.choisir(modele, tenseur(etat, j), etat.legal_actions(), alea))
            prof += 1
        gains = etat.returns()
        for prof_, j, e in trace:
            noeuds.append((prof_, j, e, gains[j]))
    return noeuds


if __name__ == "__main__":
    modele = charger("models/phase3/final.pt", 205, 24)
    n_donnes = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    rejeux = int(sys.argv[2]) if len(sys.argv) > 2 else 24

    noeuds = collecter(modele, range(700_000, 700_000 + n_donnes))
    retours = [r for _, _, _, r in noeuds]
    var_noeuds = statistics.pvariance(retours)
    print(f"nœuds collectes            : {len(noeuds)} sur {n_donnes} parties de self-play a 3 copies")
    print(f"moyenne des retours        : {statistics.fmean(retours):+.4f}")
    print(f"VARIANCE des retours       : {var_noeuds:.4f}   <- le denominateur de la MSE")
    par_partie = [r for i, (_, _, _, r) in enumerate(noeuds)]
    print(f"  (pour memoire, variance sur les gains de SIEGE, 3 par partie : ", end="")
    sieges = {}
    for prof, j, e, r in noeuds:
        sieges[(id(e), j)] = r
    print(f"{statistics.pvariance(list(sieges.values())):.4f})")

    # 2 et 3 : le plancher, par rejeu du MEME etat
    alea = random.Random(31337)
    echantillon = alea.sample(noeuds, min(400, len(noeuds)))
    residus = []
    par_profondeur: dict[int, list[float]] = {}
    for prof, j, etat, _ in echantillon:
        tirages = [jouer_depuis(etat, modele, random.Random(alea.randrange(10**9)))[j]
                   for _ in range(rejeux)]
        v = statistics.pvariance(tirages)
        residus.append(v)
        par_profondeur.setdefault(prof, []).append(v)
    plancher = statistics.fmean(residus)
    print(f"\nPLANCHER E[Var(R | etat complet)] : {plancher:.4f}  "
          f"({len(echantillon)} etats x {rejeux} rejeux)")
    print(f"part de la variance IRREDUCTIBLE  : {100*plancher/var_noeuds:.1f} %")
    print(f"part maximale explicable          : {100*(1-plancher/var_noeuds):.1f} %")
    print("\nvariance residuelle par profondeur de nœud :")
    for prof in sorted(par_profondeur):
        v = par_profondeur[prof]
        print(f"  profondeur {prof:2d} : {statistics.fmean(v):.4f}   ({len(v)} etats)")
