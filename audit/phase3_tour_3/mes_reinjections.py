"""Tour 3 : les sept corrections eprouvees, et ce que leur rendu publie.

Chaque injection VERIFIE d'abord que son ancre existe. Une injection qui ne s'applique pas
rend un cas vert sans avoir rien injecte -- c'est la famille meme que ce tour poursuit, et
elle m'a eu une fois en ecrivant ce fichier.

    uv run python audit/phase3_tour_3/mes_reinjections.py
"""

from __future__ import annotations

import random

from agents import campagne as C
from mesure import bootstrap as boot
from mesure import comportements as comp
from mesure import dimensionnement as dim
from mesure import phase3, phase3_mesure as pm, rapport_phase3 as rap


def _c(nom: str, succes: int, total: int) -> comp.Compte:
    return comp.Compte(nom, succes, total, "occasions", "publique")


def _une(nom: str, agent, base, budget: int = 6000, npa: int = 6000, npb: int = 6000):
    return pm.comparer({nom: _c(nom, *agent)}, {nom: _c(nom, *base)}, npa, npb, budget=budget)[0]


def a_les_quatre_cas_degeneres() -> None:
    """A. Les quatre cas sont-ils tranches, et que PUBLIE-t-on de chacun ?"""
    print("== A. les quatre cas de taux degenere, et la phrase publiee ==")
    for libelle, agent, base in (
        ("zero du cote BASE  ", (1368, 3814), (0, 1967)),
        ("zero du cote AGENT ", (0, 1967), (1368, 3814)),
        ("LES DEUX a zero    ", (0, 3814), (0, 1967)),
        ("CENT du cote agent ", (3814, 3814), (600, 1967)),
    ):
        r = _une("X", agent, base)
        lignes: list[str] = []
        rap.section_comportements(lignes, [r], 6000)
        cellule = next(x for x in lignes if x.startswith("| `X`")).split("|")[-2].strip()
        print(f"  {libelle} separable={str(r.separable):<5} regle={r.regle}")
        print(f"    publie : {cellule}")


def a_le_rendu_leve() -> None:
    """A. Le rendu leve-t-il sur une ligne qu'aucune regle n'a tranchee ?"""
    print("\n== A. une ligne non conclue, fabriquee ==")
    r = _une("Z", (1000, 3814), (500, 1967), budget=1)
    assert r.separable is None and r.exclu is None, "l'ancre a bouge : la ligne est tranchee"
    try:
        rap.section_comportements([], [r], 6000)
        print("  !!! LE RENDU N'A PAS LEVE")
    except ValueError as erreur:
        print("  LEVE :", str(erreur)[:130])


def c_le_garde_fou_voit_les_chutes() -> None:
    """C. Mon effondrement du tour 2 declenche-t-il maintenant ?"""
    print("\n== C. le garde-fou face aux trois formes ==")
    alea = random.Random(0)
    avant = [alea.uniform(0.0, 1.0) for _ in range(C.DONNES_GARDE_FOU)]
    for libelle, apres in (
        ("effondrement -20 pt", [max(0.0, x - 0.20) for x in avant]),
        ("progres      +20 pt", [min(1.0, x + 0.20) for x in avant]),
        ("stagnation exacte  ", list(avant)),
    ):
        ap = boot.bootstrap_apparie_par_donne(
            avant, apres, phase3.RECHANTILLONS, random.Random(1),
            risque=0.01 / C.CHECKPOINTS_ATTENDUS,
        )
        print(
            f"  {libelle}  ecart {ap.moyenne:+.4f} IC [{ap.intervalle[0]:+.4f} ; "
            f"{ap.intervalle[1]:+.4f}]  etabli={ap.etabli}  progres={ap.progres_etabli}"
            f"  -> DECLENCHE {not ap.progres_etabli}"
        )


def le_risque_des_bornes() -> None:
    """Le point du pilote : ces bornes sont UNILATERALES sous un intitule « 99 % »."""
    print("\n== les deux lectures d'un « 99 % » ==")
    for total in (1967, 10382):
        uni = 1 - 0.01 ** (1 / total)
        bil = 1 - 0.005 ** (1 / total)
        publie = pm.borne_haute_exacte_d_un_zero(total)
        print(
            f"  0/{total:<6} unilaterale {uni * 100:.4f} %   bilaterale {bil * 100:.4f} %   "
            f"publie {publie * 100:.4f} %  -> {'UNILATERALE' if abs(publie - uni) < 1e-12 else '?'}"
        )
    print(f"  cote normal : quantile_bilateral(0,01) = {dim.quantile_bilateral(dim.RISQUE):.4f}"
          f" -- 0,5 % par queue, contre 1 % du cote exact")
    exacte = pm.separer_un_taux_degenere(_c("X", 1368, 3814), _c("X", 0, 1967))
    print(f"  ce que le code confronte : borne basse de l'agent {exacte.borne_de_l_autre * 100:.2f} %"
          f" contre {exacte.borne * 100:.4f} % -- le rapport publie le point, 35.87 %")


def f_les_grandeurs_sont_mesurees() -> None:
    """F. `portee_minimale` recoit-elle des grandeurs mesurees ?"""
    import json
    from statistics import fmean
    from mesure import phase3_courbe

    print("\n== F. portee_minimale, sur des grandeurs mesurees ==")
    jalons = [json.loads(x) for x in open("models/phase3/journal.jsonl") if x.strip()]
    consecutifs = phase3_courbe.ecarts(jalons, 1, 0.01 / C.CHECKPOINTS_ATTENDUS)
    demi = [(e.intervalle[1] - e.intervalle[0]) / 2 * 100 for e in consecutifs]
    progres = (jalons[-1]["part_fractionnee"] - jalons[0]["part_fractionnee"]) * 100 / (
        len(jalons) - 1
    )
    print(f"  demi-largeur appariee moyenne {fmean(demi):.4f} pt (min {min(demi):.4f}"
          f" max {max(demi):.4f}), progres {progres:.4f} pt")
    print(f"  portee_minimale = {C.portee_minimale(fmean(demi), progres)}"
          f"   PORTEE_DU_GARDE_FOU = {C.PORTEE_DU_GARDE_FOU}")


def le_balayage_du_tour_2() -> None:
    """Son defaut neuf le plus instructif, verifie."""
    print("\n== le balayage du tour 2 ne visitait-il qu'une branche ? ==")
    for libelle, plage in (
        ("tour 2 : range(2900, 3101, 20)", range(2900, 3101, 20)),
        ("tour 3 : range(2700, 3301, 50)", range(2700, 3301, 50)),
    ):
        sep = non = 0
        for succes in plage:
            r = pm.comparer(
                {"X": comp.Compte("X", 3000, 6000, "parties", "publique")},
                {"X": comp.Compte("X", succes, 6000, "parties", "publique")},
                6000, 6000, budget=6000,
            )[0]
            if r.ecart == 0 or r.exclu is not None:
                continue
            sep, non = (sep + 1, non) if r.separable else (sep, non + 1)
        print(f"  {libelle} -> {sep} separables / {non} non separables")


if __name__ == "__main__":
    a_les_quatre_cas_degeneres()
    a_le_rendu_leve()
    c_le_garde_fou_voit_les_chutes()
    le_risque_des_bornes()
    f_les_grandeurs_sont_mesurees()
    le_balayage_du_tour_2()
