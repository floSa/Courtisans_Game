"""Les reinjections du tour 2 : chaque parade annoncee, eprouvee sur la faute qu'elle nomme.

Aucune fonction de `mesure/phase3*.py` n'est employee pour produire un chiffre de reference :
les nombres publies dans le verdict sont recalcules ici a partir des comptes bruts.

    uv run python audit/phase3_tour_2/mes_reinjections.py
"""

from __future__ import annotations

import math
import random
from statistics import NormalDist

from mesure import comportements as comp
from mesure import dimensionnement as dim
from mesure import phase3, phase3_mesure
from mesure import bootstrap as boot
from agents import campagne as C


def _compte(nom: str, succes: int, total: int) -> comp.Compte:
    return comp.Compte(nom, succes, total, "occasions", "publique")


def les_deux_zeros_changent_de_statut() -> None:
    """DEFAUT NEUF A. Le rapport ecrit « aucune ligne ne change de statut ». Deux changent."""
    print("== A. les deux zeros absolus, avec leur VRAI zero ==")
    for nom, (sa, na), (sb, nb), tour_1 in (
        ("B4-contre-nature", (1368, 3814), (0, 1967), "separable, detectable 3,75 %"),
        ("B4-meurtre-couteux", (298, 8131), (0, 10382), "separable, detectable 1,01 %"),
    ):
        r = phase3_mesure.comparer(
            {nom: _compte(nom, sa, na)}, {nom: _compte(nom, sb, nb)}, 6000, 6000, budget=6000
        )[0]
        exacte = 1 - 0.01 ** (1 / nb)
        print(
            f"  {nom}\n"
            f"    tour 1 : {tour_1}\n"
            f"    tour 2 : ecart {r.ecart:+.4f}  detectable {r.detectable}  "
            f"separable {r.separable}  parties_requises {r.parties_requises}\n"
            f"    borne haute EXACTE a 99 % sur {sb}/{nb} : {exacte:.6%} "
            f"-- contre {sa / na:.2%} chez l'agent"
        )


def le_test_qui_maquille_son_entree() -> None:
    """DEFAUT NEUF B. Le cas qui soutient la phrase substitue 1 au 0 des deux lignes."""
    print("\n== B. le meme couple, avec le 1 que le test substitue au 0 ==")
    for nom, (sa, na), (sb, nb) in (
        ("B4-contre-nature", (1368, 3814), (1, 1967)),
        ("B4-meurtre-couteux", (298, 8131), (1, 10382)),
    ):
        r = phase3_mesure.comparer(
            {nom: _compte(nom, sa, na)}, {nom: _compte(nom, sb, nb)}, 6000, 6000, budget=6000
        )[0]
        print(f"  {nom} : separable {r.separable}  detectable {r.detectable:.4f}")


def le_garde_fou_ne_voit_pas_un_effondrement() -> None:
    """DEFAUT NEUF C. La regle v5 ne se declenche pas sur un ecart etabli NEGATIF."""
    print("\n== C. le garde-fou v5 face a un agent qui s'effondre ==")
    alea = random.Random(0)
    avant = [alea.uniform(0.0, 1.0) for _ in range(C.DONNES_GARDE_FOU)]
    for libelle, apres in (
        ("effondrement de 20 points", [max(0.0, x - 0.20) for x in avant]),
        ("agent parfaitement plat", list(avant)),
    ):
        ap = boot.bootstrap_apparie_par_donne(
            avant, apres, phase3.RECHANTILLONS, random.Random(1),
            risque=0.01 / C.CHECKPOINTS_ATTENDUS,
        )
        ecart = (ap.moyenne, *ap.intervalle)
        # La regle telle qu'elle est ecrite dans `agents/campagne.py`, recopiee sans rien changer.
        declenche = not (ecart[1] > 0.0 or ecart[2] < 0.0)
        print(
            f"  {libelle:<26} ecart {ecart[0]:+.4f}  IC [{ecart[1]:+.4f} ; {ecart[2]:+.4f}]  "
            f"etabli {ap.etabli}  -> DECLENCHE {declenche}"
        )


def les_parties_requises_refaites() -> None:
    """Ma reconstruction du nombre publie par chaque ligne non separable."""
    print("\n== les `parties_requises` publiees, refaites sans phase3_mesure ==")
    quantile = NormalDist().inv_cdf(1 - dim.RISQUE / 2) + NormalDist().inv_cdf(dim.PUISSANCE)
    lignes = (
        ("B1-collectif", (4222, 6000), (4332, 6000), 14220),
        ("B1-strict", (1683, 6000), (1712, 6000), 202842),
        ("B7-lumiere", (2464, 24000), (2304, 24000), 11754),
        ("B7-occasions", (195, 24000), (148, 24000), 10802),
        ("B7-gaspillage", (24, 24000), (19, 24000), 120418),
        ("B7-gaspillage-vraie", (32, 24000), (24, 24000), 61242),
    )
    for nom, (sa, na), (sb, nb), publie in lignes:
        p_a, p_b = sa / na, sb / nb
        u_a, u_b = na / 6000, nb / 6000
        ecart = p_a - p_b
        facteur = p_a * (1 - p_a) / u_a + p_b * (1 - p_b) / u_b
        mien = max(1, math.ceil((quantile / ecart) ** 2 * facteur))
        print(f"  {nom:<22} mien {mien:>7}  publie {publie:>7}  "
              f"{'OK' if mien == publie else '<-- DIVERGE'}")


if __name__ == "__main__":
    les_deux_zeros_changent_de_statut()
    le_test_qui_maquille_son_entree()
    le_garde_fou_ne_voit_pas_un_effondrement()
    les_parties_requises_refaites()
