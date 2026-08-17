"""Deux contrats que la mutation a montres trop peu couverts.

MESURE a l'etape 7 : la mutation `doublons-non-masques` n'etait attrapee que par **2**
tests, `main-non-triee` par **4**. Ce sont les deux plus proches de survivre, donc les
deux endroits ou un defaut reel passerait le plus facilement.

Les controles ajoutes ici sont **comportementaux** : ils n'interrogent pas
`rules.actions_de_pose_legales` ni `rules.main_canonique`, ils appliquent les actions et
regardent le plateau obtenu. Un test qui redemande au module ce que le module vient de
calculer ne prouve rien -- c'est la lecon de l'etape 6.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    TOUTES_LES_INSTANCES,
    Instance,
    cle,
    cle_canonique,
    construire,
    noms,
    parcourir_decisions,
    signature_zone,
)

NB_PARTIES = 8


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_deux_actions_de_pose_legales_donnent_deux_plateaux_differents(
    instance: Instance,
) -> None:
    """Le masquage, verifie en jouant les actions plutot qu'en decodant leurs indices.

    Chaque action legale est appliquee sur un clone ; les plateaux obtenus doivent etre
    deux a deux distincts. Si un doublon survivait au masquage, deux actions produiraient
    le meme etat, l'arbre porterait deux fois la meme branche, et le nombre d'info-sets
    serait gonfle d'autant.

    **Les plateaux sont compares a l'exemplaire pres.** Deux cartes de meme famille et de
    meme role sont interchangeables : leur numero d'exemplaire ne change rien au jeu.
    Comparer des plateaux qui le portent ferait passer pour deux coups differents deux
    coups qui donnent le meme etat -- et le test laisserait passer exactement le defaut
    qu'il cherche. MESURE : sans cette precaution, la mutation `doublons-non-masques`
    survivait a ce test.
    """
    _, moteur = construire(instance)
    noeuds = 0
    doublons_possibles = 0

    for seed, etat in parcourir_decisions(moteur, NB_PARTIES):
        if etat.phase().name != "POSE":
            continue
        noeuds += 1

        main = etat.vue_privilegiee().mains[etat.current_player()]
        types = {(carte.famille, carte.role) for carte in main}
        if len(types) < len(main):
            doublons_possibles += 1

        plateaux: dict[tuple, int] = {}
        for action in etat.legal_actions():
            clone = etat.clone()
            clone.apply(action)
            vue = clone.vue_privilegiee()
            plateau = tuple(
                sorted(
                    (
                        posee.carte.famille,
                        posee.carte.role.name,
                        signature_zone(posee.zone),
                        posee.poseur,
                    )
                    for posee in list(vue.posees) + list(vue.defausse)
                )
            )
            assert plateau not in plateaux, (
                f"{instance.nom}, seed {seed} : les actions {plateaux[plateau]} et "
                f"{action} laissent le meme plateau -- doublon non masque"
            )
            plateaux[plateau] = action

    assert noeuds > 0
    assert doublons_possibles > 0, (
        f"{instance.nom} : aucune main a doublon rencontree sur {NB_PARTIES} parties, "
        f"le masquage n'est jamais exerce"
    )


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_la_main_exposee_est_toujours_dans_l_ordre_canonique(
    instance: Instance,
) -> None:
    """Regle R-c : `vue_privilegiee().mains[j]` est l'ordre sur lequel les actions indexent.

    C'est le contrat dont depend tout le decodage des poses. Sans lui, une action designe
    une carte differente selon l'etat, et l'encodage cesse d'etre markovien.
    """
    _, moteur = construire(instance)
    mains_vues = 0

    for seed, etat in parcourir_decisions(moteur, NB_PARTIES):
        for joueur, main in enumerate(etat.vue_privilegiee().mains):
            if not main:
                continue
            mains_vues += 1
            rangs = [cle_canonique(carte) for carte in main]
            assert rangs == sorted(rangs), (
                f"{instance.nom}, seed {seed} : la main du joueur {joueur} n'est pas "
                f"triee -- {[cle(carte) for carte in main]}"
            )

    assert mains_vues > 0
