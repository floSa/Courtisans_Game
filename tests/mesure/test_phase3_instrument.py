"""L'instrument de la phase 3, teste AVANT d'entrainer quoi que ce soit.

Un instrument se teste comme un agent : sur ce qu'il PROMET, pas sur ce qu'il rend. Les cas
ci-dessous verifient les quatre promesses de `mesure/phase3.py`, dans l'ordre ou elles
portent le seuil :

1. **le plan est equilibre** -- chaque siege exactement une fois par donne, sur la meme
   pioche. C'est ce qui fait exister le niveau nul du seuil, et non une precaution de forme ;
2. **le niveau nul est exact en esperance**, et sa demonstration repose sur `mu_0 + mu_1 +
   mu_2 = 0` partie par partie -- verifie ici sur de vraies parties, pas suppose ;
3. **les gardes levent** plutot que de rendre un nombre qu'il faudrait relire -- plan
   desequilibre, budget vide, ecart nul ;
4. **l'effet de plan est applique** au dimensionnement, la ou une formule iid le tairait.

Aucun de ces cas ne joue plus de quelques dizaines de donnes : ils testent la **structure**
de la mesure, jamais sa valeur.
"""

from __future__ import annotations

import random

import pytest

from mesure import phase3
from mesure.instance import ENTRAINEMENT_3J

CONFIG = ENTRAINEMENT_3J


def _campagne_greedy(donnes: int = 8) -> phase3.Campagne:
    """Le greedy mis a la place de l'agent : la population de l'hypothese nulle."""
    return phase3.jouer_composition(
        agent=phase3.greedy_de_reference,
        adversaire=phase3.greedy_de_reference,
        donnes=donnes,
        intitule="1 greedy contre 2 greedys (hypothese nulle)",
    )


# ---------------------------------------------------------------------------------
# 1. Le plan
# ---------------------------------------------------------------------------------


def test_chaque_donne_donne_chaque_siege_exactement_une_fois():
    """Le desequilibre des sieges deplacerait le niveau nul de l'ordre de l'effet cherche.

    Les gains par siege du greedy valent 0,697 / 0,812 / 0,886 (phase 2, M3) : une etendue de
    0,189, quand l'effet cherche est de l'ordre du dixieme. Un plan qui verrait un siege deux
    fois et un autre zero fois ne mesurerait pas l'agent, il mesurerait le siege.
    """
    campagne = _campagne_greedy(donnes=5)
    for donne, sieges in zip(campagne.donnes, campagne.sieges_mesures, strict=True):
        assert sorted(sieges) == list(range(CONFIG.joueurs)), (
            f"donne {donne} : sieges mesures {sieges}, attendu chacun une fois"
        )


def test_les_parties_d_une_donne_partagent_la_pioche_et_rien_d_autre():
    """Meme donne => meme pioche. Sinon l'appariement ne supprime aucune variance.

    La pioche est verifiee par une **reconstruction independante** -- rejouer `reset(donne)`
    et lire la vue de dieu --, pas en demandant a la campagne de se confirmer elle-meme.
    """
    from courtisans.engine import Engine

    campagne = _campagne_greedy(donnes=4)
    moteur = Engine(CONFIG)
    for donne, groupe in zip(campagne.donnes, campagne.traces, strict=True):
        attendue = tuple(moteur.reset(donne).vue_privilegiee().pioche)
        assert all(trace.seed == donne for trace in groupe)
        for trace in groupe:
            rejoue = tuple(moteur.reset(trace.seed).vue_privilegiee().pioche)
            assert rejoue == attendue, f"donne {donne} : la pioche n'est pas la meme"


def test_les_deux_adversaires_ne_partagent_jamais_leur_aleatoire():
    """Deux copies d'une politique aleatoire sur un meme generateur joueraient correle.

    Le cas est construit sur la politique **uniforme**, ou le partage se verrait : deux
    adversaires partageant un `Random` tireraient dans la meme suite. Il compare les actions
    des deux adversaires sur les nœuds ou ils ont le meme nombre d'actions legales, et exige
    qu'elles ne soient pas systematiquement egales.
    """
    campagne = phase3.jouer_composition(
        agent=phase3.greedy_de_reference,
        adversaire=phase3.uniforme,
        donnes=6,
        intitule="1 greedy contre 2 aleatoires",
    )
    differences = 0
    comparables = 0
    for groupe, sieges in zip(campagne.traces, campagne.sieges_mesures, strict=True):
        for trace, siege_agent in zip(groupe, sieges, strict=True):
            adversaires = [s for s in range(CONFIG.joueurs) if s != siege_agent]
            par_siege: dict[int, list[int]] = {s: [] for s in adversaires}
            for decision in trace.decisions:
                if decision.joueur in par_siege:
                    par_siege[decision.joueur].append(decision.action)
            a, b = (par_siege[s] for s in adversaires)
            for action_a, action_b in zip(a, b, strict=False):
                comparables += 1
                differences += action_a != action_b
    assert comparables > 50, f"echantillon trop maigre : {comparables} couples"
    assert differences > 0, (
        "les deux adversaires ont joue exactement la meme suite d'actions sur "
        f"{comparables} couples comparables : ils partagent leur aleatoire, donc la "
        "composition mesuree n'est pas celle qui est annoncee."
    )


# ---------------------------------------------------------------------------------
# 2. Le niveau nul, et la seule chose qui soit exacte
# ---------------------------------------------------------------------------------


def test_la_somme_des_trois_sieges_vaut_zero_dans_CHAQUE_partie():
    """`mu_0 + mu_1 + mu_2 = 0` : le fondement du niveau nul, verifie et non suppose.

    C'est l'invariant I5 et le paragraphe 5.2, et c'est **ceci** qui est exact -- partie par
    partie, sur les trois sieges d'une meme partie.
    """
    campagne = _campagne_greedy(donnes=6)
    for groupe in campagne.traces:
        for trace in groupe:
            assert abs(sum(trace.gains)) < 1e-12, (
                f"la somme des gains vaut {sum(trace.gains)} et non 0 : la somme nulle du "
                f"paragraphe 5.2 est violee, et le niveau nul du seuil avec elle"
            )


def test_la_somme_sur_les_trois_parties_d_une_donne_n_est_PAS_nulle():
    """Le contre-exemple, ecrit pour que personne ne relise le module de travers.

    La docstring de `mesure/phase3.py` a affirme, dans une premiere redaction, que sommer le
    gain de l'agent sur les trois assignations de siege d'une donne revenait a sommer les
    trois sieges d'une partie. **C'est faux** : ce sont trois parties differentes, meme
    pioche mais aleas de politique distincts. Ce cas fige le contre-exemple.

    Il echouerait si les trois traces d'une donne devenaient identiques -- ce qui arriverait
    si l'alea de departage cessait de dependre du siege, et rendrait l'appariement illusoire.
    """
    campagne = _campagne_greedy(donnes=10)
    sommes = [sum(groupe) for groupe in campagne.gains_par_donne()]
    assert any(abs(somme) > 1e-9 for somme in sommes), (
        "toutes les donnes somment a zero sur leurs trois parties : les trois traces d'une "
        "donne sont devenues identiques, donc l'appariement ne recouvre plus trois parties "
        "distinctes."
    )


# ---------------------------------------------------------------------------------
# 3. Les gardes levent
# ---------------------------------------------------------------------------------


def test_un_plan_desequilibre_leve_au_lieu_de_rendre_un_nombre():
    """Le rapport intraclasse suppose des groupes egaux : sur des groupes inegaux il ment.

    C'est la meme parade que `ecart_de_taux` et `cumuler` en phase 2 -- lever plutot que
    rendre un nombre qu'il faudrait relire.
    """
    campagne = _campagne_greedy(donnes=3)
    with pytest.raises(ValueError, match="meme nombre de parties"):
        phase3.Campagne(
            intitule="plan mutile",
            donnes=campagne.donnes,
            traces=(campagne.traces[0][:2],) + campagne.traces[1:],
            sieges_mesures=(campagne.sieges_mesures[0][:2],)
            + campagne.sieges_mesures[1:],
        )


def test_les_gardes_de_budget_levent():
    """Un budget vide et un ecart nul ne rendent pas un nombre : ils levent."""
    dimension = phase3.dimensionner(_campagne_greedy(donnes=4))
    with pytest.raises(ValueError, match="au moins une partie"):
        dimension.ecart_detectable(0)
    with pytest.raises(ValueError, match="strictement positif"):
        dimension.parties_pour_ecart(0.0)
    with pytest.raises(ValueError, match="strictement positif"):
        dimension.parties_pour_ecart(-0.1)
    with pytest.raises(ValueError, match="au moins une donne"):
        phase3.jouer_composition(
            agent=phase3.greedy_de_reference,
            adversaire=phase3.greedy_de_reference,
            donnes=0,
            intitule="vide",
        )


# ---------------------------------------------------------------------------------
# 4. L'effet de plan est APPLIQUE, et pas seulement mesure
# ---------------------------------------------------------------------------------


def test_l_effet_de_plan_entre_reellement_dans_le_budget():
    """Mesurer `rho` sans l'appliquer serait le publier pour rien.

    Le cas construit deux dimensionnements identiques sauf par leur effet de plan, et exige
    que le budget suive. Un effet de 2 doit doubler le nombre de parties : c'est
    l'arithmetique de `n_effectif = n / effet`, et elle se verifie sans mesurer.
    """
    reference = phase3.dimensionner(_campagne_greedy(donnes=4))
    sans = phase3.Dimensionnement(
        intitule="effet neutre",
        nb_donnes=reference.nb_donnes,
        nb_parties=reference.nb_parties,
        replicats=reference.replicats,
        sigma_gain=0.6652,
        rho=0.0,
        effet_de_plan=1.0,
        gain=reference.gain,
    )
    double = phase3.Dimensionnement(
        intitule="effet double",
        nb_donnes=reference.nb_donnes,
        nb_parties=reference.nb_parties,
        replicats=reference.replicats,
        sigma_gain=0.6652,
        rho=0.5,
        effet_de_plan=2.0,
        gain=reference.gain,
    )
    assert double.parties_pour_ecart(0.10) == 2 * sans.parties_pour_ecart(0.10)
    # Un effet de 2 divise le `n` effectif par 2, donc multiplie l'ecart detectable par
    # racine de 2. Tolerance a 1e-9 : c'est une identite, pas une mesure.
    assert double.ecart_detectable(1000) == pytest.approx(
        sans.ecart_detectable(1000) * 2**0.5, rel=1e-9
    )


def test_ma_formule_n_est_PAS_celle_de_la_phase_2_et_le_rapport_vaut_racine_de_deux():
    """Les deux formules ne dimensionnent pas le meme estimand, et il faut l'ecrire.

    **La phase 2 dimensionne un contraste apparie entre DEUX agents** :
    `Var(X_A - X_B) = 2 sigma^2 (1 - rho)`, d'ou `z sigma sqrt(2(1-rho)) / sqrt(n)`. C'est de
    la que vient son `+0,1013` a 1 000 parties.

    **La phase 3 dimensionne la moyenne d'UN echantillon contre un niveau nul exact** :
    l'agent contre deux greedys, juge par `gain moyen > 0`. Il n'y a pas de second agent a
    soustraire -- c'est le plan a sieges permutes qui fournit le zero, en esperance. La
    variance de la moyenne vaut `sigma^2 (1 + (m-1) rho) / N`.

    Deux consequences, et **la seconde est contre-intuitive** :

    1. a `rho = 0`, mon ecart detectable vaut celui de la phase 2 **divise par exactement
       `sqrt(2)`** -- le facteur 2 de la variance d'une difference. Emprunter le `+0,1013`
       aurait donc surestime mon budget d'un facteur 2 en parties ;
    2. **`rho` joue en sens INVERSE dans les deux formules.** Chez la phase 2, la correlation
       est entre les deux termes qu'on **soustrait** : elle aide, et un `rho` eleve reduit le
       budget. Chez moi, elle est entre les replicats qu'on **moyenne** : elle nuit, et un
       `rho` eleve augmente le budget. Lire « rho = 0,0066, donc l'appariement ne rapporte
       rien » et en conclure que `rho` est sans consequence pour la phase 3 serait faux dans
       le sens le plus couteux -- un `rho` fort me couterait des parties la ou il en
       economisait a la phase 2.

    Ce cas verifie les deux, et il verifie d'abord que ma reimplementation de **leur** formule
    rend **leur** chiffre : sans ca, le rapport de `sqrt(2)` ne dirait rien.
    """
    from mesure import phase2

    sigma, n = 0.6652, 1000
    reference = phase3.dimensionner(_campagne_greedy(donnes=4))

    def mien(rho: float, replicats: int = 3) -> float:
        return dataclasses_replace(reference, sigma, rho, replicats).ecart_detectable(n)

    # 0. Leur formule rend leur chiffre. Le controle qui rend les suivants lisibles.
    assert phase2.ecart_detectable(sigma, 0.0066, n) == pytest.approx(0.1013, abs=5e-5)

    # 1. A rho nul, le rapport vaut exactement racine de deux.
    assert phase2.ecart_detectable(sigma, 0.0, n) / mien(0.0) == pytest.approx(
        2**0.5, rel=1e-9
    ), "le facteur 2 de la variance d'une difference a disparu de l'une des deux formules"

    # 2. Les deux formules bougent en sens INVERSE avec rho.
    rhos = (0.0, 0.2, 0.5, 0.8)
    leurs = [phase2.ecart_detectable(sigma, r, n) for r in rhos]
    miens = [mien(r) for r in rhos]
    assert leurs == sorted(leurs, reverse=True), (
        f"chez la phase 2, rho croissant doit REDUIRE l'ecart detectable : {leurs}"
    )
    assert miens == sorted(miens), (
        f"chez la phase 3, rho croissant doit AUGMENTER l'ecart detectable : {miens}"
    )

    # 3. En parties, l'ecart de budget est un facteur 2 -- ce que l'emprunt aurait coute.
    budget_mien = phase3.Dimensionnement(
        intitule="a rho nul",
        nb_donnes=reference.nb_donnes,
        nb_parties=reference.nb_parties,
        replicats=3,
        sigma_gain=sigma,
        rho=0.0,
        effet_de_plan=1.0,
        gain=reference.gain,
    ).parties_pour_ecart(0.10)
    budget_phase2 = 1027  # tableau de dimensionnement de la phase 2, ligne +0.10, apparie
    assert budget_phase2 / budget_mien == pytest.approx(2.0, rel=0.02), (
        f"mon budget {budget_mien} parties contre {budget_phase2} pour la phase 2 : le "
        f"rapport devrait valoir 2, il vaut {budget_phase2 / budget_mien:.3f}"
    )


def dataclasses_replace(
    reference: phase3.Dimensionnement, sigma: float, rho: float, replicats: int
) -> phase3.Dimensionnement:
    """Un dimensionnement de meme forme, avec sigma, rho et m imposes."""
    import dataclasses

    return dataclasses.replace(
        reference,
        sigma_gain=sigma,
        rho=rho,
        replicats=replicats,
        effet_de_plan=1.0 + (replicats - 1) * rho,
    )


def test_le_controle_de_collision_de_tenseurs_compte_de_vrais_noeuds():
    """Le controle du reseau partage : il doit voir des nœuds, sinon il ne dit rien.

    Un controle qui balaie zero nœud rendrait « 0 collision » et se lirait comme une preuve.
    Ce cas exige un echantillon non vide et coherent -- autant de tenseurs distincts que de
    nœuds, aux collisions pres.
    """
    campagne = _campagne_greedy(donnes=3)
    noeuds, tenseurs, collisions = phase3.collision_de_tenseurs(campagne)
    assert noeuds > 100, f"echantillon trop maigre : {noeuds} nœuds"
    assert tenseurs <= noeuds
    assert collisions >= 0
    assert collisions == 0 or collisions <= noeuds


def test_le_juge_lit_le_seuil_du_protocole_et_pas_un_autre():
    """`bat_le_greedy` est la borne basse **strictement** positive, et le neutre est 1/3.

    Le cas fabrique deux verdicts, l'un dont la borne basse vaut exactement 0. Un seuil
    « >= 0 » le declarerait vainqueur ; le protocole dit « strictement positif ».
    """
    reference = phase3.juger(_campagne_greedy(donnes=3))
    assert reference.part_neutre == pytest.approx(1 / 3)

    import dataclasses

    a_zero = dataclasses.replace(
        reference,
        gain=dataclasses.replace(reference.gain, intervalle=(0.0, 0.5)),
    )
    positif = dataclasses.replace(
        reference,
        gain=dataclasses.replace(reference.gain, intervalle=(1e-9, 0.5)),
    )
    negatif = dataclasses.replace(
        reference,
        gain=dataclasses.replace(reference.gain, intervalle=(-0.1, 0.5)),
    )
    assert not a_zero.bat_le_greedy, "une borne basse a 0 exactement ne bat pas le greedy"
    assert positif.bat_le_greedy
    assert not negatif.bat_le_greedy


def test_la_campagne_porte_sa_composition_en_toutes_lettres():
    """Un resultat qui ne nomme pas sa composition n'est pas auditable."""
    campagne = _campagne_greedy(donnes=2)
    assert "greedy" in campagne.intitule.lower()
    assert phase3.juger(campagne).intitule == campagne.intitule
    assert phase3.dimensionner(campagne).intitule == campagne.intitule


def test_les_decalages_de_graine_sont_disjoints_de_ceux_de_la_phase_2():
    """Aucune partie de la phase 3 ne doit etre une partie de la phase 2 sous un autre nom."""
    from mesure import phase2

    miens = {
        phase3.DECALAGE_DEPARTAGE,
        phase3.DECALAGE_UNIFORME,
        phase3.DECALAGE_AGENT,
        phase3.GRAINE_BOOTSTRAP,
    }
    siens = {
        valeur
        for nom, valeur in vars(phase2).items()
        if nom.startswith(("DECALAGE_", "DEPART_", "GRAINE_")) and isinstance(valeur, int)
    }
    assert not (miens & siens), f"graines partagees avec la phase 2 : {sorted(miens & siens)}"
    assert phase3.DEPART_DONNE >= 20_000, (
        "les donnes de la phase 3 doivent etre disjointes des seeds 0-3333 et 10000-11666 "
        "de la phase 2 : dimensionner sur les donnes qui ont produit la ligne de base "
        "reutiliserait l'echantillon deux fois."
    )
    alea = random.Random(0)  # noqa: F841 -- ce cas ne tire rien, il compare des constantes
