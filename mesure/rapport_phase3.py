"""Le rapport de la phase 3. **Ecrit en UTF-8 depuis Python, jamais par une redirection.**

C'est le defaut mineur 2 de la phase 2, ferme au debut de celle-ci : le rapport de la phase 2
partait sur la sortie standard et c'est la console qui decidait de son encodage. Ce
generateur-ci ecrit son fichier lui-meme, avec `encoding="utf-8"` explicite. Il ne peut pas
naitre en cp1252.

Aucune interpretation : chaque chiffre porte sa decomposition, sa composition et son
denominateur. Les seuils rappeles sont ceux de `mesure/phase3_hypothese_et_instrument.md`,
commite **avant** l'entrainement.
"""

from __future__ import annotations

import pathlib
from collections.abc import Sequence

from mesure import phase3, phase3_mesure


def _pct(valeur: float | None) -> str:
    return "-" if valeur is None else f"{valeur * 100:.2f} %"


def _pt(valeur: float | None) -> str:
    return "-" if valeur is None else f"{valeur * 100:+.2f} pt"


def _titre(texte: str) -> str:
    return f"\n## {texte}\n"


def section_juge(lignes: list[str], mesure: phase3_mesure.Mesure) -> None:
    """Le juge du protocole : gain moyen, borne basse de l'IC 99 %, part fractionnee a cote."""
    verdict = mesure.verdict
    basse, haute = verdict.gain.intervalle
    lignes.append(_titre("1. Le juge -- gain moyen contre deux greedys"))
    lignes += [
        f"**Composition : {mesure.intitule}.** {mesure.nb_donnes} donnes x "
        f"{phase3.CONFIG.joueurs} sieges = **{mesure.nb_parties} parties**. Bootstrap **par "
        f"donne**, {phase3.RECHANTILLONS} rechantillons.",
        "",
        "**Le niveau nul du gain moyen est exactement 0,0000**, et il n'est pas estime : sous "
        "l'hypothese nulle, l'esperance du gain mesure vaut 0 par la somme nulle du paragraphe "
        "5.2 et par la permutation systematique des sieges. Voir le paragraphe 1 de la "
        "pre-inscription.",
        "",
        "| Grandeur | Valeur | Niveau nul |",
        "|---|---:|---:|",
        f"| **Gain moyen** | **{verdict.gain.moyenne:+.4f}** | **0,0000** (exact) |",
        f"| IC 99 % bootstrap par donne | [{basse:+.4f} ; {haute:+.4f}] | |",
        f"| Part de victoire fractionnee | {_pct(verdict.part_fractionnee.moyenne)} | "
        f"{_pct(verdict.part_neutre)} (exact) |",
        f"| Part de victoire stricte | {_pct(verdict.part_stricte)} | "
        f"**inconnu d'avance -- jamais un seuil** |",
        "",
        f"**Seuil du protocole : la borne basse de l'IC 99 % est-elle strictement positive ?** "
        f"Elle vaut **{basse:+.4f}**. "
        + (
            "**OUI -- l'agent bat le greedy.**"
            if verdict.bat_le_greedy
            else (
                "**NON.** "
                + (
                    "L'IC contient 0 : **non conclu a ce budget**. Ce n'est pas « l'agent ne "
                    "bat pas le greedy »."
                    if haute > 0
                    else "La borne haute est negative : **l'agent est battu par le greedy**."
                )
            )
        ),
        "",
        "### Le gain par siege -- a cote de la moyenne, jamais a sa place",
        "",
        "**L'avantage de siege est massif dans cette composition** : contraste apparie entre "
        "sieges extremes **+0,5735**, IC 99 % [+0,5218 ; +0,6240], mesure sur la population de "
        "l'hypothese nulle. Un chiffre d'un seul siege ne se compare **jamais** a un chiffre "
        "agrege sur trois.",
        "",
        "| Siege occupe | Gain moyen de l'agent |",
        "|---|---:|",
    ]
    for siege, gain in sorted(verdict.gains_par_siege.items()):
        lignes.append(f"| siege {siege} | {gain:+.4f} |")
    somme = sum(verdict.gains_par_siege.values())
    lignes += [
        "",
        f"Somme des trois : **{somme:+.4f}**. Elle n'est nulle qu'a la precision "
        f"d'echantillonnage -- l'agent occupe chaque siege une fois par donne, mais les trois "
        f"parties d'une donne sont **trois parties differentes**.",
    ]


def section_dimensionnement(lignes: list[str], mesure: phase3_mesure.Mesure) -> None:
    """`sigma` et `rho` **remesures** sur la composition reelle, contre ceux du nul."""
    dim = mesure.dimensionnement
    basse, haute = mesure.verdict.gain.intervalle
    demi_largeur = (haute - basse) / 2
    detectable = dim.ecart_detectable(dim.nb_parties)
    rho = "-" if dim.rho is None else f"**{dim.rho:+.4f}**"
    effet = "-" if dim.effet_de_plan is None else f"**{dim.effet_de_plan:.4f}**"

    lignes.append(_titre("2. Le dimensionnement, remesure sur la composition reelle"))
    lignes += [
        "La pre-inscription mesure `sigma` et `rho` **sous l'hypothese nulle** -- le greedy mis "
        "a la place de l'agent. Un agent different a une distribution de gain differente : "
        "l'ecart entre le **SUPPOSE** de la pre-inscription et le **MESURE** ci-dessous est un "
        "chiffre, et non un oubli.",
        "",
        "| Grandeur | Pre-inscription (hypothese nulle) | Mesure ici |",
        "|---|---:|---:|",
        f"| `sigma(gain)` | 0,6494 | **{dim.sigma_gain:.4f}** |",
        f"| `rho` intra-donne | −0,1400 | {rho} |",
        f"| effet de plan (analyse de variance) | 0,7200 | {effet} |",
        f"| effet de plan (bootstrap) | 0,7223 | **{dim.gain.effet:.4f}** |",
        "",
        f"**Ecart de gain detectable a ce budget** : **{detectable:+.4f}** sur "
        f"{dim.nb_parties} parties, 99 % bilateral et 80 % de puissance. La pre-inscription "
        f"annoncait **+0,0243**.",
        "",
        f"**Demi-largeur de l'IC 99 % du gain** : **{demi_largeur:.4f}** sur "
        f"{dim.nb_parties} parties.",
        "",
        "> **Elle ne se compare pas telle quelle au 0,0183 de la pre-inscription**, et c'est la "
        "faute du projet appliquee a un budget plutot qu'a une population. Une demi-largeur "
        "depend de **deux** choses : `sigma`, propre a la composition, et `n`, propre au "
        "budget. Le 0,0183 est pre-inscrit **a 6 000 parties**. Le confronter a une "
        "demi-largeur mesuree sur un autre nombre de parties melangerait un effet de "
        "composition et un effet de budget.",
        ">",
        f"> **Ce qui se compare est `sigma`**, qui ne depend pas de `n` : **{dim.sigma_gain:.4f}** "
        f"ici contre **0,6494** sous l'hypothese nulle, soit "
        f"**{(dim.sigma_gain / 0.6494 - 1) * 100:+.1f} %**"
        + (
            ". `sigma` a bouge de plus de 10 % : la pre-inscription le donnait comme SUPPOSE, "
            "et il faut donc le dire ici plutot que de laisser le budget se lire comme s'il "
            "n'avait pas bouge."
            if abs(dim.sigma_gain / 0.6494 - 1) > 0.10
            else ". `sigma` tient dans la marge de 10 % que la pre-inscription s'etait donnee."
        ),
        ">",
        f"> Pour memoire, la demi-largeur **ramenee a 6 000 parties** vaut "
        f"`{demi_largeur:.4f} x sqrt({dim.nb_parties} / 6000)` = "
        f"**{demi_largeur * (dim.nb_parties / 6000) ** 0.5:.4f}**, et c'est **cette** valeur "
        f"qui se lit contre 0,0183. La conversion suppose que l'effet de plan est le meme aux "
        f"deux tailles, ce qui est vrai a `rho` constant.",
    ]


def section_pool(lignes: list[str], mesures: Sequence[phase3_mesure.Mesure]) -> None:
    """Chaque membre du pool, **avec sa composition nommee**."""
    lignes.append(_titre("3. Le pool -- chaque composition, nommee"))
    lignes += [
        "**Aucune de ces lignes n'est le juge.** Le juge est le gain moyen contre deux greedys, "
        "et lui seul. Les autres compositions repondent a d'autres questions.",
        "",
        "| Composition | Parties | Gain moyen | IC 99 % | Part fractionnee | Neutre |",
        "|---|---:|---:|---|---:|---:|",
    ]
    for mesure in mesures:
        basse, haute = mesure.verdict.gain.intervalle
        lignes.append(
            f"| {mesure.intitule} | {mesure.nb_parties} | "
            f"{mesure.verdict.gain.moyenne:+.4f} | [{basse:+.4f} ; {haute:+.4f}] | "
            f"{_pct(mesure.verdict.part_fractionnee.moyenne)} | "
            f"{_pct(mesure.verdict.part_neutre)} |"
        )
    lignes += [
        "",
        "**Un agent qui ecrase ses propres checkpoints mais ne bat pas le greedy est le "
        "symptome exact de l'effondrement de convention en self-play.** C'est la contrepartie "
        "assumee d'avoir sorti le greedy du pool d'entrainement, elle est pre-inscrite au "
        "paragraphe 6, et c'est un resultat publiable, pas un echec a cacher.",
    ]


def section_garde_fou(lignes: list[str], jalons: Sequence[dict]) -> None:
    """La courbe du garde-fou, checkpoint par checkpoint."""
    lignes.append(_titre("4. Le garde-fou -- un agent contre deux aleatoires"))
    lignes += [
        "**Ce n'est pas un juge.** Depasser 86,52 % ne dit rien sur le fait de battre le "
        "greedy : le greedy y est deja. C'est un detecteur d'agent qui n'apprend pas.",
        "",
        "Le **86,52 %** est une **moyenne sur les trois sieges**, agregee sur les 10 002 "
        "parties de la campagne B de la phase 2, et il ne se compare qu'a une mesure agregee "
        "de la meme facon. La colonne ci-dessous l'est.",
        "",
        f"Chaque checkpoint : {phase3_mesure_donnes_garde_fou()} donnes x "
        f"{phase3.CONFIG.joueurs} sieges. IC corrige de **Bonferroni pour 8 regards**.",
        "",
        "| # | s | Parties d'entrainement | Entropie | Part fractionnee | IC (Bonferroni) | "
        "Gain moyen |",
        "|---:|---:|---:|---:|---:|---|---:|",
    ]
    for jalon in jalons:
        lignes.append(
            f"| {jalon['numero']} | {jalon['secondes']:.0f} | {jalon['parties']} | "
            f"{jalon['entropie']:.4f} | {_pct(jalon['part_fractionnee'])} | "
            f"[{_pct(jalon['borne_basse'])} ; {_pct(jalon['borne_haute'])}] | "
            f"{jalon['gain_moyen']:+.4f} |"
        )
    if jalons:
        dernier = jalons[-1]
        franchi = dernier["part_fractionnee"] > 0.8652
        lignes += [
            "",
            f"**Critere terminal du protocole** : au dernier checkpoint, la part fractionnee "
            f"vaut **{_pct(dernier['part_fractionnee'])}** contre **86,52 %**. "
            + ("**Franchi.**" if franchi else "**NON franchi.**"),
            "",
            "**Arret anticipe** : "
            + (
                "**declenche** -- la part a stagne sur une demi-heure ET la borne haute est "
                "restee sous 86,52 %."
                if any(j["declenche"] for j in jalons)
                else "non declenche."
            ),
        ]


def phase3_mesure_donnes_garde_fou() -> int:
    """Le nombre de donnes du garde-fou, **demande au module qui le fixe**, jamais recopie."""
    from agents import campagne

    return campagne.DONNES_GARDE_FOU


def section_comportements(
    lignes: list[str],
    comparaisons: Sequence[phase3_mesure.Comparaison],
    nb_parties: int,
) -> None:
    """B1 a B7, compares a la ligne de base regeneree **au meme grain**."""
    lignes.append(_titre("5. Les comportements B1 a B7"))
    lignes += [
        "**La ligne de base est REGENEREE**, et ce n'est pas une commodite : ma composition est "
        "un agent contre deux greedys, un seul siege mesure. Sa ligne de base est donc **trois "
        "greedys, UN seul siege compte**, et elle n'existe pas dans le depot. Memes seeds, meme "
        "composition, meme decalage de graine `6000000` : seuls les sieges **comptes** changent.",
        "",
        "`comportements.ecart_de_taux` **leve** si les grains different. Elle est appelee "
        "plutot que contournee : une ligne dont le grain differe fait tomber la mesure au lieu "
        "de produire un nombre qu'il faudrait relire.",
        "",
        f"**Les exclusions sont recalculees au budget de {nb_parties} parties**, jamais "
        f"recopiees : ce sont des proprietes du couple `(ligne, budget)`. Voir "
        f"`mesure/phase3_budget_des_comportements.py`.",
        "",
        "| Compteur | Agent | Ligne de base | Ecart | Detectable | Separable ? |",
        "|---|---|---|---:|---:|---|",
    ]
    for comparaison in comparaisons:
        agent, base = comparaison.agent, comparaison.base
        if comparaison.exclu is not None:
            verdict = f"**non compare** : {comparaison.exclu}"
        elif comparaison.separable:
            verdict = "**separable**"
        else:
            verdict = "non separable a ce budget"
        lignes.append(
            f"| `{comparaison.nom}` | {_pct(agent.taux())} ({agent.succes}/{agent.total}) | "
            f"{_pct(base.taux())} ({base.succes}/{base.total}) | {_pt(comparaison.ecart)} | "
            f"{_pct(comparaison.detectable)} | {verdict} |"
        )


def section_ce_qui_n_est_pas_etabli(lignes: list[str]) -> None:
    """Pre-inscrite au paragraphe 10, recopiee ici pour que le rapport soit autoportant."""
    lignes.append(_titre("7. Ce que ces chiffres n'etablissent PAS"))
    lignes += [
        "**Ecrit avant la mesure**, paragraphe 10 de la pre-inscription.",
        "",
        "1. **B1 et B3 mesurent la frequence a laquelle un MOTIF apparait, jamais une "
        "planification.** Ecrire « l'agent planifie des retournements dans X % des parties » "
        "serait faux quel que soit X. Le chiffre s'intitule *frequence du motif*, jamais "
        "*frequence de planification*.",
        "2. **B1 est plafonne par les 7,40 % de parties portant une perte d'acquis qu'aucun "
        "siege ne pouvait voir**, mesures en phase 1. Ces retournements sont **invulnerables a "
        "toute planification, par n'importe quel agent** : c'est un plafond du mesurable, pas "
        "un defaut d'agent.",
        "3. **Battre le greedy ne dit pas que l'agent est fort.** Le greedy a un horizon d'un "
        "tour, et son gain publie est un **plancher** de lui-meme -- son ciblage est plus myope "
        "que sa specification. Aucun chiffre ici ne borne la distance entre l'agent et un bon "
        "joueur.",
        "4. **Rien ici ne se transporte a `complet-3j`** -- 6 familles, 90 cartes, 10 tours.",
        "5. **Le controle de collision de tenseurs est un echantillon, pas une preuve "
        "d'injectivite.**",
        "6. **Aucun resultat de cette phase ne valide le moteur.** Elle le suppose conforme ; "
        "c'est la phase 0 qui l'etablit, et elle est close.",
        "7. **B7 devient separable par le bas a ce budget, il ne devient pas informatif.** "
        "`B7-occasions` vaut 1,22 % des poses au banquet : l'occasion de se manifester est "
        "rare, et un taux bas se lit sur ce fond-la.",
    ]


def section_audit(lignes: list[str], controles: Sequence) -> None:
    """L'auto-audit, **ecrit avant le resultat** et joue sur lui.

    Un controle ecrit apres avoir vu un chiffre est un controle que le chiffre a passe par
    construction. Ceux-ci sont dans `mesure/phase3_audit.py`, commite avant l'entrainement.
    """
    lignes.append(_titre("6. L'audit de ce resultat, par ses propres controles"))
    lignes += [
        "**Ces controles sont ecrits et commites AVANT que l'agent ne soit mesure** -- "
        "`mesure/phase3_audit.py`. Un controle ecrit apres avoir vu un chiffre est un controle "
        "que le chiffre a passe par construction.",
        "",
        "Ils portent sur des **unites**, des **denominateurs** et des **populations**, jamais "
        "sur des valeurs : reproduire un nombre ne le valide pas, et un facteur trois indu a "
        "survecu a deux verifications reussies en phase 2 pour cette raison.",
        "",
        "| Question | Controle | Verdict | Preuve |",
        "|---|---|---|---|",
    ]
    for controle in controles:
        etat = "concluant" if controle.passe else "**ECHOUE**"
        lignes.append(
            f"| {controle.code} | {controle.intitule} | {etat} | {controle.preuve} |"
        )
    echoues = [c for c in controles if not c.passe]
    lignes += [
        "",
        (
            f"**{len(echoues)} controle(s) en echec : "
            + ", ".join(c.intitule for c in echoues)
            + ". Aucun chiffre de ce rapport ne vaut tant qu'ils ne sont pas expliques.**"
            if echoues
            else f"**{len(controles)} controles, aucun en echec.**"
        ),
    ]


def rapport(
    contre_greedys: phase3_mesure.Mesure,
    pool: Sequence[phase3_mesure.Mesure],
    comparaisons: Sequence[phase3_mesure.Comparaison],
    jalons: Sequence[dict],
    controles: Sequence,
) -> str:
    """Assemble le rapport complet en Markdown."""
    lignes: list[str] = [
        "# Phase 3 -- le premier agent entraine",
        "",
        "Genere par `uv run python -m mesure.phase3_mesure`. Aucune interpretation : chaque "
        "chiffre porte sa decomposition, sa composition et son denominateur. Les seuils "
        "rappeles sont ceux de `mesure/phase3_hypothese_et_instrument.md`, commite **avant** "
        "l'entrainement.",
        "",
        f"Instance : `familles={phase3.CONFIG.familles}`, {len(phase3.CONFIG.roles)} roles, "
        f"`exemplaires={phase3.CONFIG.exemplaires}`, `joueurs={phase3.CONFIG.joueurs}` -- "
        f"{phase3.CONFIG.nb_cartes} cartes, {phase3.CONFIG.tours} tours par joueur.",
        "",
        "Algorithme : **PPO a masque d'actions**, reseau unique partage par les trois sieges, "
        "tete de valeur, `gamma = 1`, `lambda = 1`. Pool d'entrainement : 60 % copie courante, "
        "40 % checkpoint fige. **Ni le greedy ni l'aleatoire n'entrent dans le pool.**",
    ]
    section_juge(lignes, contre_greedys)
    section_dimensionnement(lignes, contre_greedys)
    section_pool(lignes, pool)
    section_garde_fou(lignes, jalons)
    section_comportements(lignes, comparaisons, contre_greedys.nb_parties)
    section_audit(lignes, controles)
    section_ce_qui_n_est_pas_etabli(lignes)
    return "\n".join(lignes) + "\n"


def ecrire(texte: str, chemin: pathlib.Path) -> None:
    """Ecrit le rapport **en UTF-8**, depuis Python. Voir la docstring du module."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(texte, encoding="utf-8", newline="\n")



__all__ = ["ecrire", "rapport"]
