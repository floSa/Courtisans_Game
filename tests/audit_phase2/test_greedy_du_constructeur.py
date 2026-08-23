"""Controles hostiles de l'auditeur contre le greedy du constructeur.

Ecrits **apres** les miens et **sans les siens** : `tests/agents/` n'a pas ete lu avant que
ce fichier existe. Deux d'entre eux sont les cas construits a la main dont l'attendu se
calcule de tete, un troisieme est l'aveuglement differentiel exige par le prompt d'audit --
et il compare le **vecteur d'evaluation entier**, pas l'action tiree : deux politiques
peuvent choisir la meme action par chance de departage tout en evaluant differemment.
"""

from __future__ import annotations

import random

import pytest

from agents.greedy import choisir, evaluer_actions
from agents.perception import percevoir
from audit.phase2.decompte import scores
from courtisans.cards import Carte, Position, Role
from courtisans.engine import Engine
from tests.audit_phase2.outils import INSTANCE, banquet, domaine, etat_de_ciblage
from tests.audit_phase2.test_greedy_auditeur import (
    _paire_differant_par_un_dos,
    _position_ou_tuer_coute,
    _position_ou_tuer_rapporte,
)

ALEA = 20260819


def _decider(etat, joueur=None):
    """L'action du greedy du constructeur sur cet etat, graine fixee."""
    joueur = etat.current_player() if joueur is None else joueur
    return choisir(percevoir(etat, joueur), random.Random(ALEA))


def _evaluations(etat, joueur=None) -> dict[int, int]:
    """Le vecteur d'evaluation complet, avant tout departage."""
    joueur = etat.current_player() if joueur is None else joueur
    return evaluer_actions(percevoir(etat, joueur))


# ---------------------------------------------------------------------------------
# Les deux positions construites a la main
# ---------------------------------------------------------------------------------


def test_son_greedy_refuse_quand_le_meurtre_lui_couterait():
    """Attendu calcule de tete : refuser vaut 1, tuer vaut 0. Il doit refuser."""
    etat, _ = _position_ou_tuer_coute()
    assert scores(etat.vue_privilegiee().posees, 4, 3) == [1, 0, 0]
    refus = len(etat.cibles_courantes())
    valeurs = _evaluations(etat)
    assert valeurs == {0: 0, refus: 1}, "l'evaluation elle-meme doit separer les deux"
    assert _decider(etat) == refus


def test_son_greedy_tue_quand_le_meurtre_lui_rapporte():
    """Le controle symetrique : tuer remonte J0 de -1 a 0. Il doit tuer."""
    etat, _ = _position_ou_tuer_rapporte()
    assert scores(etat.vue_privilegiee().posees, 4, 3) == [-1, 0, 0]
    valeurs = _evaluations(etat)
    assert valeurs == {0: 0, 1: -1}
    assert _decider(etat) == 0


# ---------------------------------------------------------------------------------
# L'aveuglement differentiel -- la cible numero un de cet audit
# ---------------------------------------------------------------------------------


def test_son_greedy_evalue_a_l_identique_deux_plateaux_qui_ne_different_que_par_un_dos():
    """Deux etats identiques a l'identite pres d'un Espion adverse au banquet.

    On compare le **vecteur d'evaluation entier** : si une seule action recevait une valeur
    differente, la politique lirait la vue de dieu, et M3 comme M4 seraient a refaire.
    """
    a, b = _paire_differant_par_un_dos()
    assert a.information_state_string(0) == b.information_state_string(0)
    assert _evaluations(a, 0) == _evaluations(b, 0)
    assert _decider(a, 0) == _decider(b, 0)


def test_son_greedy_est_aveugle_a_un_dos_qui_est_une_cible():
    """Le cas ou l'identite est la plus a portee de main : le dos est une **cible**.

    `State.cibles_courantes()` rend de vrais `CartePosee`, identite comprise. Une politique
    qui lirait `cible.carte.famille` evaluerait les deux plateaux differemment.
    """
    commun = [
        banquet(Carte(2, Role.NOBLE, 0), Position.DISGRACE, poseur=2),
        domaine(Carte(2, Role.NEUTRE, 0), proprietaire=0, poseur=1),
    ]
    vecteurs = []
    for famille in (0, 3):
        assassin = banquet(Carte(1, Role.ASSASSIN, 0), Position.DISGRACE, poseur=0)
        dos = banquet(Carte(famille, Role.ESPION, 1), Position.DISGRACE, poseur=1)
        etat = etat_de_ciblage([*commun, dos, assassin], assassin, joueur=0)
        assert len(etat.cibles_courantes()) == 2
        vecteurs.append(_evaluations(etat, 0))
    assert vecteurs[0] == vecteurs[1]


def test_son_greedy_est_aveugle_sur_un_balayage_de_parties_entieres():
    """L'aveuglement sur des positions **atteintes en jeu**, pas seulement construites.

    A chaque noeud d'une vraie partie, l'identite de chaque dos adverse est permutee vers
    une autre famille et le vecteur d'evaluation est recalcule. Un cas construit a la main
    ne visite qu'une poignee de configurations ; celui-ci en visite des milliers, et c'est
    la seule facon d'exclure une fuite qui ne s'exprimerait que dans un cas de figure rare.
    """
    from courtisans.cards import ROLES_CACHES, CartePosee

    engine = Engine(INSTANCE)
    alea = random.Random(4242)
    noeuds = 0
    permutes = 0
    for seed in range(60):
        etat = engine.reset(seed)
        while not etat.is_terminal():
            joueur = etat.current_player()
            reference = _evaluations(etat, joueur)
            noeuds += 1
            jumeau = etat.clone()
            change = False
            for rang, posee in enumerate(jumeau._posees):
                if posee.carte.role in ROLES_CACHES and posee.poseur != joueur:
                    nouvelle = Carte(
                        (posee.carte.famille + 1) % INSTANCE.familles,
                        posee.carte.role,
                        posee.carte.exemplaire,
                    )
                    jumeau._posees[rang] = CartePosee(nouvelle, posee.zone, posee.poseur)
                    change = True
            if change:
                permutes += 1
                assert _evaluations(jumeau, joueur) == reference, (
                    f"seed {seed} : l'evaluation depend de l'identite d'un dos adverse"
                )
            etat.apply(choisir(percevoir(etat, joueur), alea))
    assert permutes > 200, f"balayage trop maigre : {permutes} noeuds portaient un dos"


# ---------------------------------------------------------------------------------
# La coherence interne de son horizon
# ---------------------------------------------------------------------------------


def test_l_ecart_entre_la_valeur_promise_et_la_valeur_realisee_est_caracterise():
    """Sa pose est evaluee Assassins resolus **conjointement au mieux** ; ses ciblages, eux,
    se decident un noeud a la fois, sans regarder les Assassins encore en attente.

    **Ce test interdisait l'ecart au tour 1 ; il le caracterise au tour 2.** Le constructeur
    a repondu en documentant l'incoherence plutot qu'en la corrigeant -- paragraphe 4 bis du
    rapport, `mesure/coherence_greedy.py` --, et il a raison de le faire ici : la ligne de
    base de toutes les phases suivantes est celle de **cet** agent, et la corriger apres
    publication deplacerait l'etalon. Un test qui interdirait encore l'ecart rendrait donc
    rouge une decision acceptee, ce qui est un faux rapport dans l'autre sens.

    Ce qui est tenu desormais : l'ecart **existe** -- sinon la section 4 bis decrirait un
    phenomene absent -- et il reste **rare**, sous 2 % des tours. Un elargissement silencieux
    casserait ce test, et c'est ce qu'on veut de lui.
    """
    engine = Engine(INSTANCE)
    alea = random.Random(777)
    tours_a_deux_assassins = 0
    desaccords = []
    for seed in range(400):
        etat = engine.reset(seed)
        while not etat.is_terminal():
            joueur = etat.current_player()
            perception = percevoir(etat, joueur)
            if perception.phase.name == "POSE":
                action = choisir(perception, alea)
                annoncee = evaluer_actions(perception)[action]
                etat.apply(action)
                if len(etat.assassins_en_attente()) >= 2:
                    tours_a_deux_assassins += 1
                while etat.phase().name == "CIBLAGE" and etat.current_player() == joueur:
                    etat.apply(choisir(percevoir(etat, joueur), alea))
                from agents.greedy import evaluer
                from courtisans.infoset import vue_du_joueur

                realisee = evaluer(
                    vue_du_joueur(etat, joueur).connues, joueur, INSTANCE
                )
                if realisee != annoncee:
                    desaccords.append((seed, annoncee, realisee))
            else:  # pragma: no cover - la boucle interne consomme deja les ciblages
                etat.apply(choisir(percevoir(etat, joueur), alea))
    assert tours_a_deux_assassins > 0, "le cas a tester ne s'est jamais presente"
    tours = 400 * INSTANCE.joueurs * INSTANCE.tours
    assert desaccords, (
        "aucun ecart : le paragraphe 4 bis du rapport decrirait alors un phenomene absent"
    )
    part = len(desaccords) / tours
    assert part < 0.02, (
        f"{len(desaccords)} / {tours} tours = {100 * part:.2f} % : l'ecart s'est elargi "
        f"au-dela de ce que le rapport caracterise ; trois premiers {desaccords[:3]}"
    )


# ---------------------------------------------------------------------------------
# Le renommage de `courtisans/infoset.py`, seul fichier du moteur touche par la phase
# ---------------------------------------------------------------------------------


def test_le_passage_en_public_de_vue_du_joueur_ne_change_ni_chaine_ni_tenseur():
    """`vue_du_joueur` etait `_vue_du_joueur` : la sortie observable doit etre identique.

    L'ancienne implementation est **reecrite ici depuis le paragraphe 4.2 des regles** et
    confrontee a la nouvelle sur toutes les vues de 120 parties, puis `chaine` et `tenseur`
    sont compares a une serialisation calculee sur cette partition independante.
    """
    from courtisans.cards import ROLES_CACHES
    from courtisans.infoset import chaine, tenseur, vue_du_joueur

    engine = Engine(INSTANCE)
    alea = random.Random(9)
    vues = 0
    for seed in range(120):
        etat = engine.reset(seed)
        while not etat.is_terminal():
            for joueur in range(INSTANCE.joueurs):
                attendu_connues = tuple(
                    p
                    for p in etat.vue_privilegiee().posees
                    if not (p.carte.role in ROLES_CACHES and p.poseur != joueur)
                )
                attendu_dos = tuple(
                    p
                    for p in etat.vue_privilegiee().posees
                    if p.carte.role in ROLES_CACHES and p.poseur != joueur
                )
                vue = vue_du_joueur(etat, joueur)
                assert vue.connues == attendu_connues
                assert vue.dos_adverses == attendu_dos
                assert len(chaine(etat, joueur)) > 0
                assert len(tenseur(etat, joueur)) == len(
                    tenseur(engine.reset(seed), joueur)
                )
                vues += 1
            etat.apply(choisir(percevoir(etat, etat.current_player()), alea))
    assert vues > 6000, f"balayage trop maigre : {vues} vues comparees"


def test_le_corps_de_vue_du_joueur_est_inchange_par_le_renommage():
    """Comparaison **textuelle** des deux corps, ancien et nouveau, hors docstring.

    Une fonction rendue publique est une fonction dont un agent depend : si son corps avait
    bouge en meme temps que son nom, le renommage aurait masque un changement de
    comportement.
    """
    import ast
    import subprocess

    def corps(source: str) -> str:
        arbre = ast.parse(source)
        fonction = next(
            n
            for n in ast.walk(arbre)
            if isinstance(n, ast.FunctionDef) and n.name.lstrip("_") == "vue_du_joueur"
        )
        instructions = fonction.body
        if instructions and isinstance(instructions[0], ast.Expr):
            instructions = instructions[1:]  # la docstring, seule chose qui a le droit
        return "\n".join(ast.dump(n) for n in instructions)

    avant = subprocess.run(
        ["git", "show", "19f99f2:courtisans/infoset.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    apres = subprocess.run(
        ["git", "show", "02ae24b:courtisans/infoset.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert corps(avant) == corps(apres)


@pytest.mark.parametrize("joueur", [-1, 3, 99])
def test_vue_du_joueur_publique_refuse_un_identifiant_qui_n_est_pas_un_siege(joueur):
    """Une fonction publique est appelable par n'importe qui : elle doit se defendre.

    `_joueur_observe` protege `information_state_string` ; `vue_du_joueur`, devenue une API
    d'agent, etait appelable **sans** passer par lui. Elle l'appelle depuis le 20/08/2026.

    **Ce cas affirmait l'inverse de ce que son nom annonce, et c'est un defaut a part
    entiere.** Ecrit au tour 1 de l'audit de la phase 2, il s'appelait deja
    `..._refuse_un_identifiant_qui_n_est_pas_un_siege` et son corps assertait le contraire :
    il appelait `vue_du_joueur(etat, joueur)` pour -1, 3 et 99, et verifiait que la partition
    rendue **totalisait bien toutes les cartes posees** -- c'est-a-dire qu'elle ne levait pas.
    Il documentait le defaut sous un nom qui promettait sa correction, si bien que le defaut
    mineur 2 de la phase 2 avait a la fois un releve et un test **vert** qui l'entretenait.
    Un nom qui ment est pire qu'un test absent : une recherche par nom le compte comme une
    parade.

    Le corps dit maintenant ce que le nom a toujours dit. La contrepartie -- que la vue
    rendue pour -1 n'etait celle d'aucun siege, donc que ce qu'on refuse n'etait pas
    inoffensif -- est etablie separement par
    `tests/infoset/test_vue_du_joueur.py::test_ce_que_la_parade_interdit_existait_vraiment_avant_elle`.
    """
    from courtisans.infoset import vue_du_joueur

    etat = Engine(INSTANCE).reset(0)
    with pytest.raises(ValueError, match="ne designe aucun joueur"):
        vue_du_joueur(etat, joueur)
