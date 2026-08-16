"""La distribution par noeuds de chance -- prealable a l'adaptateur OpenSpiel.

Un jeu OpenSpiel valide expose la distribution comme un vrai noeud de hasard : sans cela,
aucun algorithme travaillant sur l'arbre n'est utilisable. Deux mecanismes coexistent, et
c'est voulu :

  - `reset(seed)` et `reset_depuis_pioche` fixent la pioche a la construction. Ils servent
    au determinisme des tests et des parties de mesure ;
  - `reset_par_hasard()` ouvre un noeud de chance par carte tiree.

La machine a etats est **la meme** dans les deux cas. L'ecrire une seconde fois dans
l'adaptateur aurait viole le paragraphe 2 des conventions -- et c'est exactement ainsi
qu'un defaut s'est propage entre quatre fichiers dans la tentative precedente.

**Les issues de chance sont des TYPES de carte, pas des cartes.** Deux exemplaires du meme
couple (famille, role) sont interchangeables : en faire deux issues distinctes doublerait
l'arbre sans rien distinguer, exactement ce que le masquage des actions de pose evite
depuis l'etape 4.
"""

from __future__ import annotations

import random

import pytest

from tests.outils import (
    TOUTES_LES_INSTANCES,
    Instance,
    actions_legales,
    cartes_presentes,
    cle,
    construire,
    module,
    noms,
    paquet_attendu,
)

NB_PARTIES = 5


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_la_partie_commence_par_un_noeud_de_chance(instance: Instance) -> None:
    _, moteur = construire(instance)
    etat = moteur.reset_par_hasard()
    engine = module("engine")

    assert etat.phase().name == "CHANCE"
    assert etat.current_player() == engine.JOUEUR_HASARD
    assert etat.current_player() < 0

    vue = etat.vue_privilegiee()
    assert len(vue.pioche) == instance.nb_cartes, "aucune carte ne doit etre tiree d'avance"
    assert all(len(main) == 0 for main in vue.mains)
    assert sorted(cartes_presentes(vue)) == sorted(paquet_attendu(instance))


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_les_issues_de_chance_sont_les_types_encore_disponibles(
    instance: Instance,
) -> None:
    config, moteur = construire(instance)
    rules = module("rules")
    etat = moteur.reset_par_hasard()

    attendues = sorted(
        {
            rules.encoder_type_carte(carte, config)
            for carte in etat.vue_privilegiee().pioche
        }
    )
    assert sorted(etat.legal_actions()) == attendues
    assert len(attendues) == instance.familles * len(instance.roles)

    probabilites = etat.chance_outcomes()
    assert sorted(action for action, _ in probabilites) == attendues
    assert sum(proba for _, proba in probabilites) == pytest.approx(1.0)
    assert all(proba > 0 for _, proba in probabilites)


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_une_issue_de_chance_met_une_carte_du_bon_type_en_main(
    instance: Instance,
) -> None:
    config, moteur = construire(instance)
    rules = module("rules")
    etat = moteur.reset_par_hasard()

    action = sorted(etat.legal_actions())[0]
    famille, role = rules.decoder_type_carte(action, config)
    etat.apply(action)

    main = etat.vue_privilegiee().mains[0]
    assert len(main) == 1
    assert main[0].famille == famille
    assert main[0].role is role
    assert len(etat.vue_privilegiee().pioche) == instance.nb_cartes - 1


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_une_partie_par_hasard_se_joue_de_bout_en_bout(instance: Instance) -> None:
    """Les memes controles que C1 a C4, sur l'arbre avec noeuds de chance."""
    _, moteur = construire(instance)
    attendues = sorted(paquet_attendu(instance))

    for seed in range(NB_PARTIES):
        etat = moteur.reset_par_hasard()
        rng = random.Random(seed)
        poses = 0
        noeuds_de_chance = 0

        while not etat.is_terminal():
            phase = etat.phase().name
            if phase == "CHANCE":
                noeuds_de_chance += 1
            elif phase == "POSE":
                poses += 1
                assert len(etat.vue_privilegiee().mains[etat.current_player()]) == 3
            assert sorted(cartes_presentes(etat.vue_privilegiee())) == attendues
            etat.apply(rng.choice(actions_legales(etat)))

        vue = etat.vue_privilegiee()
        assert poses == instance.joueurs * instance.tours
        assert noeuds_de_chance == instance.cartes_jouees, (
            f"{instance.nom} : {noeuds_de_chance} noeuds de chance pour "
            f"{instance.cartes_jouees} cartes distribuees"
        )
        assert len(vue.pioche) == instance.reste_en_pioche
        assert sorted(cartes_presentes(vue)) == attendues
        assert sum(etat.returns()) == pytest.approx(0.0)


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_une_carte_tiree_ne_revient_jamais_dans_la_pioche(instance: Instance) -> None:
    _, moteur = construire(instance)
    etat = moteur.reset_par_hasard()
    rng = random.Random(0)
    deja_vues: set[tuple[int, str, int]] = set()

    while not etat.is_terminal():
        vue = etat.vue_privilegiee()
        en_pioche = {cle(carte) for carte in vue.pioche}
        assert not (deja_vues & en_pioche), (
            f"{instance.nom} : une carte deja distribuee est revenue en pioche"
        )
        deja_vues |= {cle(carte) for main in vue.mains for carte in main}
        etat.apply(rng.choice(actions_legales(etat)))

    assert len(deja_vues) == instance.cartes_jouees


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_le_hasard_ne_sert_qu_a_distribuer(instance: Instance) -> None:
    """Les noeuds de chance vont par trois, et sont toujours suivis d'une pose.

    Un noeud de chance ailleurs voudrait dire que le hasard intervient dans une regle --
    ce que le paragraphe 3.3 exclut : le seul aleatoire du jeu est la pioche.
    """
    _, moteur = construire(instance)
    etat = moteur.reset_par_hasard()
    rng = random.Random(2)
    sequence: list[str] = []

    while not etat.is_terminal():
        sequence.append(etat.phase().name)
        etat.apply(rng.choice(actions_legales(etat)))

    reste = sequence
    tours_vus = 0
    while reste:
        assert reste[:3] == ["CHANCE"] * 3, (
            f"{instance.nom} : le tour {tours_vus} ne commence pas par trois tirages -- "
            f"{reste[:4]}"
        )
        assert reste[3] == "POSE", f"{instance.nom} : pas de pose apres les trois tirages"
        reste = reste[4:]
        cibles = 0
        while reste and reste[0] == "CIBLAGE":
            reste = reste[1:]
            cibles += 1
        assert cibles <= 3, "plus de trois Assassins resolus en un tour"
        tours_vus += 1

    assert tours_vus == instance.joueurs * instance.tours
