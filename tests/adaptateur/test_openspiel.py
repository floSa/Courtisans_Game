"""L'adaptateur OpenSpiel -- validite du jeu, et absence de regle ajoutee.

Les 18 tests de conformite et les 11 invariants ne sont **pas** reecrits ici : ils
tournent a l'identique sur le coeur et a travers l'adaptateur, pilotes par la variable
d'environnement `COURTISANS_MOTEUR`. Trois commandes, la meme suite :

    uv run pytest tests/conformite -q
    COURTISANS_MOTEUR=openspiel uv run pytest tests/conformite -q
    COURTISANS_MOTEUR=openspiel-hasard uv run pytest tests/conformite -q

Ce fichier verifie ce que ces trois passages ne peuvent pas voir : que le jeu est valide
au sens d'OpenSpiel, que l'adaptateur **n'ajoute aucune regle**, et que le coeur n'importe
toujours ni pyspiel, ni NumPy, ni PyTorch -- critere A4.
"""

from __future__ import annotations

import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    RAPIDE_3J,
    Instance,
    actions_legales,
    construire_config,
    empreinte,
    module,
    noms,
)

RACINE = Path(__file__).resolve().parents[2]
NB_PARTIES = 5

#: Importe le coeur, et rien d'autre. Le sous-processus est indispensable : dans le
#: processus de test, pyspiel et NumPy sont deja charges par l'adaptateur lui-meme.
SCRIPT_IMPORTS = """
import sys
import courtisans.cards, courtisans.config, courtisans.rules
import courtisans.engine, courtisans.infoset
interdits = sorted(
    nom for nom in sys.modules
    if nom.split(".")[0] in {"pyspiel", "open_spiel", "numpy", "torch", "scipy"}
)
print(";".join(interdits))
"""


def _jeu(instance: Instance):  # noqa: ANN202 - le type vit dans l'adaptateur
    return module("openspiel_adapter").CourtisansGame(
        config=construire_config(instance)
    )


# ---------------------------------------------------------------------------------
# A4 -- le coeur reste en stdlib pure
# ---------------------------------------------------------------------------------


def test_a4_le_coeur_n_importe_ni_openspiel_ni_numpy_ni_pytorch() -> None:
    environnement = dict(os.environ)
    environnement["PYTHONPATH"] = str(RACINE)
    resultat = subprocess.run(
        [sys.executable, "-c", SCRIPT_IMPORTS],
        capture_output=True,
        text=True,
        cwd=RACINE,
        env=environnement,
        check=False,
    )

    assert resultat.returncode == 0, f"le coeur ne s'importe pas seul :\n{resultat.stderr}"
    charges = resultat.stdout.strip()
    assert charges == "", (
        f"importer le coeur charge des dependances interdites : {charges}"
    )


def test_l_adaptateur_lui_importe_bien_pyspiel() -> None:
    """Temoin positif : sans lui, le test A4 passerait meme si rien n'etait installe."""
    adaptateur = module("openspiel_adapter")
    assert "pyspiel" in sys.modules
    assert adaptateur.NOM_COURT == "courtisans"


# ---------------------------------------------------------------------------------
# Validite du jeu au sens d'OpenSpiel
# ---------------------------------------------------------------------------------


def test_le_jeu_est_enregistre_et_chargeable_par_son_nom() -> None:
    import pyspiel

    module("openspiel_adapter").enregistrer()  # idempotent
    assert "courtisans" in pyspiel.registered_names()

    jeu = pyspiel.load_game("courtisans(familles=4,exemplaires=2,joueurs=3)")
    assert jeu.num_players() == 3
    assert jeu.get_type().chance_mode == pyspiel.GameType.ChanceMode.EXPLICIT_STOCHASTIC
    assert (
        jeu.get_type().information
        == pyspiel.GameType.Information.IMPERFECT_INFORMATION
    )
    assert jeu.get_type().utility == pyspiel.GameType.Utility.ZERO_SUM


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_les_bornes_declarees_sont_respectees(instance: Instance) -> None:
    """Un jeu qui declare des bornes fausses casse les algorithmes qui s'y fient."""
    jeu = _jeu(instance)
    config = construire_config(instance)

    assert jeu.num_players() == instance.joueurs
    assert jeu.num_distinct_actions() >= config.actions_de_pose
    assert jeu.max_chance_outcomes() == module("rules").nb_types_de_carte(config)

    for seed in range(NB_PARTIES):
        etat = jeu.new_initial_state()
        rng = random.Random(seed)
        longueur = 0

        while not etat.is_terminal():
            if etat.is_chance_node():
                issues = etat.chance_outcomes()
                assert sum(proba for _, proba in issues) == pytest.approx(1.0)
                assert all(0 <= a < jeu.max_chance_outcomes() for a, _ in issues)
                actions = [a for a, _ in issues]
            else:
                actions = etat.legal_actions()
                assert all(0 <= a < jeu.num_distinct_actions() for a in actions), (
                    f"{instance.nom} : action hors de num_distinct_actions"
                )
                assert 0 <= etat.current_player() < instance.joueurs
            etat.action_to_string(etat.current_player(), actions[0])
            etat.apply_action(rng.choice(actions))
            longueur += 1

        assert longueur <= jeu.max_game_length(), (
            f"{instance.nom} : partie de {longueur} coups pour une borne declaree de "
            f"{jeu.max_game_length()}"
        )
        assert sum(etat.returns()) == pytest.approx(0.0)
        assert all(
            jeu.min_utility() <= gain <= jeu.max_utility() for gain in etat.returns()
        )


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_la_racine_est_un_noeud_de_chance(instance: Instance) -> None:
    import pyspiel

    etat = _jeu(instance).new_initial_state()

    assert etat.is_chance_node()
    assert etat.current_player() == pyspiel.PlayerId.CHANCE
    assert etat.phase().name == "CHANCE"


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_le_tenseur_a_la_taille_annoncee(instance: Instance) -> None:
    jeu = _jeu(instance)
    etat = jeu.new_initial_state()
    taille = jeu.information_state_tensor_size()

    for joueur in range(instance.joueurs):
        assert len(etat.information_state_tensor(joueur)) == taille
    assert jeu.information_state_tensor_shape() == [taille]


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_un_clone_adapte_est_independant(instance: Instance) -> None:
    jeu = _jeu(instance)
    etat = jeu.new_initial_state()
    for _ in range(4):
        etat.apply_action(etat.legal_actions()[0])

    clone = etat.clone()
    empreinte_avant = empreinte(etat, instance)
    rng = random.Random(0)
    while not clone.is_terminal():
        clone.apply_action(rng.choice(actions_legales(clone)))

    assert empreinte(etat, instance) == empreinte_avant
    assert not etat.is_terminal()


# ---------------------------------------------------------------------------------
# L'adaptateur n'ajoute aucune regle
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_l_adaptateur_produit_exactement_les_memes_etats_que_le_coeur(
    instance: Instance,
) -> None:
    """Meme pioche, memes actions : les deux etats doivent etre indiscernables.

    C'est le controle qui dit que l'adaptateur traduit et rien de plus. S'il divergeait,
    la suite de conformite validerait un moteur qui n'est pas celui qu'OpenSpiel joue.
    """
    config = construire_config(instance)
    coeur = module("engine").Engine(config)
    jeu = _jeu(instance)

    for seed in range(NB_PARTIES):
        pioche = list(coeur.pioche_depuis_seed(seed))
        etat_coeur = coeur.reset_depuis_pioche(pioche)
        etat_adapte = jeu.reset_depuis_pioche(pioche)
        rng = random.Random(seed)
        pas = 0

        while not etat_coeur.is_terminal():
            assert empreinte(etat_coeur, instance) == empreinte(etat_adapte, instance), (
                f"{instance.nom}, seed {seed} : divergence au pas {pas}"
            )
            assert sorted(etat_adapte.legal_actions()) == sorted(
                etat_coeur.legal_actions()
            )
            action = rng.choice(actions_legales(etat_coeur))
            etat_coeur.apply(action)
            etat_adapte.apply(action)
            pas += 1

        assert etat_adapte.is_terminal()
        assert empreinte(etat_coeur, instance) == empreinte(etat_adapte, instance)


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_la_facade_expose_la_meme_surface_que_le_coeur(instance: Instance) -> None:
    """Toutes les entrees du coeur doivent exister sur l'adaptateur, et rendre la meme
    chose. C'est ce qui permet aux memes tests de tourner des deux cotes ; une methode
    oubliee ne se verrait qu'en lancant la suite dans l'autre mode."""
    jeu = _jeu(instance)
    coeur = module("engine").Engine(construire_config(instance))

    assert [
        (c.famille, c.role.name, c.exemplaire) for c in jeu.pioche_depuis_seed(7)
    ] == [(c.famille, c.role.name, c.exemplaire) for c in coeur.pioche_depuis_seed(7)]

    par_hasard = jeu.reset_par_hasard()
    assert par_hasard.phase().name == "CHANCE"
    assert par_hasard.assassins_en_attente() == ()
    assert par_hasard.tours_restants(0) == instance.tours
    assert isinstance(str(par_hasard), str) and str(par_hasard)

    etat = jeu.reset(7)
    reference = coeur.reset(7)
    assert etat.phase().name == reference.phase().name
    assert etat.scores() == reference.scores()
    assert etat.assassin_en_resolution() is reference.assassin_en_resolution() is None
    assert etat.cibles_courantes() == reference.cibles_courantes()
    assert etat.assassins_en_attente() == reference.assassins_en_attente()
    assert [etat.tours_restants(j) for j in range(instance.joueurs)] == [
        reference.tours_restants(j) for j in range(instance.joueurs)
    ]
    assert str(etat) == reference.information_state_string(0)


def test_les_noms_d_action_couvrent_les_trois_phases() -> None:
    """`action_to_string` doit rester lisible dans les trois phases, y compris le refus."""
    jeu = _jeu(RAPIDE_3J)
    etat = jeu.new_initial_state()
    rng = random.Random(3)
    vus = {"tirage": 0, "pose": 0, "tuer": 0, "ne pas tuer": 0}

    while not etat.is_terminal():
        actions = etat.legal_actions()
        for action in actions:
            texte = etat.action_to_string(etat.current_player(), action)
            for prefixe in vus:
                if texte.startswith(prefixe):
                    vus[prefixe] += 1
        etat.apply_action(rng.choice(actions))

    assert vus["tirage"] > 0
    assert vus["pose"] > 0
    assert vus["ne pas tuer"] > 0
    assert vus["tuer"] > 0, "aucune cible proposee sur cette partie"
