"""Les huit criteres d'acceptation du paragraphe 7 de 03_specification_moteur.md.

Quatre criteres sont deja portes par un test ailleurs, et ne sont **pas** dupliques ici --
un critere verifie a deux endroits est un critere qu'on peut satisfaire a moitie sans que
rien ne le dise :

  A4  le coeur sans OpenSpiel, NumPy ni PyTorch
      -> tests/adaptateur/test_openspiel.py, en sous-processus, avec temoin positif
  A5  aucune valeur en dur, cinq configurations distinctes
      -> tests/config/test_gameconfig.py
  A7  couverture du coeur >= 90 %
      -> mesure hors pytest : uv run pytest --cov=courtisans
  A8  une GameConfig non conforme leve
      -> tests/config/test_gameconfig.py, 26 cas de refus

Restent ceux qui n'avaient pas de test dedie : A1 et A2, dont personne ne verifiait la
**completude**, A3, qui n'avait jamais tourne a son volume, et A6, dont la formulation
exige deux executions distinctes -- ce qu'un test en memoire ne peut pas prouver.
"""

from __future__ import annotations

import os
import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.outils import (
    COMPLET_3J,
    TOUTES_LES_INSTANCES,
    actions_legales,
    construire,
)

RACINE = Path(__file__).resolve().parents[2]

#: A3 : « une partie complete a 3 joueurs se joue de bout en bout sans exception, sur
#: 1 000 parties aleatoires, avec les trois joueurs jouant le meme nombre de tours ».
NB_PARTIES_A3 = 1000

#: A6 : joue une partie entiere depuis un seed et imprime une signature. Execute dans deux
#: processus distincts, avec des PYTHONHASHSEED differents.
SCRIPT_A6 = """
import random
from courtisans.cards import Role
from courtisans.config import GameConfig
from courtisans.engine import Engine

config = GameConfig(familles=6, roles=tuple(Role), exemplaires=3, joueurs=3)
etat = Engine(config).reset(20260816)
rng = random.Random(20260816)
actions = []
while not etat.is_terminal():
    legales = sorted(etat.legal_actions())
    action = rng.choice(legales)
    actions.append(action)
    etat.apply(action)
vue = etat.vue_privilegiee()
plateau = sorted(
    (p.carte.famille, p.carte.role.name, p.carte.exemplaire,
     p.zone.genre.name, getattr(p.zone.position, "name", "-"), p.zone.proprietaire, p.poseur)
    for p in list(vue.posees) + list(vue.defausse)
)
print(len(actions), "".join(map(str, actions)), etat.scores(), plateau)
"""


def _executer(script: str, hashseed: str) -> str:
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
    assert resultat.returncode == 0, resultat.stderr
    return resultat.stdout.strip()


# ---------------------------------------------------------------------------------
# A1 et A2 -- la suite est-elle complete ?
# ---------------------------------------------------------------------------------


def test_a1_les_dix_huit_controles_de_conformite_existent() -> None:
    """Un controle absent ne fait echouer aucun test : rien ne signale son absence."""
    fichiers = sorted((RACINE / "tests" / "conformite").glob("test_c*.py"))
    numeros = {int(re.match(r"test_c(\d+)_", f.name).group(1)) for f in fichiers}

    assert numeros == set(range(1, 19)), (
        f"controles manquants : {sorted(set(range(1, 19)) - numeros)} ; "
        f"controles en trop : {sorted(numeros - set(range(1, 19)))}"
    )


def test_a1_les_trois_nombres_de_joueurs_sont_couverts() -> None:
    joueurs = {instance.joueurs for instance in TOUTES_LES_INSTANCES}
    assert {2, 3, 4} <= joueurs, f"nombres de joueurs couverts : {sorted(joueurs)}"


def test_a2_les_onze_invariants_existent_et_sur_assez_de_configurations() -> None:
    fichiers = sorted((RACINE / "tests" / "invariants").glob("test_i*.py"))
    numeros = {int(re.match(r"test_i(\d+)_", f.name).group(1)) for f in fichiers}

    assert numeros == set(range(1, 12)), (
        f"invariants manquants : {sorted(set(range(1, 12)) - numeros)}"
    )
    assert len(TOUTES_LES_INSTANCES) >= 5, (
        f"{len(TOUTES_LES_INSTANCES)} configurations, le critere en demande au moins 5"
    )
    assert len({i.nb_cartes for i in TOUTES_LES_INSTANCES}) >= 3


# ---------------------------------------------------------------------------------
# A3 -- 1 000 parties a 3 joueurs, paquet complet
# ---------------------------------------------------------------------------------


@pytest.mark.lent
def test_a3_mille_parties_a_trois_joueurs_sur_paquet_complet() -> None:
    """Le critere le plus important avec A1 : le moteur joue le jeu, a la cible visee."""
    instance = COMPLET_3J
    config, moteur = construire(instance)
    assert instance.joueurs == 3
    assert instance.nb_cartes == 90
    assert instance.tours == 10

    cartes_posees = set()
    scores_vus = set()

    for seed in range(NB_PARTIES_A3):
        etat = moteur.reset(seed)
        rng = random.Random(seed)
        tours = [0] * instance.joueurs

        while not etat.is_terminal():
            if etat.phase().name == "POSE":
                tours[etat.current_player()] += 1
            etat.apply(rng.choice(actions_legales(etat)))

        assert tours == [instance.tours] * instance.joueurs, (
            f"seed {seed} : tours {tours} au lieu de {[instance.tours] * 3}"
        )
        vue = etat.vue_privilegiee()
        cartes_posees.add(len(vue.posees) + len(vue.defausse))
        scores_vus.add(tuple(sorted(etat.scores().values())))
        assert sum(etat.returns()) == pytest.approx(0.0)

    assert cartes_posees == {config.cartes_jouees}, (
        f"cartes posees observees : {sorted(cartes_posees)}, attendu "
        f"{config.cartes_jouees}"
    )
    assert len(scores_vus) > 1, "1 000 parties aleatoires donnent toutes le meme score"


# ---------------------------------------------------------------------------------
# A6 -- deux executions distinctes
# ---------------------------------------------------------------------------------


def test_a6_meme_seed_meme_partie_dans_deux_processus() -> None:
    """« `reset(seed)` reproduit la meme partie sur deux executions distinctes. »

    Un test en memoire ne peut pas le prouver : dans un meme processus, le hachage est
    fige et l'ordre d'iteration des ensembles est stable. Deux processus, deux
    `PYTHONHASHSEED`.
    """
    premiere = _executer(SCRIPT_A6, "0")
    seconde = _executer(SCRIPT_A6, "12345")

    assert premiere == seconde, (
        "deux executions distinctes du meme seed donnent deux parties differentes"
    )
    assert premiere, "le script n'a rien imprime"
