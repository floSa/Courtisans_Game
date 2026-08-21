"""Tests hostiles de l'auditeur -- axe 1 : l'agent ne triche pas.

Ecrits sans reutiliser une seule ligne de `tests/agents/test_aveuglement_reseau.py` : mon
brouilleur, mon piege, mon compteur. Chaque test qui affirme une invariance est double d'un
test qui prouve que l'instrument MORD -- sinon il verrouillerait le defaut qu'il pretend
interdire, ce qui est arrive une fois en phase 2.
"""

from __future__ import annotations

import random
from dataclasses import replace
from pathlib import Path

import pytest

from agents.politique_reseau import charger, politique_reseau, politique_reseau_deterministe
from courtisans.cards import ROLES_CACHES, Carte, Role
from courtisans.engine import Engine, Phase, State
from courtisans.infoset import chaine, tenseur
from mesure.instance import ENTRAINEMENT_3J

CHEMIN = Path("models/phase3/final.pt")


# ---------------------------------------------------------------------------------------
# Outils de l'auditeur
# ---------------------------------------------------------------------------------------


def _paquet_total(etat: State) -> list[Carte]:
    """Toutes les cartes de la partie, ou qu'elles soient. Doit etre le paquet, toujours."""
    return sorted(
        list(etat._pioche)
        + [c for main in etat._mains for c in main]
        + [p.carte for p in etat._posees]
        + [p.carte for p in etat._defausse]
    )


def etat_apres(seed: int, coups: int, alea: random.Random) -> State:
    """Une partie avancee de `coups` decisions, tirees au hasard parmi les legales."""
    etat = Engine(ENTRAINEMENT_3J).reset(seed)
    dernier = etat.clone()
    for _ in range(coups):
        if etat.phase() is Phase.TERMINAL:
            break
        if etat.phase() is not Phase.CHANCE:
            dernier = etat.clone()
        etat.apply(alea.choice(etat.legal_actions()))
    if etat.phase() is Phase.TERMINAL:
        return dernier
    return etat


def _cachees_invisibles(etat: State, moi: int) -> list[tuple[str, int]]:
    """Les emplacements dont `moi` ne connait pas le contenu : pioche, mains adverses."""
    emplacements: list[tuple[str, int]] = [("pioche", i) for i in range(len(etat._pioche))]
    for siege in range(etat.config.joueurs):
        if siege != moi:
            emplacements += [("main", (siege, i)) for i in range(len(etat._mains[siege]))]
    return emplacements


def brouiller_l_invisible(etat: State, moi: int, alea: random.Random) -> State:
    """Melange tout ce que `moi` ne peut pas voir, SANS toucher a ce qu'il voit.

    Deux operations, et elles preservent le multiensemble du paquet :

    1. permutation complete des cartes de la pioche et des mains adverses entre elles ;
    2. echange de l'identite d'un dos adverse avec un Espion cache ailleurs -- meme role,
       donc meme apparence publique, mais autre famille, donc autre verite.
    """
    copie = etat.clone()
    emplacements = _cachees_invisibles(copie, moi)
    cartes = []
    for genre, ou in emplacements:
        cartes.append(copie._pioche[ou] if genre == "pioche" else copie._mains[ou[0]][ou[1]])
    alea.shuffle(cartes)
    for (genre, ou), carte in zip(emplacements, cartes, strict=True):
        if genre == "pioche":
            copie._pioche[ou] = carte
        else:
            copie._mains[ou[0]][ou[1]] = carte

    dos = [
        (i, p)
        for i, p in enumerate(copie._posees)
        if p.carte.role in ROLES_CACHES and p.poseur != moi
    ]
    ailleurs = [
        (genre, ou, c)
        for (genre, ou), c in (
            (e, copie._pioche[e[1]] if e[0] == "pioche" else copie._mains[e[1][0]][e[1][1]])
            for e in _cachees_invisibles(copie, moi)
        )
        if c.role in ROLES_CACHES
    ]
    for (i, posee), (genre, ou, autre) in zip(dos, ailleurs, strict=False):
        if autre.famille == posee.carte.famille:
            continue
        copie._posees[i] = replace(posee, carte=autre)
        if genre == "pioche":
            copie._pioche[ou] = posee.carte
        else:
            copie._mains[ou[0]][ou[1]] = posee.carte
    return copie


class Espion:
    """Compte les appels a une methode de `State`, et peut les faire lever."""

    def __init__(self, nom: str, explosif: bool) -> None:
        self.nom, self.explosif, self.appels = nom, explosif, 0
        self.origine = getattr(State, nom)

    def __enter__(self) -> "Espion":
        espion = self

        def piege(soi, *args, **kwargs):
            espion.appels += 1
            if espion.explosif:
                raise AssertionError(f"l'agent a appele State.{espion.nom} pendant sa decision")
            return espion.origine(soi, *args, **kwargs)

        setattr(State, self.nom, piege)
        return self

    def __exit__(self, *_) -> None:
        setattr(State, self.nom, self.origine)


PRIVILEGES = ("vue_privilegiee", "scores", "returns", "cibles_courantes")


@pytest.fixture(scope="module")
def modele():
    if not CHEMIN.exists():
        pytest.fail(f"{CHEMIN} absent : ces controles ne se sautent pas, ils tombent")
    return charger(str(CHEMIN), 205, 24)


# ---------------------------------------------------------------------------------------
# A. Le brouilleur MORD -- sans quoi tout le reste est vide
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("seed", range(12))
def test_A_mon_brouilleur_change_vraiment_la_verite_cachee(seed: int) -> None:
    alea = random.Random(9000 + seed)
    etat = etat_apres(seed, 6 + (seed % 8), alea)
    if etat.phase() is Phase.TERMINAL:
        pytest.skip("partie finie avant le 12e coup")
    moi = etat.current_player()
    autre = brouiller_l_invisible(etat, moi, random.Random(1234 + seed))

    assert autre.vue_privilegiee() != etat.vue_privilegiee(), "brouilleur inerte"
    for siege in range(etat.config.joueurs):
        if siege != moi:
            assert list(autre._mains[siege]) != list(etat._mains[siege]) or list(
                autre._pioche
            ) != list(etat._pioche)
    assert _paquet_total(autre) == _paquet_total(etat), (
        "le brouilleur a fabrique un paquet impossible"
    )
    assert len(set(_paquet_total(etat))) == len(_paquet_total(etat)), "carte en double"


def test_A_le_brouillage_deplace_bien_le_score_final_au_moins_une_fois() -> None:
    """Un brouilleur qui ne change jamais l'issue ne prouverait rien de l'aveuglement."""
    deplace = 0
    for seed in range(40):
        alea = random.Random(4000 + seed)
        etat = etat_apres(seed, 10, alea)
        if etat.phase() is Phase.TERMINAL:
            continue
        moi = etat.current_player()
        autre = brouiller_l_invisible(etat, moi, random.Random(77 + seed))
        if etat.scores() != autre.scores():
            deplace += 1
    assert deplace > 0, "le brouilleur ne touche jamais la verite : les tests suivants seraient vides"


# ---------------------------------------------------------------------------------------
# B. L'observation ne bouge pas
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("seed", range(30))
def test_B_le_tenseur_et_la_chaine_sont_invariants_sous_brouillage(seed: int) -> None:
    alea = random.Random(500 + seed)
    etat = etat_apres(seed, 8 + (seed % 15), alea)
    if etat.phase() is Phase.TERMINAL:
        pytest.skip("partie finie")
    moi = etat.current_player()
    autre = brouiller_l_invisible(etat, moi, random.Random(31337 + seed))

    assert tenseur(autre, moi) == tenseur(etat, moi)
    assert chaine(autre, moi) == chaine(etat, moi)
    assert autre.legal_actions() == etat.legal_actions()


# ---------------------------------------------------------------------------------------
# C. La decision du reseau ne bouge pas
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("seed", range(30))
def test_C_les_logits_du_reseau_sont_identiques_bit_a_bit(seed: int, modele) -> None:
    import torch

    from agents import reseau as reseau_module

    alea = random.Random(600 + seed)
    etat = etat_apres(seed, 8 + (seed % 15), alea)
    if etat.phase() is Phase.TERMINAL:
        pytest.skip("partie finie")
    moi = etat.current_player()
    autre = brouiller_l_invisible(etat, moi, random.Random(4242 + seed))

    with torch.no_grad():
        a = modele(torch.tensor([tenseur(etat, moi)], dtype=torch.float32))[0]
        b = modele(torch.tensor([tenseur(autre, moi)], dtype=torch.float32))[0]
    assert torch.equal(a, b)
    assert reseau_module.choisir_le_plus_probable(
        modele, tenseur(etat, moi), etat.legal_actions()
    ) == reseau_module.choisir_le_plus_probable(
        modele, tenseur(autre, moi), autre.legal_actions()
    )


def test_C_une_partie_entiere_donne_la_meme_suite_d_actions_sous_brouillage(modele) -> None:
    """Le brouillage est refait a CHAQUE noeud : l'agent joue dans un monde cache different
    a chaque decision et doit produire exactement la meme partie."""
    for seed in range(6):
        reference = Engine(ENTRAINEMENT_3J).reset(seed)
        actions_ref = []
        politique = politique_reseau_deterministe(modele)
        while reference.phase() is not Phase.TERMINAL:
            if reference.phase() is Phase.CHANCE:
                reference.apply(reference.legal_actions()[0])
                continue
            actions_ref.append(politique(reference))
            reference.apply(actions_ref[-1])

        rejeu = Engine(ENTRAINEMENT_3J).reset(seed)
        actions_bis = []
        i = 0
        while rejeu.phase() is not Phase.TERMINAL:
            if rejeu.phase() is Phase.CHANCE:
                rejeu.apply(rejeu.legal_actions()[0])
                continue
            trouble = brouiller_l_invisible(rejeu, rejeu.current_player(), random.Random(i + 7 * seed))
            action = politique(trouble)
            actions_bis.append(action)
            rejeu.apply(action)
            i += 1
        assert actions_bis == actions_ref, f"seed {seed}"


# ---------------------------------------------------------------------------------------
# D. Le piege -- et la preuve qu'il mord
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("nom", PRIVILEGES)
def test_D_mon_piege_mord_quand_on_le_teste_sur_lui_meme(nom: str) -> None:
    etat = etat_apres(3, 10, random.Random(1))
    with Espion(nom, explosif=True):
        with pytest.raises(AssertionError):
            getattr(etat, nom)()


@pytest.mark.parametrize("nom", PRIVILEGES)
def test_D_une_partie_entiere_se_joue_avec_les_quatre_acces_pieges(nom: str, modele) -> None:
    for seed in range(4):
        etat = Engine(ENTRAINEMENT_3J).reset(seed)
        politique = politique_reseau(modele, random.Random(seed))
        while etat.phase() is not Phase.TERMINAL:
            if etat.phase() is Phase.CHANCE:
                etat.apply(etat.legal_actions()[0])
                continue
            observation = tenseur(etat, etat.current_player())
            actions = etat.legal_actions()
            from agents import reseau as reseau_module

            with Espion(nom, explosif=True):
                action = reseau_module.choisir(
                    modele, observation, actions, random.Random(seed)
                )
            etat.apply(action)


def test_D_le_compteur_compte_vraiment() -> None:
    etat = etat_apres(5, 6, random.Random(2))
    with Espion("scores", explosif=False) as espion:
        etat.scores()
        etat.scores()
    assert espion.appels == 2


def test_D_zero_appel_privilegie_pendant_la_decision_du_reseau(modele) -> None:
    """Le compteur, pas seulement l'interdiction : combien d'appels, exactement."""
    from agents import reseau as reseau_module

    total = {nom: 0 for nom in PRIVILEGES}
    decisions = 0
    for seed in range(4):
        etat = Engine(ENTRAINEMENT_3J).reset(seed)
        while etat.phase() is not Phase.TERMINAL:
            if etat.phase() is Phase.CHANCE:
                etat.apply(etat.legal_actions()[0])
                continue
            observation = tenseur(etat, etat.current_player())
            actions = etat.legal_actions()
            espions = [Espion(nom, explosif=False) for nom in PRIVILEGES]
            for e in espions:
                e.__enter__()
            try:
                action = reseau_module.choisir(
                    modele, observation, actions, random.Random(1)
                )
            finally:
                for e in reversed(espions):
                    e.__exit__()
            for e in espions:
                total[e.nom] += e.appels
            decisions += 1
            etat.apply(action)
    assert decisions > 50
    assert total == {nom: 0 for nom in PRIVILEGES}, total


# ---------------------------------------------------------------------------------------
# E. Le reseau ne recoit qu'un vecteur -- et ne joue jamais d'illegal
# ---------------------------------------------------------------------------------------


def test_E_l_action_choisie_est_toujours_legale(modele) -> None:
    coups = 0
    for seed in range(8):
        etat = Engine(ENTRAINEMENT_3J).reset(seed)
        politique = politique_reseau(modele, random.Random(seed))
        while etat.phase() is not Phase.TERMINAL:
            if etat.phase() is Phase.CHANCE:
                etat.apply(etat.legal_actions()[0])
                continue
            action = politique(etat)
            assert action in etat.legal_actions()
            coups += 1
            etat.apply(action)
    assert coups > 100


# ---------------------------------------------------------------------------------------
# F. Mon controle d'invariance MORD -- on lui presente trois tricheurs
# ---------------------------------------------------------------------------------------


def _fuite(etat: State, joueur: int, quoi: str) -> float:
    if quoi == "pioche":
        v = etat.vue_privilegiee()
        return float(v.pioche[0].famille) if v.pioche else -1.0
    if quoi == "dos":
        for p in etat._posees:
            if p.carte.role in ROLES_CACHES and p.poseur != joueur:
                return float(p.carte.famille)
        return -1.0
    raise ValueError(quoi)


@pytest.mark.parametrize("quoi", ["pioche", "dos"])
def test_F_un_tenseur_qui_fuiterait_UNE_composante_serait_attrape(quoi: str) -> None:
    """Sans ce test, l'invariance du B pourrait n'etre qu'une invariance vide."""
    attrape = 0
    for seed in range(30):
        etat = etat_apres(seed, 8 + (seed % 15), random.Random(500 + seed))
        moi = etat.current_player()
        autre = brouiller_l_invisible(etat, moi, random.Random(31337 + seed))
        if _fuite(etat, moi, quoi) != _fuite(autre, moi, quoi):
            attrape += 1
    assert attrape >= 10, f"seulement {attrape}/30 : mon brouilleur ne brouille pas assez"


def test_F_dans_cette_instance_la_main_adverse_est_TOUJOURS_vide() -> None:
    """Constat de l'auditeur, et il change la lecture de l'aveuglement : le moteur ne
    remplit la main que du joueur courant. L'information cachee de `entrainement-3j` est
    la pioche et l'identite des Espions poses, jamais un jeu adverse en main."""
    vues = 0
    for seed in range(20):
        etat = Engine(ENTRAINEMENT_3J).reset(seed)
        while etat.phase() is not Phase.TERMINAL:
            if etat.phase() is not Phase.CHANCE:
                moi = etat.current_player()
                for siege in range(etat.config.joueurs):
                    if siege != moi:
                        assert etat._mains[siege] == []
                vues += 1
            etat.apply(etat.legal_actions()[0])
    assert vues > 100
