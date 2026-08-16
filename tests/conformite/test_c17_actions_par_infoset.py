"""C17 -- prerequis IA, cite au paragraphe 9 de 01_regles.md.

« Tous les etats d'un meme info-set exposent le meme ensemble d'actions legales. »

Si deux etats indistinguables pour le joueur courant offraient des actions differentes, la
politique serait definie sur un support qui depend d'une information que le joueur n'a
pas : ni CFR ni l'apprentissage par renforcement n'ont alors de garantie.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    NB_PARTIES_INFOSET,
    Instance,
    construire,
    noms,
    parcourir_decisions,
)


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_c17_un_info_set_expose_toujours_les_memes_actions(instance: Instance) -> None:
    _, moteur = construire(instance)
    actions_par_chaine: dict[str, tuple[int, ...]] = {}
    phase_par_chaine: dict[str, str] = {}
    noeuds = 0

    for seed, etat in parcourir_decisions(moteur, NB_PARTIES_INFOSET):
        joueur = etat.current_player()
        if joueur < 0:
            continue
        noeuds += 1

        chaine = etat.information_state_string(joueur)
        actions = tuple(sorted(etat.legal_actions()))
        phase = etat.phase().name

        if chaine in actions_par_chaine:
            assert actions_par_chaine[chaine] == actions, (
                f"{instance.nom}, seed {seed} : l'info-set\n  {chaine}\nexpose "
                f"{actions_par_chaine[chaine]} puis {actions}"
            )
            assert phase_par_chaine[chaine] == phase, (
                f"{instance.nom}, seed {seed} : l'info-set\n  {chaine}\napparait en phase "
                f"{phase_par_chaine[chaine]} puis {phase}"
            )
        else:
            actions_par_chaine[chaine] = actions
            phase_par_chaine[chaine] = phase

    assert noeuds > 0
    assert len(actions_par_chaine) > instance.joueurs * instance.tours
