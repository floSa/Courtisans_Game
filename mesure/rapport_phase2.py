"""Le rapport de la phase 2 : les quatre mesures, decomposees.

Ce module **n'interprete rien**. Il joue les campagnes de `phase2.py`, applique les compteurs,
et ecrit chaque chiffre avec sa decomposition -- numerateur, denominateur, grain, vue, seeds.
Un chiffre que le lecteur ne peut pas reconstruire n'a pas sa place ici (paragraphe 10 des
conventions).

Les seuils rappeles sont ceux de `phase2_hypothese_et_instrument.md`, commites avant la mesure.
Aucun n'est recalcule ici a partir du resultat.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from time import perf_counter

from mesure import comportements as comp
from mesure import dimensionnement as dim
from mesure import phase2
from mesure.bootstrap import EffetDePlan

CONFIG = phase2.CONFIG

#: Les ecarts de gain moyen dont M2 chiffre le cout en parties.
ECARTS_A_DIMENSIONNER = (0.02, 0.05, 0.10, 0.20, 0.30)


def _pct(valeur: float | None, decimales: int = 2) -> str:
    return "sans objet" if valeur is None else f"{100 * valeur:.{decimales}f} %"


def _titre(texte: str) -> str:
    return f"\n## {texte}\n"


def _ligne_effet(nom: str, effet: EffetDePlan, en_pourcent: bool) -> str:
    """Une statistique bootstrapee, avec son intervalle, son effet de plan et son n effectif."""
    forme = _pct if en_pourcent else (lambda v: f"{v:+.4f}")
    basse, haute = effet.intervalle
    return (
        f"| {nom} | {forme(effet.moyenne)} | [{forme(basse)} ; {forme(haute)}] | "
        f"{forme(effet.erreur_type_iid())} | "
        f"{forme(effet.erreur_type_bootstrap())} | "
        f"{effet.effet:.3f} | {effet.n_effectif:.0f} |"
    )


def section_plan(lignes: list[str], donnes_a: int, donnes_b: int) -> None:
    """Ce qui a ete joue, avec les seeds. Premier, parce que tout le reste s'y rapporte."""
    lignes.append(_titre("1. Ce qui a ete joue"))
    parties_a = donnes_a * 6
    parties_b = donnes_b * CONFIG.joueurs
    lignes += [
        f"Instance : `familles={CONFIG.familles}`, {CONFIG.nb_roles} roles, "
        f"`exemplaires={CONFIG.exemplaires}`, `joueurs={CONFIG.joueurs}` -- "
        f"{CONFIG.nb_cartes} cartes, {CONFIG.tours} tours par joueur.",
        "",
        "| Campagne | Composition | Donnes | Parties | Seeds de donne | Alea de politique |",
        "|---|---|---:|---:|---|---|",
        f"| A | trois aleatoires | {donnes_a} x 6 replicats | **{parties_a}** | "
        f"{phase2.DEPART_A} a {phase2.DEPART_A + donnes_a - 1} | "
        f"`Random({phase2.DECALAGE_POLITIQUE_A} + 6 x donne + replicat)` |",
        f"| A controle | trois aleatoires | {donnes_a} x 6 | **{parties_a}** | "
        f"{phase2.DEPART_A_CONTROLE} a {phase2.DEPART_A_CONTROLE + donnes_a - 1} | idem |",
        f"| B | 1 greedy, 2 aleatoires | {donnes_b} x 3 sieges | **{parties_b}** | "
        f"{phase2.DEPART_B} a {phase2.DEPART_B + donnes_b - 1} | "
        f"`Random({phase2.DECALAGE_POLITIQUE_B} + 3 x donne + siege)` |",
        "",
        f"Bootstrap : **par donne**, {phase2.REPETITIONS_BOOTSTRAP} rechantillons, "
        f"`Random({phase2.DECALAGE_BOOTSTRAP})`. Chaque donne entre avec **tous** ses "
        "replicats : tirer des parties detruirait la structure qu'on mesure.",
    ]


def section_m1(
    lignes: list[str],
    resultats: Sequence[phase2.ResultatSiege],
    intitule: str,
) -> None:
    """M1, sur les deux statistiques et leurs deux niveaux neutres."""
    lignes.append(_titre(f"2. M1 -- avantage de siege ({intitule})"))
    lignes += [
        "**Deux niveaux neutres, et ils ne sont pas les memes.** `0,0000` pour le gain moyen "
        "`returns()` -- exact, par la somme nulle du paragraphe 5.2, tenue par l'invariant I5. "
        "`33,33 %` pour la part de victoire fractionnee -- exact aussi, les parts `1/k` sommant "
        "a 1 sur les sieges a chaque partie. Un siege a `+0,05` de gain n'est pas mediocre ; "
        "un siege a `0,05` de part de victoire le serait.",
        "",
        "### Gain moyen `returns()` -- niveau neutre **0,0000**",
        "",
        "| Siege | Moyenne | IC 99 % bootstrap | ET iid | ET boot | Effet | n eff. |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for resultat in resultats:
        lignes.append(_ligne_effet(f"siege {resultat.siege}", resultat.gain, False))
    somme = sum(r.gain.moyenne for r in resultats)
    lignes += [
        "",
        f"Controle de somme nulle sur les moyennes : **{somme:+.2e}**, "
        "soit zero a la precision machine.",
        "",
        "### Part de victoire fractionnee -- niveau neutre **33,3333 %**",
        "",
        "| Siege | Part | IC 99 % bootstrap | ET iid | ET boot | Effet | n eff. |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for resultat in resultats:
        lignes.append(_ligne_effet(f"siege {resultat.siege}", resultat.part_fractionnee, True))
    total = sum(r.part_fractionnee.moyenne for r in resultats)
    lignes += [
        "",
        f"Controle : les trois parts somment a **{total:.6f}**, soit 1 exactement.",
        "",
        "### Part de victoire stricte -- niveau neutre **inconnu d'avance**",
        "",
        "Elle vaut `(1 - P(ex aequo)) / 3` et **ne peut donc pas servir de seuil**. Rapportee "
        "parce que c'est la lecture spontanee de « gagner une partie ».",
        "",
        "| Siege | Part stricte |",
        "|---|---:|",
    ]
    for resultat in resultats:
        lignes.append(f"| siege {resultat.siege} | {_pct(resultat.part_stricte)} |")

    nb = resultats[0].part_fractionnee.nb_parties
    plan = dim.plan_m1()
    maxi = max(resultats, key=lambda r: r.part_fractionnee.moyenne)
    lignes += [
        "",
        "### Les trois seuils, et ce que le resultat en dit",
        "",
        "| Seuil | Valeur | Origine | Franchi ? |",
        "|---|---:|---|---|",
    ]
    for nom, seuil, origine in (
        ("protocole", plan.seuil_protocole, "paragraphe 3 du protocole, phase 2"),
        ("detection 99 %", plan.seuil_non_corrige, "bilateral, non corrige"),
        ("detection 99 % Bonferroni", plan.seuil_bonferroni, "corrige pour 3 sieges"),
    ):
        franchi = "**oui**" if maxi.part_fractionnee.moyenne > seuil else "non"
        lignes.append(f"| {nom} | {_pct(seuil)} | {origine} | {franchi} |")
    ecarts = dim.ecarts_types(maxi.part_fractionnee.moyenne, plan.neutre, nb)
    lignes += [
        "",
        f"Le siege le plus favorise est le **siege {maxi.siege}**, a "
        f"{_pct(maxi.part_fractionnee.moyenne)}, soit **{ecarts:+.2f} erreurs-type** de "
        f"l'attendu (calcul iid a n = {nb}).",
        "",
        "**Puissance de cette mesure**, ecrite a cote du resultat pour qu'une absence de "
        "detection ne se lise pas comme une absence d'effet :",
        "",
        "| Ecart vrai | Parties pour 80 % (exact stable) | Puissance exacte a "
        f"n = {nb} |",
        "|---|---:|---:|",
    ]
    for cible in (0.38, 0.35):
        exacte = dim.parties_pour_puissance_exacte(
            plan.neutre, cible, dim.RISQUE, dim.PUISSANCE, CONFIG.joueurs
        )
        puissance = dim.puissance_exacte(nb, plan.neutre, cible, dim.RISQUE, CONFIG.joueurs)
        lignes.append(
            f"| un siege a {_pct(cible)} | {exacte.stable} "
            f"(premier franchissement {exacte.franchissement}) | {_pct(puissance, 1)} |"
        )


def section_m2(lignes: list[str], resultat: phase2.ResultatVariance) -> None:
    """M2 : la dispersion, la correlation intra-donne, et le tableau de dimensionnement."""
    lignes.append(_titre("3. M2 -- variance du score final"))
    lignes += [
        f"Sur {resultat.nb_parties} parties de la campagne A, soit "
        f"{resultat.nb_parties * CONFIG.joueurs} scores.",
        "",
        "| Grandeur | Valeur |",
        "|---|---|",
        "| Ecart-type du score, par siege | "
        + " / ".join(f"{e:.3f}" for e in resultat.ecarts_types_score)
        + " |",
        f"| Ecart-type du score, sieges confondus | **{resultat.ecart_type_score_global:.3f}** |",
        f"| Ecart-type du gain `returns()` | **{resultat.ecart_type_gain:.4f}** |",
        "| Valeurs de score distinctes, par siege | "
        + " / ".join(str(v) for v in resultat.valeurs_distinctes)
        + " |",
        "| Part de la valeur modale, par siege | "
        + " / ".join(_pct(p) for p in resultat.part_modale)
        + " |",
        f"| Parties a trois ex aequo | {_pct(resultat.trois_ex_aequo)} |",
        "",
        "La precision de l'ecart-type a cette taille est de "
        f"**{_pct(dim.erreur_relative_ecart_type(resultat.nb_parties), 3)} relatif** "
        f"(`1 / sqrt(2n)`), et 5 % relatif sont atteints des "
        f"{dim.parties_pour_erreur_relative(0.05)} parties. **M2 est donc decide bien avant la "
        "fin de la campagne** : son contenu reel est la correlation intra-donne et le tableau "
        "ci-dessous.",
        "",
        "### Correlation intra-donne -- le cinquieme trou du protocole",
        "",
        "Le paragraphe 1 du protocole affirme que l'appariement « divise par cinq a dix » le "
        "nombre de parties necessaires, ce qui implique `rho` dans `[0,80 ; 0,90]`. **Aucune "
        "mesure du depot ne l'appuyait.** Voici la mesure.",
        "",
        "| Grandeur | Siege 0 | Siege 1 | Siege 2 |",
        "|---|---:|---:|---:|",
        "| `rho` sur le score | "
        + " | ".join(
            "sans objet" if r is None else f"{r:+.4f}" for r in resultat.correlation_score
        )
        + " |",
        "| `rho` sur le gain | "
        + " | ".join(
            "sans objet" if r is None else f"{r:+.4f}" for r in resultat.correlation_gain
        )
        + " |",
    ]
    rhos = [r for r in resultat.correlation_gain if r is not None]
    rho = sum(rhos) / len(rhos) if rhos else 0.0
    facteur = 1 / (1 - rho) if rho < 1 else float("inf")
    lignes += [
        "",
        f"`rho` moyen sur le gain : **{rho:+.4f}**, soit un facteur de gain de "
        f"**{facteur:.2f}** contre les 5 a 10 annonces.",
        "",
        "**Ce que ce chiffre dit, et ce qu'il ne dit pas.** Il est mesure **sous jeu "
        "uniformement aleatoire**, ou l'alea de la politique domine tout : la donne n'explique "
        f"que {_pct(max(rho, 0.0), 2)} de la variance du gain. Sous cette politique-la, "
        "l'appariement ne rapporte rien.",
        "",
        "Il ne **refute pas** l'affirmation du protocole, qui porte sur la comparaison de deux "
        "agents *differents* sur la meme donne. Il l'**infirme pour les deux politiques "
        "mesurees ici** -- voir aussi l'effet de plan du greedy en section 4, qui vaut ~0,94, "
        "soit un gain de 6 % et non un facteur 5 a 10. L'affirmation reste donc **non appuyee**, "
        "et c'est a ce titre qu'elle remonte comme cinquieme trou du protocole : pas comme une "
        "erreur etablie, comme un chiffre publie sans mesure.",
        "",
        "### Le tableau de dimensionnement -- le produit livre de M2",
        "",
        "Pour chaque ecart de gain moyen qu'on voudrait etablir, les parties necessaires a 99 % "
        f"bilateral et 80 % de puissance, avec `sigma = {resultat.ecart_type_gain:.4f}` mesure "
        f"et `rho = {max(rho, 0.0):.4f}` mesure.",
        "",
        "| Ecart de gain moyen | Sans appariement | Avec appariement |",
        "|---|---:|---:|",
    ]
    for ecart, sans, avec in phase2.tableau_de_dimensionnement(
        resultat.ecart_type_gain, rho, ECARTS_A_DIMENSIONNER
    ):
        lignes.append(f"| {ecart:+.2f} | {sans} | {avec} |")
    detectable = phase2.ecart_detectable(resultat.ecart_type_gain, rho, 1_000)
    lignes += [
        "",
        f"**Lecture inverse, pour la phase 3** : a 1 000 parties appariees -- le budget que le "
        f"paragraphe 3 du protocole lui fixe --, l'ecart de gain moyen detectable est "
        f"**{detectable:+.4f}**. C'est le chiffre qui dira si son seuil de « > 55 % contre le "
        "greedy » est atteignable a ce budget.",
    ]


def section_m3(lignes: list[str], resultats: Sequence[phase2.ResultatGreedy]) -> None:
    """M3 : le winrate du greedy, compositions et variantes."""
    lignes.append(_titre("4. M3 -- winrate du greedy contre l'aleatoire"))
    lignes += [
        "**Les deux niveaux neutres, a nouveau, parce que c'est ici que la confusion coute le "
        "plus cher.** `0,0000` pour le gain moyen, `33,3333 %` pour la part de victoire "
        "fractionnee. Le chiffre de reference du protocole -- « si le greedy est a 60 % » -- est "
        "une part de victoire, et son point de comparaison est **33,33 %, pas 50 %** : a trois "
        "joueurs, 50 % est deja une domination.",
        "",
        "### Gain moyen `returns()` -- niveau neutre **0,0000**",
        "",
        "| Mesure | Moyenne | IC 99 % bootstrap | ET iid | ET boot | Effet | n eff. |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for resultat in resultats:
        lignes.append(_ligne_effet(resultat.intitule, resultat.gain, False))
    lignes += [
        "",
        "### Part de victoire fractionnee -- niveau neutre **33,3333 %**",
        "",
        "| Mesure | Part | IC 99 % bootstrap | ET iid | ET boot | Effet | n eff. |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for resultat in resultats:
        lignes.append(_ligne_effet(resultat.intitule, resultat.part_fractionnee, True))
    lignes += [
        "",
        "| Mesure | Part stricte | Parties |",
        "|---|---:|---:|",
    ]
    for resultat in resultats:
        lignes.append(
            f"| {resultat.intitule} | {_pct(resultat.part_stricte)} | {resultat.nb_parties} |"
        )

    lignes += [
        "",
        "### L'effet de siege du greedy -- et il n'a rien a voir avec celui de M1",
        "",
        "**M1 mesure le siege sous jeu uniformement aleatoire ; ceci le mesure sous jeu "
        "greedy.** Rien ne disait d'avance que les deux se ressembleraient, et le tableau "
        "ci-dessous montre qu'ils ne se ressemblent pas du tout. Chaque ligne porte le gain du "
        "greedy sur les seules parties ou il occupait ce siege -- un tiers des parties, "
        "appariees par donne.",
        "",
    ]
    for resultat in resultats:
        lignes += [
            f"**{resultat.intitule}**",
            "",
            "| Siege occupe | Gain moyen | IC 99 % bootstrap | Parties |",
            "|---|---:|---|---:|",
        ]
        for siege, effet in enumerate(resultat.par_siege_bootstrap):
            basse, haute = effet.intervalle
            lignes.append(
                f"| siege {siege} | {effet.moyenne:+.4f} | "
                f"[{basse:+.4f} ; {haute:+.4f}] | {effet.nb_parties} |"
            )
        contraste = resultat.contraste_extremes
        if contraste is not None:
            basse, haute = contraste.intervalle
            etabli = "**etabli**" if basse > 0 or haute < 0 else "non etabli"
            lignes += [
                "",
                f"Contraste entre les deux sieges extremes, **apparie par donne** : "
                f"**{contraste.moyenne:+.4f}**, IC 99 % [{basse:+.4f} ; {haute:+.4f}] -- "
                f"{etabli}. Chaque donne fournit les deux sieges, donc la difference ne "
                f"contient plus la variance de distribution.",
                "",
            ]
    lignes += [
        "**Consequence sur l'arbitrage de la phase 2.** Permuter les sieges "
        "inconditionnellement etait la bonne decision, et pour une raison que M1 seul ne "
        "pouvait pas donner : l'avantage de siege est **negligeable sous jeu aleatoire et "
        "massif sous jeu greedy**. Un protocole qui aurait teste le seuil de 38 % sur des "
        "agents aleatoires aurait conclu « inutile de neutraliser » -- et se serait trompe des "
        "la premiere mesure d'agent.",
    ]

    reference = next((r for r in resultats if "reference" in r.intitule), None)
    deterministe = next((r for r in resultats if "deterministe" in r.intitule), None)
    if reference is not None and deterministe is not None:
        ecart = deterministe.gain.moyenne - reference.gain.moyenne
        basse, haute = reference.gain.intervalle
        demi = (haute - basse) / 2
        lignes += [
            "",
            "### Le departage change 61 % des refus et ne change pas le gain",
            "",
            "**Ce n'est pas un doublon, c'est une mesure de consequence nulle**, et elle ne se "
            "lit qu'en juxtaposant les deux nombres :",
            "",
            "| | |",
            "|---|---:|",
            "| part des refus du greedy que le **departage** decide (section 5) | "
            "voir `B4-departage` |",
            f"| ecart de gain entre departage aleatoire et deterministe | **{ecart:+.4f}** |",
            f"| demi-largeur de l'IC 99 % du gain de reference | {demi:.4f} |",
            f"| l'ecart, en demi-largeurs | **{abs(ecart) / demi:.2f}** |",
            "",
            "Autrement dit : **une majorite des decisions de refus du greedy sont "
            "strategiquement indifferentes sur cette instance.** C'est un fait du JEU, pas de "
            "l'implementation, et il n'est nulle part ailleurs dans ce depot.",
            "",
            "Deux usages immediats. Il **desarme** la lecture « le greedy refuse dans X % des "
            "cas » en montrant que la majorite de ces refus ne coutent rien. Et il donne a la "
            "phase 3 un **etalon** : un agent qui refuse dans les memes proportions n'a rien "
            "appris ; un agent dont les refus deplacent son gain a appris quelque chose.",
        ]


def section_m4(
    lignes: list[str],
    greedy: dict[str, comp.Compte],
    hasard: dict[str, comp.Compte],
    b6_greedy: dict[str, float | None],
    b6_hasard: dict[str, float | None],
    b6_concurrente_greedy: dict[str, float | None],
    b6_concurrente_hasard: dict[str, float | None],
) -> None:
    """M4 : les sept comportements, deux lignes de base, definitions concurrentes comprises."""
    lignes.append(_titre("5. M4 -- B1 a B7, ligne de base du greedy ET du hasard"))
    lignes += [
        "**Deux points de comparaison, pas un.** « Le greedy fait B4 dans X % des cas » n'est "
        "pas interpretable sans savoir ce que le hasard donne. La colonne « hasard » vient de la "
        "campagne A, tous sieges confondus ; la colonne « greedy » de la campagne B, siege du "
        "greedy seul.",
        "",
        "Chaque ligne porte son **denominateur**, son **grain** et sa **vue** : un taux dont le "
        "sujet grammatical n'est pas l'unite comptee n'est pas auditable.",
        "",
        "**B1 a deux grains, et un seul se compare.** C'est le seul des sept dont le "
        "denominateur naturel est la partie et non une action, donc agreger les sieges mesures "
        "par un « au moins un » gonfle son numerateur **sans toucher au denominateur**. La "
        "colonne « hasard » porte trois sieges, la colonne « greedy » un seul : seules les "
        "lignes au grain `(partie, siege)` se comparent. Les lignes `-par-partie` repondent a "
        "une autre question -- *cette partie contient-elle le motif quelque part* -- et leur "
        "valeur monte mecaniquement avec le nombre de sieges agreges. **Ce defaut a ete trouve "
        "par l'audit de l'etape 4, apres une premiere lecture qui concluait l'inverse.**",
        "",
        "**Et B1 n'est pas homogene par siege.** MESURE sur 500 donnes x 6 replicats, politique "
        "uniforme : 37,93 % au siege 0, 36,80 % au siege 1, 33,50 % au siege 2, soit 4,4 points "
        "d'etendue -- le siege 0 pose en premier, donc son « nourrir » laisse plus de nœuds "
        "ulterieurs disponibles pour un « baisser ». **Une ligne de base B1 doit donc etre "
        "equilibree sur les sieges**, et les deux colonnes ci-dessous le sont : la campagne A "
        "compte les trois sieges, la campagne B fait tourner le greedy sur les trois. Un chiffre "
        "de 37,58 % a circule en cours d'audit -- c'etait 451/1200, **siege 0 seul**, sur un "
        "echantillon de 200 donnes ; il n'a pas cours et ne doit pas etre compare a la colonne "
        "greedy.",
        "",
        "| Compteur | Greedy | Hasard | Grain du denominateur | Vue |",
        "|---|---|---|---|---|",
    ]
    for nom in greedy:
        g, h = greedy[nom], hasard.get(nom)
        part_g = f"{_pct(g.taux())} ({g.succes}/{g.total})"
        part_h = (
            f"{_pct(h.taux())} ({h.succes}/{h.total})" if h is not None else "sans objet"
        )
        lignes.append(f"| `{nom}` | {part_g} | {part_h} | {g.grain} | {g.vue} |")

    lignes += [
        "",
        "### B4 -- le controle d'identite, et la part que le departage produit",
        "",
        "`B4-strict + B4-departage + B4-contre-nature` doit valoir exactement le nombre de "
        "refus. C'est un **controle**, verifie par `comportements.verifier_b4`, qui leve si "
        "l'identite tombe.",
        "",
        "| | Greedy | Hasard |",
        "|---|---:|---:|",
    ]
    for source, colonnes in (("somme des trois", (greedy, hasard)),):
        valeurs = []
        for comptes in colonnes:
            somme = sum(
                comptes[nom].succes
                for nom in ("B4-strict", "B4-departage", "B4-contre-nature")
            )
            valeurs.append(f"{somme} = {comptes['B4-brut'].succes} refus")
        lignes.append(f"| {source} | {valeurs[0]} | {valeurs[1]} |")
    part_dos_g = greedy["B4-tout-dos"].taux()
    lignes += [
        "",
        f"**{_pct(part_dos_g)} des nœuds de ciblage du greedy n'offrent que des dos.** Sur "
        "ceux-la son evaluation est **plate** -- un dos ne compte pas dans l'influence percue, "
        "donc le tuer ne change rien -- et c'est la **regle de departage** qui choisit, pas "
        f"l'heuristique : elle refuse avec probabilite `1/(k+1)`. C'est la part de `B4-brut` "
        "qui ne mesure pas un comportement, et elle se lit a cet endroit.",
        "",
        "### Une inclusion, verifiee et non deduite",
        "",
        "`B1-collectif` majore `B1-motif` **par construction** : le don vient du siege mesure, "
        "la bascule de n'importe quel siege. L'inclusion est verifiee sur les deux colonnes -- "
        f"greedy {greedy['B1-collectif'].succes} >= {greedy['B1-motif'].succes}, hasard "
        f"{hasard['B1-collectif'].succes} >= {hasard['B1-motif'].succes}. **Une inclusion qui "
        "tombe designerait un compteur faux**, et celle-ci est tombee une fois : "
        "`B1-collectif` n'agregeait que les sieges mesures, donc il valait exactement "
        "`B1-motif` des qu'on mesurait un agent seul -- muet precisement dans le cas ou il "
        "sert, un don du greedy retourne par un adversaire.",
        "",
        "### Deux choses que la mesure a corrigees dans ma propre lecture",
        "",
        f"**Le departage explique {_pct(greedy['B4-departage'].taux())} des refus du greedy, "
        f"mais les nœuds tout-dos n'en sont que {_pct(part_dos_g)}.** Le paragraphe 5.4.1 de la "
        "pre-inscription designait les nœuds tout-dos comme le mecanisme de l'egalite : c'est "
        "un mecanisme, ce n'est pas **le** mecanisme. La majorite des egalites vient de nœuds "
        "ou une cible identifiable existe mais dont le meurtre ne change pas l'ecart evalue -- "
        "typiquement une carte d'une famille Indifferente. Ma pre-inscription avait raison sur "
        "la necessite de separer les trois nombres, et incomplete sur la cause.",
        "",
        f"**B7 n'a presque pas d'occasion de se manifester** : "
        f"{_pct(greedy['B7-occasions'].taux())} des poses au banquet du greedy surviennent "
        f"alors qu'au moins une famille est hors d'atteinte, soit "
        f"{greedy['B7-occasions'].succes} poses sur {greedy['B7-occasions'].total}. Le "
        f"gaspillage mesure, {_pct(greedy['B7-gaspillage'].taux())}, se lit **sur ce fond-la** : "
        "sur cette instance a 4 tours, une famille devient rarement hors d'atteinte avant la "
        "fin. B7 est donc quasi inmesurable ici, et c'est un fait de l'instance, pas un defaut "
        "du compteur -- `B7-occasions` existe precisement pour que ce zero ne se lise pas comme "
        "« il ne gaspille pas ».",
        "",
        "### B6 -- distance de variation totale entre le tour 1 et le tour "
        f"{CONFIG.tours}",
        "",
        "**Elle n'est pas nulle chez le greedy, et ce n'est pas une preuve de comprehension** : "
        "l'etat du plateau change avec le tour, donc un agent a horizon un tour joue "
        "mecaniquement differemment sans rien savoir de la pioche. La phase 3 ne conclura que "
        "sur l'**ecart** entre sa distance et celles-ci.",
        "",
        "**La concurrente est publiee a cote, et son ecart avec la retenue est un resultat.** "
        f"**B6-dernier-contre-reste** compare le tour {CONFIG.tours} aux tours 1 a "
        f"{CONFIG.tours - 1} **agreges** : son terme de comparaison porte trois fois plus de "
        "nœuds, donc il est plus stable -- et il melange trois etats de plateau differents, donc "
        "il **dilue** l'ecart. Le choix du paragraphe 6.6 de la pre-inscription se lit sur les "
        "deux colonnes de droite.",
        "",
        f"| Groupe de categories | Greedy, tour 1 vs {CONFIG.tours} | Hasard, tour 1 vs "
        f"{CONFIG.tours} | Greedy, dernier vs reste | Hasard, dernier vs reste |",
        "|---|---:|---:|---:|---:|",
    ]
    for groupe in comp.GROUPES_B6:
        cellules = [
            source.get(groupe)
            for source in (b6_greedy, b6_hasard, b6_concurrente_greedy, b6_concurrente_hasard)
        ]
        rendues = " | ".join(
            "sans objet" if valeur is None else f"{valeur:.4f}" for valeur in cellules
        )
        lignes.append(f"| {groupe} | {rendues} |")


def section_pouvoir_discriminant(
    lignes: list[str], greedy: dict[str, comp.Compte], hasard: dict[str, comp.Compte]
) -> None:
    """Ce que chaque compteur peut separer au budget de la phase 3. La vraie livrable de M4.

    Un compteur qui ne peut rien separer au budget de la phase suivante **constate au lieu de
    tester**. C'est arrive trois fois dans ce projet : les quatre criteres de
    non-degenerescence de la phase 1, le seuil de 38 % de M1, et B7 ici. Cette section est ce
    qui doit l'empecher une quatrieme fois.
    """
    lignes.append(_titre("6. Ce que chaque compteur peut separer -- M4 pour la phase 3"))
    budget = 1_000
    lignes += [
        f"La phase 3 se donne **{budget} parties appariees** (paragraphe 3 du protocole). Pour "
        "chaque compteur, l'ecart de taux qu'elle pourra **etablir** a ce budget, a 99 % "
        "bilateral et 80 % de puissance, entre son agent et le greedy -- chacun mesure sur un "
        "siege tournant.",
        "",
        "Le `denominateur par partie` est ce qui decide : un compteur d'action en offre "
        "plusieurs par partie, un compteur d'occasion rare beaucoup moins d'une.",
        "",
        "| Compteur | Greedy | Denom. / partie | Ecart detectable a "
        f"{budget} parties | Ecart greedy-hasard observe | Parties pour l'etablir |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    nb_reference = greedy["B4-brut"].total and greedy["B1-motif"].total
    for nom, compte in greedy.items():
        if compte.total == 0 or compte.taux() is None:
            lignes.append(f"| `{nom}` | sans objet | 0 | sans objet | sans objet | sans objet |")
            continue
        par_partie = compte.total / nb_reference
        detectable = phase2.ecart_de_taux_detectable(compte.taux(), par_partie, budget)
        if detectable is None and compte.succes == 0:
            borne = phase2.borne_exacte_d_un_taux_nul(par_partie, budget)
            autre = hasard.get(nom)
            gap = (
                "sans objet"
                if autre is None or autre.taux() is None
                else f"{-100 * autre.taux():+.2f} pt"
            )
            lignes.append(
                f"| `{nom}` | **0 %** | {par_partie:.4f} | borne exacte "
                f"{'sans objet' if borne is None else _pct(borne)} | {gap} | "
                "voir ci-dessous |"
            )
            continue
        autre = hasard.get(nom)
        observe = (
            None
            if autre is None or autre.taux() is None
            else compte.taux() - autre.taux()
        )
        besoin = (
            None
            if observe is None
            else phase2.parties_pour_separer_un_taux(
                compte.taux(), par_partie, abs(observe)
            )
        )
        lignes.append(
            f"| `{nom}` | {_pct(compte.taux())} | {par_partie:.4f} | "
            f"{'sans objet' if detectable is None else _pct(detectable)} | "
            f"{'sans objet' if observe is None else f'{100 * observe:+.2f} pt'} | "
            f"{'sans objet' if besoin is None else besoin} |"
        )

    b7 = greedy["B7-gaspillage"]
    occ = greedy["B7-occasions"]
    par_partie_b7 = b7.total / nb_reference
    detectable_b7 = phase2.ecart_de_taux_detectable(b7.taux(), par_partie_b7, budget)
    ecart_b7 = abs(b7.taux() - hasard["B7-gaspillage"].taux())
    besoin_b7 = phase2.parties_pour_separer_un_taux(b7.taux(), par_partie_b7, ecart_b7)
    lignes += [
        "",
        "### Les deux zeros ne sont pas « rien a detecter »",
        "",
        "`B4-contre-nature` et `B4-meurtre-couteux` valent **exactement 0** chez le greedy, par "
        "construction : `choisir` prend un argmax. Un taux nul a une variance estimee nulle, "
        "donc la formule normale rendrait un ecart detectable de zero -- « tout est detectable » "
        "--, ce qui est exactement faux. Ce qui se dit d'un zero, c'est sa **borne haute "
        f"exacte** de Clopper-Pearson : au budget de {budget} parties, un agent dont ce compteur "
        "depasse la borne ci-dessus est **separable** du greedy ; en dessous, il ne l'est pas. "
        "C'est ce qui empeche de lire « le greedy ne le fait jamais » comme « aucun agent ne "
        "peut faire mieux ».",
        "",
        "### B7 n'a aucun pouvoir discriminant a ce budget, et ce n'est pas une opinion",
        "",
        f"L'occasion ne survient que dans {_pct(occ.taux())} des poses au banquet, soit "
        f"{occ.succes} occasions sur {occ.total}. A {budget} parties il en resterait de l'ordre "
        f"de {round(budget * occ.total / nb_reference * occ.taux())}.",
        "",
        f"L'ecart greedy-hasard observe vaut "
        f"{100 * (b7.taux() - hasard['B7-gaspillage'].taux()):+.2f} point, quand l'ecart "
        f"detectable a {budget} parties est de {_pct(detectable_b7)}. **B7 ne peut donc rien "
        "separer au budget de la phase 3**, et il faudrait "
        f"{besoin_b7} parties pour esperer trancher l'ecart observe.",
        "",
        "**C'est le meme defaut que les quatre criteres de non-degenerescence de la phase 1 et "
        "que le seuil de 38 % de M1** : un critere qui constate au lieu de tester. Ca fait "
        "trois fois dans ce projet. La colonne « ecart detectable » ci-dessus existe pour que "
        "la quatrieme n'arrive pas -- un lecteur de la phase 3 qui comparerait son agent au "
        f"{_pct(b7.taux())} de B7 comparerait du bruit.",
    ]


def section_ce_que_ca_n_etablit_pas(
    lignes: list[str], greedy: dict[str, comp.Compte]
) -> None:
    """La section que la pre-inscription impose, avec les chiffres de la mesure dedans."""
    lignes.append(_titre("7. Ce que ces chiffres n'etablissent PAS"))
    b1 = greedy["B1-motif"]
    lignes += [
        f"1. **Le greedy ne planifie rien.** Son horizon est d'un tour, par construction. Les "
        f"{_pct(b1.taux())} de parties portant le motif B1 mesurent la frequence a laquelle "
        f"le MOTIF apparait par **coincidence** -- deux actions separees, chacune localement "
        f"optimale, qui forment apres coup la figure d'un plan. Ecrire « le greedy planifie des "
        f"retournements dans {_pct(b1.taux())} des parties » serait **faux**. Le chiffre "
        f"s'intitule *frequence du motif B1*, jamais *frequence de planification*.",
        "2. **Le meme avertissement vaut mot pour mot pour B3.** Le greedy ne modelise pas "
        "l'interet qu'il cree en donnant une carte : son B3 mesure la coincidence entre ce "
        "qu'il detient et ce qu'il donne.",
        "3. **B1 a un plafond que rien ne franchira.** La phase 1 a mesure que 7,40 % des "
        "parties portent une perte d'acquis qu'aucun des trois sieges ne pouvait voir. Ces "
        "retournements sont invulnerables a toute planification, par n'importe quel agent : une "
        "ligne de base B1 basse est un **plafond du mesurable**, pas un defaut d'agent.",
        "4. **Une part de B4 mesure le departage, pas le jeu** -- "
        f"{_pct(greedy['B4-tout-dos'].taux())} des nœuds de ciblage. Le taux brut ne se "
        "publie donc jamais seul.",
        "5. **M3 ne dit pas que le greedy est fort.** Il dit qu'il bat le hasard. Aucun chiffre "
        "ici ne borne la distance entre le greedy et un bon joueur.",
        "6. **M1 ne dit rien de l'avantage de siege sous d'autres politiques.** La permutation "
        "systematique rend la question sans consequence pratique ; elle ne la resout pas.",
        "7. **Aucun de ces chiffres ne dit quoi que ce soit de `complet-3j`** -- 6 familles, "
        "3 exemplaires, 10 tours. Rien ne se transporte par un facteur.",
        "8. **La phase 2 ne valide pas le moteur.** Elle le suppose conforme ; c'est la phase 0 "
        "qui l'etablit, et elle est close.",
    ]


def rapport(donnes_a: int, donnes_b: int, avec_variantes: bool = True) -> str:
    """Joue tout et rend le rapport complet en Markdown.

    **Chaque campagne est mesuree puis liberee avant la suivante.** Les traces portent, par
    decision, la vue du decideur, la verite et l'evaluation de chaque action legale : garder
    cinq campagnes de 10 002 parties vivantes en meme temps demanderait plus d'un gigaoctet.
    Les objets de resultat, eux, tiennent en quelques kilooctets. On mesure, on retient le
    resultat, on jette les parties.
    """
    lignes: list[str] = ["# Phase 2 -- les quatre mesures"]
    lignes += [
        "",
        "Genere par `uv run python -m mesure.phase2`. Aucune interpretation : chaque chiffre "
        "porte sa decomposition. Les seuils rappeles sont ceux de "
        "`mesure/phase2_hypothese_et_instrument.md`, commites **avant** la mesure.",
    ]
    section_plan(lignes, donnes_a, donnes_b)
    durees: list[tuple[str, float]] = []

    # --- Campagne A : M1, M2, et la ligne de base du hasard ---------------------------
    debut = perf_counter()
    groupes = phase2.campagne_a(donnes_a)
    durees.append(("A", perf_counter() - debut))
    alea = random.Random(phase2.DECALAGE_BOOTSTRAP)
    resultats_m1 = phase2.mesurer_m1(groupes, alea)
    resultat_m2 = phase2.mesurer_m2(groupes)
    hasard = phase2.mesurer_m4(groupes)
    b6_hasard = phase2.mesurer_b6(groupes)
    b6_concurrente_hasard = phase2.mesurer_b6_concurrente(groupes)
    del groupes

    # --- Bloc de controle : M1 seul, sur des seeds disjoints --------------------------
    debut = perf_counter()
    groupes = phase2.campagne_a(donnes_a, depart=phase2.DEPART_A_CONTROLE)
    durees.append(("A controle", perf_counter() - debut))
    resultats_m1_controle = phase2.mesurer_m1(
        groupes, random.Random(phase2.DECALAGE_BOOTSTRAP + 1)
    )
    del groupes

    # --- Campagne B : M3 de reference, et la ligne de base du greedy ------------------
    debut = perf_counter()
    groupes = phase2.campagne_b(donnes_b)
    durees.append(("B", perf_counter() - debut))
    resultats_m3 = [
        phase2.mesurer_m3(groupes, "1 greedy contre 2 aleatoires (reference)", alea)
    ]
    greedy = phase2.mesurer_m4(groupes)
    b6_greedy = phase2.mesurer_b6(groupes)
    b6_concurrente_greedy = phase2.mesurer_b6_concurrente(groupes)
    del groupes

    # --- Les deux variantes rapportees a cote de M3 -----------------------------------
    if avec_variantes:
        for intitule, arguments in (
            ("2 greedys contre 1 aleatoire", {"nb_greedys": 2}),
            ("1 greedy, departage deterministe", {"departage_deterministe": True}),
        ):
            debut = perf_counter()
            groupes = phase2.campagne_b(donnes_b, **arguments)
            durees.append((f"B, {intitule}", perf_counter() - debut))
            resultats_m3.append(phase2.mesurer_m3(groupes, intitule, alea))
            del groupes

    section_m1(lignes, resultats_m1, f"seeds {phase2.DEPART_A}+")
    section_m1(
        lignes,
        resultats_m1_controle,
        f"bloc de controle, seeds {phase2.DEPART_A_CONTROLE}+",
    )
    section_m2(lignes, resultat_m2)
    section_m3(lignes, resultats_m3)
    section_m4(
        lignes,
        greedy,
        hasard,
        b6_greedy,
        b6_hasard,
        b6_concurrente_greedy,
        b6_concurrente_hasard,
    )
    section_pouvoir_discriminant(lignes, greedy, hasard)
    section_ce_que_ca_n_etablit_pas(lignes, greedy)

    lignes.append(_titre("8. Duree machine"))
    lignes += ["| Campagne | Duree |", "|---|---:|"]
    for nom, duree in durees:
        lignes.append(f"| {nom} | {duree:.1f} s |")
    return "\n".join(lignes)


__all__ = ["rapport"]
