"""Le CONTENU de l'encodage -- 03_specification_moteur.md paragraphe 4.2.

**Pourquoi ce fichier existe.** C16 et I8 verifient que la chaine et le tenseur sont en
bijection. Ils ne peuvent pas verifier ce qu'ils contiennent : les deux sont rendus depuis
la meme observation, donc retirer un bloc des deux les laisse en bijection. Mesure faite
par mutation le 16/08 : supprimer le bloc `phase` et le bloc `assassin`, ou compter les
cartes mortes comme encore en circulation, laisse **395 tests sur 395 au vert**.

Ce fichier ferme ce trou. Chaque bloc du tenseur y est **recalcule independamment**, a
partir de la vue de dieu et de ce que le paragraphe 4.2 dit qu'il doit contenir -- comme
`scores_attendus` recalcule le decompte pour C9, C11 et C12. Un test qui demanderait au
module son propre attendu ne verifierait rien.

Les trois pieges du paragraphe 4.2 ont chacun leur test :
  - `banquet_visible` et `domaine_visible` excluent les Espions, `banquet_prive` et
    `domaine_prive` ne contiennent que les miens ;
  - `residu` retranche les morts ;
  - `phase` et `assassin` sont presents et corrects.

Et le quatrieme, que la specification ne mentionne pas : `scores_visibles` n'est pas
`scores()`, sinon la famille des Espions adverses fuiterait.
"""

from __future__ import annotations

import random
from typing import Any

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    RAPIDE_3J,
    Instance,
    actions_legales,
    construire,
    module,
    noms,
    parcourir_decisions,
    partie,
    pioches_jumelles_espion,
    scores_moteur,
)

NB_PARTIES = 12

#: Longueur attendue de chaque bloc, en fonction de la configuration. Les formules sont
#: ecrites depuis le tableau du paragraphe 4.2, pas lues dans le module.
def _longueurs_attendues(instance: Instance, nb_roles_visibles: int) -> dict[str, int]:
    familles = instance.familles
    roles = len(instance.roles)
    joueurs = instance.joueurs
    return {
        "main": familles * roles,
        "banquet_visible": familles * nb_roles_visibles * 2,
        "banquet_prive": familles * 2,
        "domaine_visible": familles * nb_roles_visibles * joueurs,
        "domaine_prive": familles * joueurs,
        "residu": familles * roles,
        "morts": familles * roles,
        "marges": familles * 4,
        "dos_adverses_banquet": (joueurs - 1) * 2,
        "dos_adverses_domaine": (joueurs - 1) * joueurs,
        "tours_restants": joueurs,
        "pioche": 1,
        "morts_total": 1,
        "phase": 2,
        "assassin": 2 + 2 + joueurs,
        "assassins_restants": 1,
        "scores_visibles": joueurs,
        "ecart": 1,
    }


def _blocs_du_tenseur(etat: Any, joueur: int) -> dict[str, list[float]]:
    """Decoupe le tenseur selon la disposition annoncee par le module."""
    infoset = module("infoset")
    tenseur = etat.information_state_tensor(joueur)
    blocs: dict[str, list[float]] = {}
    debut = 0
    for nom, longueur in infoset.disposition(etat, joueur):
        blocs[nom] = tenseur[debut : debut + longueur]
        debut += longueur
    assert debut == len(tenseur), "la disposition ne couvre pas tout le tenseur"
    return blocs


def _roles_visibles(instance: Instance) -> list[str]:
    return [nom for nom in instance.roles if nom != "ESPION"]


# ---------------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_tous_les_blocs_exiges_sont_presents_a_la_bonne_taille(instance: Instance) -> None:
    """Attrape la suppression d'un bloc, que la bijection chaine / tenseur ne voit pas."""
    _, moteur = construire(instance)
    etat = moteur.reset(0)
    attendues = _longueurs_attendues(instance, len(_roles_visibles(instance)))

    disposition = dict(module("infoset").disposition(etat, 0))

    assert set(disposition) == set(attendues), (
        f"{instance.nom} : blocs {sorted(disposition)} au lieu de {sorted(attendues)}"
    )
    for nom, longueur in attendues.items():
        assert disposition[nom] == longueur, (
            f"{instance.nom} : le bloc {nom} fait {disposition[nom]} au lieu de {longueur}"
        )
    assert sum(disposition.values()) == len(etat.information_state_tensor(0))


# ---------------------------------------------------------------------------------
# Contenu, recalcule independamment
# ---------------------------------------------------------------------------------


def _attendu(etat: Any, joueur: int, instance: Instance) -> dict[str, list[float]]:
    """Recalcule chaque bloc depuis la vue de dieu, d'apres le paragraphe 4.2."""
    vue = etat.vue_privilegiee()
    joueurs = instance.joueurs
    roles = list(instance.roles)
    visibles = _roles_visibles(instance)

    def au_joueur(autre: int) -> int:
        return (joueur + autre) % joueurs

    def posees_ou(genre: str, **criteres: Any) -> list[Any]:
        retenues = []
        for posee in vue.posees:
            if posee.zone.genre.name != genre:
                continue
            if "position" in criteres and posee.zone.position.name != criteres["position"]:
                continue
            if (
                "proprietaire" in criteres
                and posee.zone.proprietaire != criteres["proprietaire"]
            ):
                continue
            retenues.append(posee)
        return retenues

    def compte(cartes: Any, famille: int, nom_role: str) -> int:
        return sum(
            1 for c in cartes if c.famille == famille and c.role.name == nom_role
        )

    main = list(vue.mains[joueur])
    mortes = [posee.carte for posee in vue.defausse]

    bloc_main: list[float] = []
    bloc_residu: list[float] = []
    bloc_morts: list[float] = []
    bloc_banquet_visible: list[float] = []
    bloc_banquet_prive: list[float] = []
    bloc_domaine_visible: list[float] = []
    bloc_domaine_prive: list[float] = []

    for famille in range(instance.familles):
        for nom_role in roles:
            en_main = compte(main, famille, nom_role)
            en_defausse = compte(mortes, famille, nom_role)
            # Connues : les faces visibles, plus mes propres Espions.
            connues = sum(
                1
                for posee in vue.posees
                if posee.carte.famille == famille
                and posee.carte.role.name == nom_role
                and (nom_role != "ESPION" or posee.poseur == joueur)
            )
            bloc_main.append(en_main)
            bloc_morts.append(en_defausse)
            # Le residu retranche les morts (regle 2 du paragraphe 4.2).
            bloc_residu.append(
                instance.exemplaires - connues - en_main - en_defausse
            )
        for nom_role in visibles:
            for position in ("ESTIME", "DISGRACE"):
                bloc_banquet_visible.append(
                    compte(
                        [p.carte for p in posees_ou("BANQUET", position=position)],
                        famille,
                        nom_role,
                    )
                )
            for autre in range(joueurs):
                bloc_domaine_visible.append(
                    compte(
                        [
                            p.carte
                            for p in posees_ou("DOMAINE", proprietaire=au_joueur(autre))
                        ],
                        famille,
                        nom_role,
                    )
                )
        for position in ("ESTIME", "DISGRACE"):
            bloc_banquet_prive.append(
                sum(
                    1
                    for p in posees_ou("BANQUET", position=position)
                    if p.carte.role.name == "ESPION"
                    and p.carte.famille == famille
                    and p.poseur == joueur
                )
            )
        for autre in range(joueurs):
            bloc_domaine_prive.append(
                sum(
                    1
                    for p in posees_ou("DOMAINE", proprietaire=au_joueur(autre))
                    if p.carte.role.name == "ESPION"
                    and p.carte.famille == famille
                    and p.poseur == joueur
                )
            )

    dos_banquet: list[float] = []
    dos_domaine: list[float] = []
    for autre in range(1, joueurs):
        poseur = au_joueur(autre)
        for position in ("ESTIME", "DISGRACE"):
            dos_banquet.append(
                sum(
                    1
                    for p in posees_ou("BANQUET", position=position)
                    if p.carte.role.name == "ESPION" and p.poseur == poseur
                )
            )
        for domaine in range(joueurs):
            dos_domaine.append(
                sum(
                    1
                    for p in posees_ou("DOMAINE", proprietaire=au_joueur(domaine))
                    if p.carte.role.name == "ESPION" and p.poseur == poseur
                )
            )

    assassin = etat.assassin_en_resolution()
    genre = [0, 0]
    position_assassin = [0, 0]
    domaine_assassin = [0] * joueurs
    if assassin is not None:
        genre[0 if assassin.zone.genre.name == "BANQUET" else 1] = 1
        if assassin.zone.position is not None:
            position_assassin[0 if assassin.zone.position.name == "ESTIME" else 1] = 1
        if assassin.zone.proprietaire is not None:
            domaine_assassin[(assassin.zone.proprietaire - joueur) % joueurs] = 1

    return {
        "main": bloc_main,
        "banquet_visible": bloc_banquet_visible,
        "banquet_prive": bloc_banquet_prive,
        "domaine_visible": bloc_domaine_visible,
        "domaine_prive": bloc_domaine_prive,
        "residu": bloc_residu,
        "morts": bloc_morts,
        "dos_adverses_banquet": dos_banquet,
        "dos_adverses_domaine": dos_domaine,
        "tours_restants": [etat.tours_restants(au_joueur(a)) for a in range(joueurs)],
        "pioche": [len(vue.pioche)],
        "morts_total": [len(vue.defausse)],
        "phase": [
            1 if etat.phase().name == "POSE" else 0,
            1 if etat.phase().name == "CIBLAGE" else 0,
        ],
        "assassin": [*genre, *position_assassin, *domaine_assassin],
        "assassins_restants": [len(etat.assassins_en_attente())],
    }


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_chaque_bloc_vaut_ce_que_le_paragraphe_4_2_exige(instance: Instance) -> None:
    _, moteur = construire(instance)
    controles = 0

    for seed, etat in parcourir_decisions(moteur, NB_PARTIES):
        for joueur in range(instance.joueurs):
            obtenu = _blocs_du_tenseur(etat, joueur)
            attendu = _attendu(etat, joueur, instance)
            for nom, valeurs in attendu.items():
                assert obtenu[nom] == [float(v) for v in valeurs], (
                    f"{instance.nom}, seed {seed}, joueur {joueur} : bloc {nom} vaut "
                    f"{obtenu[nom]} au lieu de {valeurs}"
                )
            controles += 1

    assert controles > 0


# ---------------------------------------------------------------------------------
# Les trois pieges, isoles
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_le_residu_diminue_quand_une_carte_meurt(instance: Instance) -> None:
    """Piege 2 : une carte tuee n'est plus visible ; la compter comme en circulation
    surestime le residu de jusqu'a 20 % du paquet."""
    _, moteur = construire(instance)
    morts_rencontrees = 0

    for seed in range(NB_PARTIES):
        etat = partie(moteur, seed)
        vue = etat.vue_privilegiee()
        if not vue.defausse:
            continue
        morts_rencontrees += 1

        for joueur in range(instance.joueurs):
            residu = _blocs_du_tenseur(etat, joueur)["residu"]
            attendu = _attendu(etat, joueur, instance)["residu"]
            assert residu == [float(v) for v in attendu]
            assert sum(residu) == len(vue.pioche) + sum(
                len(main) for autre, main in enumerate(vue.mains) if autre != joueur
            ) + sum(
                1
                for posee in vue.posees
                if posee.carte.role.name == "ESPION" and posee.poseur != joueur
            ), (
                f"{instance.nom}, seed {seed}, joueur {joueur} : le residu ne vaut pas ce "
                f"qui circule encore -- des cartes mortes y sont comptees"
            )

    assert morts_rencontrees > 0, f"{instance.nom} : aucune partie avec mort"


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_la_phase_et_la_zone_de_l_assassin_sont_encodees(instance: Instance) -> None:
    """Piege 3 : sans elles, deux poses differentes donnent le meme tenseur avec des
    cibles totalement differentes."""
    _, moteur = construire(instance)
    vus_en_pose = 0
    vus_en_ciblage = 0
    zones_vues: set[tuple[float, ...]] = set()

    for _seed, etat in parcourir_decisions(moteur, NB_PARTIES):
        blocs = _blocs_du_tenseur(etat, etat.current_player())
        if etat.phase().name == "POSE":
            vus_en_pose += 1
            assert blocs["phase"] == [1.0, 0.0]
            assert blocs["assassin"] == [0.0] * len(blocs["assassin"])
            assert blocs["assassins_restants"] == [0.0]
        else:
            vus_en_ciblage += 1
            assert blocs["phase"] == [0.0, 1.0]
            assert sum(blocs["assassin"]) >= 2, "genre et position ou domaine attendus"
            assert blocs["assassins_restants"][0] >= 1
            zones_vues.add(tuple(blocs["assassin"]))

    assert vus_en_pose > 0
    assert vus_en_ciblage > 0
    assert len(zones_vues) >= 2, (
        f"{instance.nom} : une seule zone d'Assassin observee, le bloc ne distingue rien"
    )


def test_le_score_encode_n_est_pas_le_vrai_score() -> None:
    """Piege non ecrit dans la specification : les Espions adverses poses dans un domaine
    comptent au decompte, mais leur famille est cachee. Encoder `scores()` ferait fuiter
    exactement ce que I7 interdit."""
    instance = RAPIDE_3J
    _, moteur = construire(instance)
    pioche_a, pioche_b, _, _ = pioches_jumelles_espion(instance, joueur=0)

    ecarts = 0
    for pioche in (pioche_a, pioche_b):
        etat = moteur.reset_depuis_pioche(pioche)
        rng = random.Random(5)
        while not etat.is_terminal():
            etat.apply(rng.choice(actions_legales(etat)))

        vrais = scores_moteur(etat, instance)
        for joueur in range(instance.joueurs):
            visibles = _blocs_du_tenseur(etat, joueur)["scores_visibles"]
            relatifs = [
                float(vrais[(joueur + autre) % instance.joueurs])
                for autre in range(instance.joueurs)
            ]
            if visibles != relatifs:
                ecarts += 1

    assert ecarts > 0, (
        "le score encode coincide toujours avec le vrai score : soit aucun Espion n'a ete "
        "pose en domaine, soit le vrai score est encode -- et alors I7 est viole"
    )
