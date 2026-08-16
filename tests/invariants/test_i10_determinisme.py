"""I10 -- 03_specification_moteur.md paragraphe 5.

« `reset(seed)` est deterministe : meme seed, meme partie, sur toute plateforme. »

Trois controles, dont le dernier est le seul a mordre :

  1. deux moteurs distincts, meme seed : les etats sont identiques, empreinte par empreinte,
     tout au long d'une partie rejouee avec la meme suite d'actions ;
  2. deux seeds distincts donnent des pioches distinctes -- sinon le seed ne sert a rien et
     le controle 1 serait vide ;
  3. **meme seed, `PYTHONHASHSEED` different** : la pioche doit etre la meme. C'est ce qui
     attrape la dependance a l'ordre d'iteration d'un `set` ou d'un `dict`, interdite par le
     paragraphe 5 des conventions de code. Sans ce controle, un moteur non deterministe
     passe les deux premiers sans difficulte, parce que dans un meme processus Python le
     hachage est fige.

« Sur toute plateforme » n'est pas testable ici : on ne dispose que de celle-ci. Le controle
3 en teste la cause la plus frequente.
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
    TOUTES_LES_INSTANCES,
    Instance,
    actions_legales,
    construire,
    empreinte,
    noms,
)

#: Deux instances suffisent pour le controle par sous-processus : il coute trois demarrages
#: de Python par cas, et ce qu'il cherche ne depend pas de la configuration.
INSTANCES_SOUS_PROCESSUS = INSTANCES_RAPIDES[:2]

NB_PARTIES = 10
RACINE = Path(__file__).resolve().parents[2]

#: Imprime l'ordre de la pioche produit par un seed. Execute dans un processus separe, avec
#: un PYTHONHASHSEED impose : c'est le seul moyen d'observer une dependance au hachage.
SCRIPT_EMPREINTE = """
import sys
from courtisans.cards import Role
from courtisans.config import GameConfig
from courtisans.engine import Engine

config = GameConfig(
    familles={familles},
    roles=tuple(getattr(Role, nom) for nom in {roles!r}),
    exemplaires={exemplaires},
    joueurs={joueurs},
)
pioche = Engine(config).pioche_depuis_seed({seed})
print(";".join(f"{{c.famille}}-{{c.role.name}}-{{c.exemplaire}}" for c in pioche))
"""


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_i10_meme_seed_meme_partie(instance: Instance) -> None:
    _, moteur_a = construire(instance)
    _, moteur_b = construire(instance)

    for seed in range(NB_PARTIES):
        etat_a = moteur_a.reset(seed)
        etat_b = moteur_b.reset(seed)
        rng = random.Random(seed)

        pas = 0
        while not etat_a.is_terminal():
            assert empreinte(etat_a, instance) == empreinte(etat_b, instance), (
                f"{instance.nom}, seed {seed} : divergence au pas {pas}"
            )
            action = rng.choice(actions_legales(etat_a))
            etat_a.apply(action)
            etat_b.apply(action)
            pas += 1

        assert etat_b.is_terminal()
        assert empreinte(etat_a, instance) == empreinte(etat_b, instance)


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_i10_deux_seeds_donnent_deux_pioches(instance: Instance) -> None:
    """Garde-fou : sans lui, un moteur qui ignore le seed passerait le test precedent."""
    _, moteur = construire(instance)
    pioches = {
        tuple((c.famille, c.role.name, c.exemplaire) for c in moteur.pioche_depuis_seed(seed))
        for seed in range(NB_PARTIES)
    }
    assert len(pioches) > 1, (
        f"{instance.nom} : {NB_PARTIES} seeds donnent la meme pioche -- le seed est ignore"
    )


@pytest.mark.parametrize(
    "instance", INSTANCES_SOUS_PROCESSUS, ids=noms(INSTANCES_SOUS_PROCESSUS)
)
def test_i10_la_pioche_ne_depend_pas_du_hachage(instance: Instance) -> None:
    script = SCRIPT_EMPREINTE.format(
        familles=instance.familles,
        roles=list(instance.roles),
        exemplaires=instance.exemplaires,
        joueurs=instance.joueurs,
        seed=1234,
    )
    sorties = []
    for hashseed in ("0", "1", "42"):
        environnement = dict(os.environ)
        environnement["PYTHONHASHSEED"] = hashseed
        environnement["PYTHONPATH"] = str(RACINE)
        resultat = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=RACINE,
            env=environnement,
            check=False,
        )
        assert resultat.returncode == 0, (
            f"{instance.nom} : le sous-processus a echoue avec PYTHONHASHSEED={hashseed}\n"
            f"{resultat.stderr}"
        )
        sorties.append(resultat.stdout.strip())

    assert len(set(sorties)) == 1, (
        f"{instance.nom} : la pioche depend de PYTHONHASHSEED -- une decision de regle "
        f"repose sur l'ordre d'iteration d'un set ou d'un dict"
    )
