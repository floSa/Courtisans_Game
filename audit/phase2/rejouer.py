"""Rejoue les quatre mesures de la phase 2 avec le code de l'auditeur, et ecrit un JSON.

Aucune ligne du constructeur n'est importee. Les chiffres produits ici sont compares aux
siens **apres** : une concordance vaut d'etre dite autant qu'un desaccord.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from audit.phase2 import comportements as B
from audit.phase2.campagne import Issue, aleatoires, mesurer_m1, mesurer_m2, mesurer_m3
from audit.phase2.greedy import Greedy
from audit.phase2.stats import clopper_pearson, pouvoir
from audit.phase2.trace import jouer, restreindre
from courtisans.engine import Engine
from tests.audit_phase2.outils import INSTANCE

COMPTEURS = {
    "B1": lambda t: B.b1(t),
    "B1.obscurite": lambda t: B.b1(t, seuil_final="obscurite"),
    "B1.cadeau": lambda t: B.b1(t, exiger_cadeau=True),
    "B2.bascule": B.b2_bascule,
    "B3": lambda t: B.b3(t),
    "B3.siege": lambda t: B.b3(t, vue="siege"),
    "B4": lambda t: B.b4(t),
    "B4.litteral": lambda t: B.b4(t, denominateur="tous_noeuds"),
    "B4.defavorable": B.b4_defavorable,
    "B4.favorable": B.b4_favorable,
    "B5": B.b5,
    "B7": B.b7,
    "B7.occasions": B.occasions_b7,
}
ZONES_B2 = ("banquet_estime", "banquet_disgrace", "domaine_propre", "domaine_adverse")


def _taux(taux: B.Taux) -> dict:
    """Un comptage serialise, denominateur et unite compris."""
    bornes = (
        clopper_pearson(taux.numerateur, taux.denominateur)
        if taux.denominateur > 0
        else None
    )
    return {
        "nom": taux.nom,
        "unite": taux.unite,
        "k": taux.numerateur,
        "n": taux.denominateur,
        "taux": taux.valeur,
        "ic95": bornes,
        "texte": taux.texte(),
    }


def compteurs(traces, sieges=None) -> dict:
    """Les treize comptages, cumules sur les parties, restreints a `sieges` si donne."""
    vues = [restreindre(t, sieges) if sieges is not None else t for t in traces]
    resultat = {
        nom: _taux(B.cumule([fonction(t) for t in vues]))
        for nom, fonction in COMPTEURS.items()
    }
    for zone in ZONES_B2:
        resultat[f"B2.{zone}"] = _taux(
            B.cumule([B.b2_distribution(t)[zone] for t in vues])
        )
    return resultat


def main() -> None:
    """Joue tout, ecrit le JSON sur la sortie demandee."""
    sortie = Path(sys.argv[1])
    n_m1 = int(sys.argv[2]) if len(sys.argv) > 2 else 10_000
    n_m3 = int(sys.argv[3]) if len(sys.argv) > 3 else 1_000
    engine = Engine(INSTANCE)
    greedy = Greedy()
    tout: dict = {"instance": "entrainement-3j", "n_m1": n_m1, "n_m3": n_m3}

    depart = time.time()
    m1 = mesurer_m1(engine, range(n_m1), apparier=False)
    tout["m1_non_apparie"] = {
        "parties": m1.parties,
        "donnes": m1.donnes,
        "strictes": m1.strictes,
        "partagees": m1.partagees,
        "gains": m1.gains,
        "egalites": m1.parties_avec_egalite,
        "nulle_stricte": m1.nulle_stricte,
        "ic_strictes": [clopper_pearson(k, m1.parties) for k in m1.strictes],
        "ic_partagees": [clopper_pearson(k, m1.parties) for k in m1.partagees],
    }
    tout["duree_m1"] = round(time.time() - depart, 1)

    depart = time.time()
    donnes = n_m1 // 6
    m1b = mesurer_m1(engine, range(donnes), apparier=True)
    tout["m1_apparie"] = {
        "parties": m1b.parties,
        "donnes": m1b.donnes,
        "strictes": m1b.strictes,
        "partagees": m1b.partagees,
        "gains": m1b.gains,
        "egalites": m1b.parties_avec_egalite,
        "nulle_stricte": m1b.nulle_stricte,
        "ic_strictes": [clopper_pearson(k, m1b.parties) for k in m1b.strictes],
    }
    tout["duree_m1_apparie"] = round(time.time() - depart, 1)

    depart = time.time()
    issues = [
        Issue.depuis(jouer(engine, seed, aleatoires(seed, 3))) for seed in range(n_m1)
    ]
    m2 = mesurer_m2(issues, 3)
    tout["m2"] = {
        "parties": m2.parties,
        "variance_par_siege": m2.variance_par_siege,
        "variance_toutes_places": m2.variance_toutes_places,
        "variance_ecart": m2.variance_ecart,
        "variance_gain": m2.variance_gain,
        "moyenne_par_siege": m2.moyenne_par_siege,
        "etendue": list(m2.etendue_scores),
        "scores_distincts": m2.scores_distincts,
    }
    tout["duree_m2"] = round(time.time() - depart, 1)

    depart = time.time()
    m3, traces_m3 = mesurer_m3(engine, range(n_m3), greedy)
    tout["m3"] = {
        "donnes": m3.donnes,
        "rotations": m3.rotations,
        "strictes": m3.victoires_strictes,
        "partagees": m3.victoires_partagees,
        "gain_moyen": m3.gain_total / m3.rotations,
        "par_siege": m3.par_siege,
        "ic_strictes": clopper_pearson(m3.victoires_strictes, m3.rotations),
        "ic_partagees": clopper_pearson(m3.victoires_partagees, m3.rotations),
    }
    tout["duree_m3"] = round(time.time() - depart, 1)

    # M4, deux compositions de table : le greedy entre greedys, et le greedy seul contre
    # deux aleatoires. La ligne de base n'est pas la meme, et le protocole ne dit pas
    # laquelle il veut.
    depart = time.time()
    traces_gvg = [jouer(engine, seed, [greedy] * 3) for seed in range(n_m3)]
    tout["m4_greedy_x3"] = compteurs(traces_gvg)
    tout["m4_greedy_seul_siege0"] = compteurs(
        [t for i, t in enumerate(traces_m3) if i % 3 == 0], sieges=[0]
    )
    tout["duree_m4"] = round(time.time() - depart, 1)

    # B6 : profils du premier et du dernier tour, avec le plancher de nullite.
    premier, dernier, n_premier, n_dernier = B.b6_profils(traces_gvg, INSTANCE.tours)
    moyenne, quantile = B.plancher_tv(traces_gvg, tour=0, graine=11)
    tout["m4_b6"] = {
        "distance_tv": B.distance_tv(premier, dernier),
        "n_premier_tour": n_premier,
        "n_dernier_tour": n_dernier,
        "plancher_moyen": moyenne,
        "plancher_q95": quantile,
        "profil_premier": {f"{k[0].name}/{k[1].name}": v for k, v in premier.items()},
        "profil_dernier": {f"{k[0].name}/{k[1].name}": v for k, v in dernier.items()},
    }

    # Le pouvoir discriminant de chaque compteur au budget annonce de la phase 3.
    # 1 000 parties appariees, l'agent occupant un siege : ses propres decisions seules.
    facteur = 1000 / n_m3
    tout["pouvoir_phase3"] = {}
    for nom, mesure in tout["m4_greedy_x3"].items():
        if mesure["n"] == 0:
            tout["pouvoir_phase3"][nom] = None
            continue
        n_agent = max(1, round(mesure["n"] * facteur / 3))
        p = pouvoir(nom, mesure["k"], mesure["n"], n_agent)
        tout["pouvoir_phase3"][nom] = {
            "taux": p.taux_mesure,
            "n_base": p.n_base,
            "n_agent_phase3": p.n_agent,
            "ecart_detectable": p.ecart_detectable,
            "aveugle_par_le_bas": p.aveugle_par_le_bas,
            "borne_haute_agent_a_zero": p.borne_zero,
            "separable_de_zero": p.separable_de_zero,
        }

    # Le departage : combien de decisions le greedy laisse-t-il decider a sa regle ?
    exaequo = {"pose": [0, 0], "ciblage": [0, 0], "pose_par_tour": {}}
    for seed in range(min(200, n_m3)):
        etat = engine.reset(seed)
        tour = 0
        poses = 0
        while not etat.is_terminal():
            sommet, legales = greedy.multiplicite_exaequo(etat)
            cle = "pose" if legales > 2 or etat.phase().name == "POSE" else "ciblage"
            cle = "pose" if etat.phase().name == "POSE" else "ciblage"
            exaequo[cle][0] += sommet
            exaequo[cle][1] += legales
            if cle == "pose":
                seau = exaequo["pose_par_tour"].setdefault(tour, [0, 0, 0])
                seau[0] += sommet
                seau[1] += legales
                seau[2] += 1
                poses += 1
                if poses == 3:
                    poses = 0
                    tour += 1
            etat.apply(greedy.action(etat))
    tout["exaequo"] = exaequo

    sortie.write_text(json.dumps(tout, indent=1, default=str), encoding="utf-8")
    print(f"ecrit : {sortie}")


if __name__ == "__main__":
    main()
