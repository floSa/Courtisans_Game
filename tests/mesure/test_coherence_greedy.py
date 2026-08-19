"""Le diagnostic d'incoherence du greedy : ce que sa specification disait mal.

Ecrits AVANT le diagnostic (regle 1 des conventions). Chaque attendu est calcule de tete depuis
la position construite, jamais en appelant le compteur teste.

Ce que ce module mesure, en une phrase : **la pose du greedy est evaluee avec ses Assassins
resolus conjointement, ses ciblages se decident un nœud a la fois.** L'audit croise a releve ce
defaut ; il est corrige dans la **description** de l'agent et non dans son code -- corriger le
code refait un autre agent et invalide M3 et M4 entiers.

Deux lectures, deux denominateurs, et c'est le meme piege que celui du paragraphe 6
------------------------------------------------------------------------------------
« 7,33 % des nœuds ou un Assassin reste en attente avec un argmax myope different » admet deux
lectures : la part **parmi les nœuds a Assassin en attente**, ou la part **parmi tous les nœuds
de ciblage**. Les deux sont mesurees et publiees separement, avec leur grain, parce qu'un chiffre
dont on ne sait pas de quoi il est la part n'est pas auditable.
"""

from __future__ import annotations

from courtisans.cards import Position, Role
from courtisans.engine import Engine, Phase
from mesure import coherence_greedy as coh
from mesure.instance import ENTRAINEMENT_3J
from mesure.trace import tracer
from tests.mesure.outils_comportements import banquet, ciblage, domaine, trace

CONFIG = ENTRAINEMENT_3J


def _noeud_incoherent(en_attente: bool):
    """Le nœud ou l'argmax myope est a egalite et l'argmax coherent strictement meilleur.

    La meme position que `tests/agents/test_greedy.py`, portee dans une trace :

      - `Assassin f3` au banquet en Estime -- l'Assassin **courant**, `d(f3) = +1` ;
      - `Assassin f3` (ex. 1) dans le domaine du joueur 1 -- l'Assassin **en attente**, et il
        vaut `+1` au joueur 1 puisque le proprietaire encaisse ;
      - `Neutre f1` au banquet en Estime -- `d(f1) = +1`, la **seule** cible du courant ;
      - `Noble f1` chez le joueur 0 : `+2` au joueur 0 ;
      - `Noble f1` (ex. 1) chez le joueur 1 : `+2` au joueur 1, seule cible de l'Assassin en
        attente.

    Scores `(2, 3, 0)`, ecart evalue `-1`. Tuer le `Neutre f1` fait tomber f1 en Indifference :
    les deux joueurs perdent leurs `+2`, l'ecart reste `-1`. **Myope : egalite a -1.**

    En prenant l'Assassin en attente en compte : apres un refus il tue le `Noble f1` du joueur 1,
    ecart `2 - 1 = +1` ; apres le meurtre, f1 est Indifferente et il n'a plus rien a gagner,
    ecart `-1`. **Coherent : refuser vaut +1, tuer vaut -1.**
    """
    courant = banquet(3, Role.ASSASSIN, Position.ESTIME, poseur=0)
    suivant = domaine(3, Role.ASSASSIN, proprietaire=1, poseur=0, exemplaire=1)
    cible = banquet(1, Role.NEUTRE, Position.ESTIME, poseur=1)
    plateau = (
        courant,
        suivant,
        cible,
        domaine(1, Role.NOBLE, proprietaire=0, poseur=0),
        domaine(1, Role.NOBLE, proprietaire=1, poseur=1, exemplaire=1),
    )
    return ciblage(
        numero=0,
        joueur=0,
        tour=1,
        cibles_connues=(cible,),
        dos_cibles=0,
        valeurs={0: -1, 1: -1},
        action=0,
        connues=plateau,
        assassins_en_attente=(suivant,) if en_attente else (),
    )


def test_le_diagnostic_compte_le_noeud_ou_les_deux_argmax_diffèrent():
    """Sur la position construite : 1 nœud sur 1, dans les deux lectures.

    L'argmax myope vaut `{tuer, refuser}` -- egalite a `-1` -- et l'argmax coherent `{refuser}`
    seul. Les deux ensembles diffèrent, **et** l'argmax myope contient une action que l'argmax
    coherent rejette : le greedy peut donc tirer le meurtre, qui est domine de 2 points.
    """
    une = trace((_noeud_incoherent(en_attente=True),))
    comptes = coh.mesurer_incoherence([une], CONFIG, sieges=[0])

    assert comptes["incoherence/argmax-differents"].succes == 1
    assert comptes["incoherence/argmax-differents"].total == 1
    assert comptes["incoherence/myope-non-optimal"].succes == 1
    assert comptes["incoherence/myope-non-optimal"].total == 1
    # La seconde lecture de la phrase de l'audit : la part parmi TOUS les nœuds de ciblage.
    assert comptes["incoherence/argmax-differents-tous-noeuds"].succes == 1
    assert comptes["incoherence/argmax-differents-tous-noeuds"].total == 1


def test_les_deux_denominateurs_portent_des_grains_differents():
    """Les deux lectures ne se soustraient pas l'une de l'autre, et le type le dit.

    C'est la meme discipline que la parade du paragraphe 6 : un taux porte son grain, et deux
    grains differents ne se comparent pas.
    """
    une = trace((_noeud_incoherent(en_attente=True),))
    comptes = coh.mesurer_incoherence([une], CONFIG, sieges=[0])
    parmi = comptes["incoherence/argmax-differents"].grain
    tous = comptes["incoherence/argmax-differents-tous-noeuds"].grain
    assert "en attente" in parmi
    assert parmi != tous


def test_un_noeud_sans_assassin_en_attente_ne_compte_pas_au_denominateur():
    """Sans Assassin en attente, la question ne se pose pas -- et le denominateur est **vide**.

    Un denominateur nul rend `None`, pas `0` : « l'occasion ne s'est pas presentee » n'est pas
    « l'incoherence n'apparait jamais ». Le nœud reste compte parmi **tous** les nœuds de
    ciblage, ce qui est precisement pourquoi les deux lectures ne donnent pas le meme chiffre.
    """
    une = trace((_noeud_incoherent(en_attente=False),))
    comptes = coh.mesurer_incoherence([une], CONFIG, sieges=[0])
    assert comptes["incoherence/argmax-differents"].total == 0
    assert comptes["incoherence/argmax-differents"].taux() is None
    assert comptes["incoherence/argmax-differents-tous-noeuds"].total == 1
    assert comptes["incoherence/argmax-differents-tous-noeuds"].succes == 0


def test_le_diagnostic_ne_compte_que_les_sieges_mesures():
    """Le meme nœud, attribue au siege 1 : mesurer le siege 0 ne doit rien voir.

    Tout compteur de ce depot se teste sur au moins **deux compositions de sieges** -- c'est
    l'enseignement des deux defauts de B1, ou le nombre de sieges mesures n'etait exerce par
    aucun cas.
    """
    from dataclasses import replace

    noeud = replace(_noeud_incoherent(en_attente=True), joueur=1)
    une = trace((noeud,))
    assert coh.mesurer_incoherence([une], CONFIG, sieges=[0])[
        "incoherence/argmax-differents-tous-noeuds"
    ].total == 0
    assert coh.mesurer_incoherence([une], CONFIG, sieges=[0, 1, 2])[
        "incoherence/argmax-differents-tous-noeuds"
    ].total == 1


def test_la_trace_d_une_vraie_partie_enregistre_les_assassins_en_attente():
    """Le releve, verifie a travers le moteur et non seulement sur une trace ecrite.

    Le moteur expose `assassins_en_attente()`, dont le premier element est l'Assassin courant.
    La trace enregistre **la suite** : autant de nœuds de ciblage consecutifs qu'il reste
    d'Assassins dans le bloc, la file decroissant de un a chaque nœud. Reconstruire cette file
    depuis les blocs de pose aurait ete une hypothese de plus a verifier ; la relever du moteur
    n'en est pas une.
    """
    import random

    from mesure.partie import politique_uniforme

    vues = 0
    for donne in range(30):
        alea = random.Random(9_000_000 + donne)
        une = tracer(
            Engine(CONFIG).reset(donne),
            [politique_uniforme(alea) for _ in range(CONFIG.joueurs)],
            seed=donne,
        )
        precedent = None
        for decision in une.decisions:
            if decision.phase is not Phase.CIBLAGE:
                assert decision.assassins_en_attente == ()
                precedent = None
                continue
            if precedent is not None:
                # Deux nœuds de ciblage consecutifs du meme joueur : la file a perdu un
                # element, et c'est l'Assassin qui vient de se resoudre.
                assert len(decision.assassins_en_attente) == len(precedent) - 1
                vues += 1
            precedent = decision.assassins_en_attente
    # Sans ce cas, le test passerait sur des parties ou aucun bloc ne porte deux Assassins et
    # ne verifierait rien du tout.
    assert vues > 0, "aucun bloc a deux Assassins dans les 30 donnes : le cas n'est pas exerce"
