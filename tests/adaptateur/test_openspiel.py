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
    ROLES_COMPLETS,
    Instance,
    actions_legales,
    construire_config,
    empreinte,
    module,
    noms,
    role,
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


#: Au-dela de ce qui est autorise, pour verifier que les bornes declarees mordent des deux
#: cotes : un joueur seul, et jusqu'a six.
JOUEURS_SONDES = range(1, 7)


def test_les_bornes_de_joueurs_declarees_sont_celles_que_la_configuration_accepte() -> None:
    """Le jeu declare `min_num_players` et `max_num_players` ; `GameConfig` decide.

    Ce test ne compare pas deux ecritures de la meme liste -- ce serait la tautologie du
    defaut 4. Il confronte la **declaration** au **comportement** : pour chaque nombre de
    joueurs sonde, la configuration doit se construire si et seulement si le nombre tombe
    dans les bornes annoncees a OpenSpiel. Etendre l'un sans l'autre echoue donc ici, dans
    les deux sens.

    Chaque configuration sondee a `familles = joueurs + 1` et le paquet complet des roles :
    les deux autres planchers -- `familles > joueurs` et `tours >= 3` -- sont satisfaits pour
    tous les nombres sondes, donc le seul refus possible porte bien sur `joueurs`.
    """
    type_de_jeu = module("openspiel_adapter")._type_de_jeu()
    game_config = module("config").GameConfig
    roles = tuple(role(nom) for nom in ROLES_COMPLETS)

    for joueurs in JOUEURS_SONDES:
        try:
            construite = game_config(
                familles=joueurs + 1, roles=roles, exemplaires=3, joueurs=joueurs
            )
        except ValueError:
            accepte = False
        else:
            accepte = True
            assert construite.tours >= 3, "le sondage viole un autre plancher que joueurs"

        dans_les_bornes = (
            type_de_jeu.min_num_players <= joueurs <= type_de_jeu.max_num_players
        )
        assert accepte == dans_les_bornes, (
            f"{joueurs} joueurs : GameConfig "
            f"{'accepte' if accepte else 'refuse'}, alors que les bornes declarees a "
            f"OpenSpiel sont [{type_de_jeu.min_num_players}, "
            f"{type_de_jeu.max_num_players}] -- une des deux sources a bouge sans l'autre"
        )


@pytest.mark.parametrize("mask_test", [False, True], ids=["sans-masque", "avec-masque"])
@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_le_harnais_de_validite_d_openspiel_passe(instance: Instance, mask_test: bool) -> None:
    """`random_sim_test` est le controle de conformite d'OpenSpiel lui-meme.

    Tout le reste de ce fichier est ecrit a la main : ce sont **nos** idees de ce qu'un jeu
    valide doit respecter. Celui-ci est celui de la bibliotheque, et il verifie ce a quoi
    ses propres algorithmes se fient -- coherence des bornes, des identifiants de joueur,
    du masque d'actions legales, du clonage et de la serialisation. Sans lui, le docstring
    de ce fichier promet une validite que personne n'a etablie.

    `serialize=False` : la serialisation d'un jeu Python passe par
    `pyspiel.serialize_game_and_state`, qui reconstruit le jeu depuis sa chaine de
    parametres ; ce n'est pas ce que ce test cherche a etablir.
    """
    import pyspiel

    jeu = _jeu(instance)
    pyspiel.random_sim_test(
        jeu, num_sims=2, serialize=False, verbose=False, mask_test=mask_test
    )


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_l_observateur_n_observe_rien_de_plus_que_l_etat(instance: Instance) -> None:
    """L'observateur et l'etat doivent rendre **la meme** observation, partout.

    OpenSpiel a deux chemins de lecture -- les methodes de l'etat, et l'observateur rendu
    par `make_py_observer` -- et ses algorithmes empruntent le second. Deux chemins qui
    calculent la meme chose sont deux implementations d'une meme regle : c'est ce que le
    paragraphe 2 des conventions interdit, et c'est ainsi qu'un defaut s'est propage entre
    quatre fichiers dans la tentative precedente. Ce test exige donc l'egalite a chaque
    noeud, pas seulement la coherence des tailles.
    """
    jeu = _jeu(instance)
    observateur = jeu.make_py_observer()
    etat = jeu.new_initial_state()
    rng = random.Random(5)
    noeuds = 0

    while not etat.is_terminal():
        for joueur in range(instance.joueurs):
            observateur.set_from(etat, joueur)
            assert list(observateur.tensor) == pytest.approx(
                etat.information_state_tensor(joueur)
            ), f"{instance.nom} : l'observateur et l'etat divergent au noeud {noeuds}"
            assert observateur.string_from(etat, joueur) == (
                etat.information_state_string(joueur)
            )
            assert list(observateur.dict["info_state"]) == list(observateur.tensor)
        noeuds += 1
        etat.apply_action(rng.choice(actions_legales(etat)))

    assert noeuds > instance.cartes_jouees, (
        f"{instance.nom} : {noeuds} noeuds visites, moins que les "
        f"{instance.cartes_jouees} distributions d'une partie"
    )


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_l_observateur_refuse_un_identifiant_qui_n_est_pas_un_joueur(
    instance: Instance,
) -> None:
    """L'observateur ne rattrape pas, ne substitue pas : il traverse jusqu'au coeur."""
    jeu = _jeu(instance)
    observateur = jeu.make_py_observer()
    etat = jeu.new_initial_state()

    for identifiant in (-1, -4, instance.joueurs):
        with pytest.raises(ValueError):
            observateur.set_from(etat, identifiant)
        with pytest.raises(ValueError):
            observateur.string_from(etat, identifiant)


def test_l_observateur_refuse_ce_que_le_jeu_ne_fournit_pas() -> None:
    """Le jeu declare `provides_observation_*=False` : l'observateur doit le tenir.

    Une observation **sans memoire** n'est pas specifiee -- le paragraphe 4.2 decrit un
    seul etat expose au joueur. En rendre une quand meme obligerait a inventer son
    contenu, ce que le paragraphe 8 des conventions interdit. Et
    `private_info=ALL_PLAYERS` demande l'information privee de tous les joueurs : la
    rendre violerait l'invariant I7. Dans les deux cas, refuser est la seule reponse qui
    ne mente pas -- et un refus explicite se lit, alors qu'un observateur silencieusement
    incomplet ne se voit pas.
    """
    import pyspiel

    jeu = _jeu(RAPIDE_3J)
    adaptateur = module("openspiel_adapter")

    with pytest.raises(ValueError):
        jeu.make_py_observer(params={"quelconque": 1})

    refuses = [
        pyspiel.IIGObservationType(perfect_recall=False),
        pyspiel.IIGObservationType(
            perfect_recall=True, private_info=pyspiel.PrivateInfoType.ALL_PLAYERS
        ),
        pyspiel.IIGObservationType(
            perfect_recall=True, private_info=pyspiel.PrivateInfoType.NONE
        ),
        pyspiel.IIGObservationType(perfect_recall=True, public_info=False),
    ]
    for type_demande in refuses:
        with pytest.raises(ValueError):
            jeu.make_py_observer(type_demande)

    assert adaptateur._est_le_type_supporte(adaptateur.TYPE_OBSERVATION_SUPPORTE)
    assert jeu.make_py_observer(adaptateur.TYPE_OBSERVATION_SUPPORTE) is not None
    assert jeu.get_type().provides_observation_string is False
    assert jeu.get_type().provides_observation_tensor is False


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_aucune_observation_n_est_rendue_sans_joueur(instance: Instance) -> None:
    """Appelee sans argument, l'observation ne doit pas se rabattre sur `current_player()`.

    Le paragraphe 4 de la specification ecrit `information_state_string(self, player: int)`
    : une observation est la vue d'un siege. Sur un noeud de chance, `current_player()`
    vaut `-1`, et au terminal `-4` ; substituer l'un ou l'autre rend une observation bien
    formee qui n'egale la vue d'**aucun** joueur -- le test
    `tests/moteur/test_observation_par_joueur.py` le montre cote coeur. Ici on exige que le
    chemin sans argument, celui qu'un utilisateur d'OpenSpiel emprunte le plus naturellement,
    **refuse** plutot que de deviner.

    Le type d'exception n'est pas impose : refuser en ne fournissant aucune valeur par
    defaut (`TypeError`) ou en validant explicitement (`ValueError`) sont deux refus.
    """
    jeu = _jeu(instance)
    etat = jeu.new_initial_state()
    rng = random.Random(0)
    noeuds_examines = 0

    while True:
        if etat.is_chance_node() or etat.is_terminal():
            noeuds_examines += 1
            with pytest.raises((TypeError, ValueError)):
                etat.information_state_string()
            with pytest.raises((TypeError, ValueError)):
                etat.information_state_tensor()
        if etat.is_terminal():
            break
        etat.apply_action(rng.choice(actions_legales(etat)))

    assert noeuds_examines > 1, (
        f"{instance.nom} : {noeuds_examines} noeud(s) sans joueur examine(s), la partie "
        f"devrait en compter au moins un par carte distribuee, plus le terminal"
    )


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_les_bornes_declarees_sont_respectees(instance: Instance) -> None:
    """Un jeu qui declare des bornes fausses casse les algorithmes qui s'y fient."""
    jeu = _jeu(instance)
    config = construire_config(instance)

    assert jeu.num_players() == instance.joueurs
    assert jeu.num_distinct_actions() >= config.actions_de_pose
    # La borne est comparee a la FORMULE de la specification -- `max_chance_outcomes` vaut
    # `familles x roles` (03_specification_moteur.md paragraphe 4) -- et non a la fonction
    # du moteur qui la calcule. Comparer les deux membres au meme code les ferait bouger
    # ensemble : le test passerait avec une formule fausse.
    assert jeu.max_chance_outcomes() == instance.familles * len(instance.roles)

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


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_deux_actions_distinctes_ne_portent_jamais_le_meme_nom(instance: Instance) -> None:
    """Exigence d'OpenSpiel, verifiee par son propre harnais : dans un etat donne, deux
    actions legales distinctes ont deux libelles distincts.

    Elle mord en phase de ciblage. Deux exemplaires du meme couple (famille, role) dans une
    meme zone sont **deux cibles distinctes** -- le controle C15 exige `nb_cibles + 1`
    actions legales, donc on ne les masque pas, contrairement aux actions de pose -- mais
    `f{famille}-{role}` ne les distingue pas. Un libelle ambigu ne fausse aucun coup ; il
    rend les traces de partie et les rapports d'exploitabilite illisibles, et il fait
    echouer `random_sim_test`.
    """
    jeu = _jeu(instance)
    etat = jeu.new_initial_state()
    rng = random.Random(11)
    ciblages_vus = 0

    while not etat.is_terminal():
        actions = actions_legales(etat)
        joueur = etat.current_player()
        noms_vus: dict[str, int] = {}
        for action in actions:
            nom = etat.action_to_string(joueur, action)
            assert nom not in noms_vus, (
                f"{instance.nom} : les actions {noms_vus[nom]} et {action} portent le meme "
                f"nom {nom!r} en phase {etat.phase().name}"
            )
            noms_vus[nom] = action
        if etat.phase().name == "CIBLAGE":
            ciblages_vus += 1
        etat.apply_action(rng.choice(actions))

    assert ciblages_vus > 0, f"{instance.nom} : aucune phase de ciblage sur cette partie"


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
