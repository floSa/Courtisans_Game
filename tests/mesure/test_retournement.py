"""Les quatre definitions du retournement, sur des suites de statuts ecrites a la main.

Chaque attendu de ce fichier est calcule **de tete**, a partir des enonces du paragraphe 2.2
de `mesure/hypothese_et_instrument.md`, et jamais en faisant tourner le compteur. Un
compteur teste contre lui-meme ne teste rien.

Rappel des enonces, sur la suite `S` des statuts d'une famille, `s_0` etant le statut du
plateau vide, donc Indifferente :

- **R0** -- toute transition : il existe `t` tel que `s_t != s_{t-1}`.
- **R1** -- inversion de signe : dans `S` privee de ses Indifferente, deux valeurs
  consecutives ont des signes opposes.
- **R2** -- perte d'acquis : il existe `t` tel que `s_{t-1} != Indifferente` et
  `s_t != s_{t-1}`.
- **R3** -- divergence finale : le premier statut non-Indifferent `p` existe, et `s_T != p`.
"""

from __future__ import annotations

from itertools import product

import pytest

from courtisans.rules import Statut
from mesure.retournement import Retournements, analyser_suite, evenements_r2

IND = Statut.INDIFFERENTE
LUM = Statut.LUMIERE
OBS = Statut.OBSCURITE


CAS = [
    # (intitule, suite, r0, r1, r2, r3)
    ("famille jamais posee au banquet", [IND], False, False, False, False),
    ("famille posee une fois, en Estime", [IND, LUM], True, False, False, False),
    ("famille posee tard", [IND, IND, IND, LUM], True, False, False, False),
    ("Lumiere renforcee", [IND, LUM, LUM], True, False, False, False),
    ("Lumiere annulee", [IND, LUM, IND], True, False, True, True),
    ("Obscurite annulee", [IND, OBS, IND, IND], True, False, True, True),
    ("Lumiere annulee puis inversee", [IND, LUM, IND, OBS], True, True, True, True),
    ("inversion directe", [IND, LUM, OBS], True, True, True, True),
    # Le contre-exemple qui interdit de supposer R1 => R3 : le signe s'est inverse deux
    # fois, donc R1 se declenche, mais le statut final egale le premier statut atteint.
    ("aller-retour de signe", [IND, LUM, OBS, LUM], True, True, True, False),
    # R2 sans R1 ni R3 : la famille perd son acquis, le recupere, et ne change jamais de
    # signe. C'est le cas que R1 rate et que le paragraphe 2.2 des regles vise.
    ("Lumiere annulee puis retrouvee", [IND, LUM, IND, LUM], True, False, True, False),
    ("Obscurite maintenue apres detour", [IND, OBS, IND, OBS], True, False, True, False),
    ("plateau vide jusqu'au bout", [IND, IND, IND, IND], False, False, False, False),
]


@pytest.mark.parametrize(
    ("intitule", "suite", "r0", "r1", "r2", "r3"),
    CAS,
    ids=[cas[0] for cas in CAS],
)
def test_les_quatre_definitions_sur_une_suite_ecrite_a_la_main(
    intitule: str, suite: list[Statut], r0: bool, r1: bool, r2: bool, r3: bool
) -> None:
    """Le compteur rend exactement ce qu'on a calcule de tete."""
    assert analyser_suite(suite) == Retournements(r0=r0, r1=r1, r2=r2, r3=r3), intitule


def test_une_suite_vide_est_refusee() -> None:
    """Une suite sans meme son statut initial ne decrit aucune famille."""
    with pytest.raises(ValueError, match="au moins un statut"):
        analyser_suite([])


def _toutes_les_suites(longueur_max: int) -> list[list[Statut]]:
    """Toutes les suites commencant par Indifferente, jusqu'a `longueur_max` statuts."""
    suites = []
    for longueur in range(1, longueur_max + 1):
        for queue in product((OBS, IND, LUM), repeat=longueur - 1):
            suites.append([IND, *queue])
    return suites


def test_les_trois_inclusions_vraies_tiennent_sur_toutes_les_suites_courtes() -> None:
    """`R1 ⊆ R2`, `R3 ⊆ R2`, `R2 ⊆ R0` -- verifiees, pas supposees.

    Exhaustif sur les 1 + 3 + 9 + 27 + 81 + 243 = 364 suites de longueur <= 6.
    """
    suites = _toutes_les_suites(6)
    assert len(suites) == 364
    for suite in suites:
        r = analyser_suite(suite)
        assert not r.r1 or r.r2, suite
        assert not r.r3 or r.r2, suite
        assert not r.r2 or r.r0, suite


def test_r1_et_r3_ne_sont_pas_ordonnees() -> None:
    """Aucune hierarchie entre R1 et R3 : chacune se declenche sans l'autre.

    C'est ce que le compte rendu ne doit pas supposer. Les deux temoins sont ecrits ici.
    """
    r1_sans_r3 = analyser_suite([IND, LUM, OBS, LUM])
    assert r1_sans_r3.r1 and not r1_sans_r3.r3

    r3_sans_r1 = analyser_suite([IND, LUM, IND])
    assert r3_sans_r1.r3 and not r3_sans_r1.r1


def test_l_agregation_d_une_partie_est_le_ou_de_ses_familles() -> None:
    """Une partie satisfait une definition des qu'une seule de ses familles la satisfait."""
    familles = [
        analyser_suite([IND, LUM, LUM]),  # R0 seule
        analyser_suite([IND, LUM, IND]),  # R0, R2, R3
        analyser_suite([IND]),  # rien
    ]
    assert Retournements.ou(familles) == Retournements(r0=True, r1=False, r2=True, r3=True)


def test_l_agregation_de_rien_ne_declenche_rien() -> None:
    """Une partie sans famille -- cas impossible en jeu, mais le neutre doit etre faux."""
    assert Retournements.ou([]) == Retournements(r0=False, r1=False, r2=False, r3=False)


# ---------------------------------------------------------------------------------
# evenements_r2 -- « quand », et pas seulement « si »
# ---------------------------------------------------------------------------------

EVENEMENTS = [
    ("famille jamais posee", [IND], ()),
    ("Lumiere prise, jamais perdue", [IND, LUM, LUM], ()),
    ("Lumiere annulee au 2e pas", [IND, LUM, IND], (2,)),
    ("perdue, reprise, reperdue", [IND, LUM, IND, LUM, IND], (2, 4)),
    ("inversion directe", [IND, LUM, OBS], (2,)),
    # L'entree en Lumiere depuis Indifferente n'est PAS une perte d'acquis : c'est le
    # piege que R0 ne sait pas eviter et que R2 evite par sa garde.
    ("entree tardive puis annulation", [IND, IND, LUM, IND], (3,)),
]


@pytest.mark.parametrize(
    ("intitule", "suite", "attendus"), EVENEMENTS, ids=[cas[0] for cas in EVENEMENTS]
)
def test_les_indices_des_pertes_d_acquis(
    intitule: str, suite: list[Statut], attendus: tuple[int, ...]
) -> None:
    """Les indices sont calcules de tete : `suite[t-1]` non-Indifferent et `suite[t]` autre."""
    assert evenements_r2(suite) == attendus, intitule


def test_avoir_un_evenement_equivaut_a_r2() -> None:
    """Les deux fonctions repondent a la meme question, l'une par oui/non, l'autre par ou.

    Exhaustif sur les 364 suites de longueur <= 6 : si elles divergeaient, l'une des deux
    compterait autre chose que la perte d'acquis.
    """
    for suite in _toutes_les_suites(6):
        assert bool(evenements_r2(suite)) == analyser_suite(suite).r2, suite


def test_une_suite_vide_est_refusee_aussi_pour_les_evenements() -> None:
    with pytest.raises(ValueError, match="au moins un statut"):
        evenements_r2([])
