"""L'audit de mon propre resultat -- **ecrit AVANT de le voir**.

Etape 6 de la boucle du paragraphe 2 du protocole : « le resultat est audite avant d'etre cru ».
Ce module existe pour une raison precise : un controle ecrit **apres** avoir vu un chiffre est
un controle que le chiffre a passe par construction. Celui-ci est ecrit et commite avant que
l'agent ne soit mesure.

Les trois questions du protocole, et les cinq du paragraphe 0.2
----------------------------------------------------------------
Chaque controle porte le numero de la question qu'il instruit.

  Q1. La mesure mesure-t-elle ce que je crois ?
  Q2. Sur quel support est-elle definie ?
  Q3. Est-elle comparable a quoi ?

  R1. Chaque taux a-t-il le bon denominateur ?
  R2. Chaque chiffre nomme-t-il la POPULATION dont il parle ?
  R3. Deux lignes comparees sont-elles au meme grain ?
  R4. Un zero ou un cent pour cent a-t-il ete confronte a un cas construit a la main ?
  R5. L'unite a-t-elle ete reconstruite AVANT la valeur, et separement ?

Ce que ce module ne fait pas
------------------------------
Il ne rejuge pas l'agent et ne recalcule pas le verdict par un second chemin qui partagerait
les memes hypotheses. **Reproduire un nombre ne le valide pas** : deux implementations qui
partagent la meme hypothese fausse concordent parfaitement, et un facteur trois indu a survecu
a deux verifications reussies pour cette raison. Les controles ci-dessous portent donc sur des
**unites**, des **denominateurs** et des **populations**, pas sur des valeurs.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass

from mesure import bootstrap as boot
from mesure import comportements as comp
from mesure import phase2, phase3, phase3_mesure


@dataclass(frozen=True)
class Controle:
    """Un controle hostile, son verdict et sa preuve.

    Attributes:
        code: la question instruite -- `Q1`, `R3`, ...
        intitule: ce que le controle cherche a casser.
        passe: vrai si le controle est concluant.
        preuve: le chiffre ou le fait qui l'etablit. **Jamais « OK ».**
    """

    code: str
    intitule: str
    passe: bool
    preuve: str


def _c(code: str, intitule: str, passe: bool, preuve: str) -> Controle:
    return Controle(code=code, intitule=intitule, passe=passe, preuve=preuve)


def controle_niveau_nul(donnes: int, depart: int) -> Controle:
    """**Q1.** Le niveau nul du juge est-il ou je crois qu'il est, SUR LES SEEDS DU VERDICT ?

    La pre-inscription calibre l'instrument sur les seeds `20000-21999`. Le verdict est rendu
    sur `30000+`. **Ce n'est pas le meme echantillon**, et un niveau nul verifie ailleurs ne
    dit rien ici : ce controle refait la calibration sur les donnes exactes du verdict, avec
    le greedy a la place de l'agent.

    Si l'IC ne contient pas 0, **c'est l'instrument qui est faux, pas l'agent** -- et aucun
    chiffre du rapport ne vaut.
    """
    campagne = phase3.jouer_composition(
        agent=phase3.greedy_de_reference,
        adversaire=phase3.greedy_de_reference,
        donnes=donnes,
        intitule="1 greedy contre 2 greedys, seeds du verdict",
        depart=depart,
    )
    verdict = phase3.juger(campagne)
    basse, haute = verdict.gain.intervalle
    return _c(
        "Q1",
        "le niveau nul du juge, recalibre sur les seeds du verdict",
        basse <= 0.0 <= haute,
        f"gain moyen {verdict.gain.moyenne:+.4f}, IC 99 % [{basse:+.4f} ; {haute:+.4f}] sur "
        f"{campagne.nb_parties} parties, seeds {depart}-{depart + donnes - 1}",
    )


def controle_somme_nulle(mesure: phase3_mesure.Mesure, campagne: phase3.Campagne) -> Controle:
    """**Q1.** La somme des gains vaut-elle 0 dans CHAQUE partie ?

    C'est l'invariant I5 et le paragraphe 5.2. Il fonde le niveau nul exact du seuil : s'il
    tombait, le seuil n'aurait plus de valeur nulle connue.
    """
    pire = 0.0
    parties = 0
    for groupe in campagne.traces:
        for trace in groupe:
            pire = max(pire, abs(sum(trace.gains)))
            parties += 1
    return _c(
        "Q1",
        "la somme des gains vaut 0 dans chaque partie (I5, paragraphe 5.2)",
        pire < 1e-12,
        f"ecart maximal a zero : {pire:.3e} sur {parties} parties de « {mesure.intitule} »",
    )


def controle_plan_equilibre(campagne: phase3.Campagne) -> Controle:
    """**Q2.** Chaque siege est-il occupe exactement une fois par donne ?

    C'est ce qui rend l'esperance du niveau nul exacte. Un plan desequilibre la deplacerait
    d'un ecart entre sieges -- et le contraste entre sieges extremes vaut **+0,5735** dans
    cette composition, soit plus de dix fois l'effet cherche.
    """
    fautifs = [
        donne
        for donne, sieges in zip(campagne.donnes, campagne.sieges_mesures, strict=True)
        if sorted(sieges) != list(range(phase3.CONFIG.joueurs))
    ]
    return _c(
        "Q2",
        "chaque siege exactement une fois par donne",
        not fautifs,
        f"{len(campagne.donnes)} donnes verifiees, {len(fautifs)} desequilibrees"
        + (f" : {fautifs[:5]}" if fautifs else ""),
    )


def controle_denominateur(mesure: phase3_mesure.Mesure) -> Controle:
    """**R1.** `parties = donnes x sieges`, reconstruit et non recopie."""
    attendu = mesure.nb_donnes * phase3.CONFIG.joueurs
    return _c(
        "R1",
        "le denominateur du verdict est `donnes x sieges`",
        mesure.nb_parties == attendu,
        f"{mesure.nb_donnes} donnes x {phase3.CONFIG.joueurs} sieges = {attendu}, "
        f"rapporte : {mesure.nb_parties}",
    )


def controle_populations_nommees(mesures: Sequence[phase3_mesure.Mesure]) -> Controle:
    """**R2.** Chaque mesure nomme-t-elle sa composition, et les noms sont-ils distincts ?

    Deux compositions portant le meme intitule se liraient comme une seule dans le rapport.
    """
    intitules = [mesure.intitule for mesure in mesures]
    sans_composition = [x for x in intitules if "contre" not in x]
    doublons = sorted({x for x in intitules if intitules.count(x) > 1})
    return _c(
        "R2",
        "chaque composition est nommee, et les noms sont distincts",
        not sans_composition and not doublons,
        f"{len(intitules)} compositions, {len(set(intitules))} noms distincts"
        + (f" ; sans composition : {sans_composition}" if sans_composition else "")
        + (f" ; doublons : {doublons}" if doublons else ""),
    )


def controle_grains(comparaisons: Sequence[phase3_mesure.Comparaison]) -> Controle:
    """**R3.** Deux lignes comparees portent-elles le MEME grain, libelle compris ?

    `ecart_de_taux` leve deja si les grains different -- ce controle verifie que la garde a
    bien ete traversee pour **toutes** les lignes, et pas seulement pour celles qu'on a
    regardees. Une ligne exclue n'est pas comparee : elle n'a pas a coincider.
    """
    fautives = [
        c.nom
        for c in comparaisons
        if c.exclu is None and c.agent.grain != c.base.grain
    ]
    comparees = sum(1 for c in comparaisons if c.exclu is None)
    return _c(
        "R3",
        "les lignes comparees sont au meme grain",
        not fautives,
        f"{comparees} lignes comparees sur {len(comparaisons)}, {len(fautives)} a grains "
        f"differents" + (f" : {fautives}" if fautives else ""),
    )


def controle_zeros(comparaisons: Sequence[phase3_mesure.Comparaison]) -> Controle:
    """**R4.** Tout zero ou cent pour cent publie est-il confronte a un cas construit ?

    Un zero absolu se confronte a un cas construit a la main **avant** d'etre ecrit : le zero
    de la phase 1 etait contredit par un test du meme livrable. Ce controle **liste** les zeros
    et les cent pour cent pour que le rapport les traite un par un ; il ne les valide pas.
    """
    extremes = [
        f"{c.nom}={c.agent.succes}/{c.agent.total}"
        for c in comparaisons
        if c.agent.total > 0 and c.agent.taux() in (0.0, 1.0)
    ]
    return _c(
        "R4",
        "les zeros et les cent pour cent sont listes pour traitement individuel",
        True,
        f"{len(extremes)} valeur(s) extreme(s) chez l'agent"
        + (f" : {', '.join(extremes)}" if extremes else " -- aucune"),
    )


def controle_unite_avant_valeur(
    mesure: phase3_mesure.Mesure, base: dict[str, comp.Compte], nb_parties_base: int
) -> Controle:
    """**R5.** L'unite est-elle reconstruite avant la valeur, et separement ?

    Le controle ne compare aucun taux. Il reconstruit, pour chaque compteur, le nombre
    d'observations **par partie** des deux cotes, et exige qu'ils coincident -- l'unite --
    **sans regarder les numerateurs** -- la valeur. C'est le controle qui manquait a la
    phase 2, ou un facteur trois a survecu a deux verifications parce que la formule de
    controle recevait le meme denominateur errone que le generateur.

    La tolerance est de 5 % relatif : les denominateurs d'action -- poses d'Assassin, nœuds de
    ciblage -- dependent de la politique et ne coincident pas au nœud pres entre deux agents
    differents. Les lignes `-par-partie`, elles, doivent valoir 1,0 exactement des deux cotes,
    et `phase2.observations_par_partie` **leve** sinon.
    """
    ecarts = []
    for nom in sorted(set(mesure.comportements) & set(base)):
        a = phase2.observations_par_partie(mesure.comportements[nom], mesure.nb_parties)
        b = phase2.observations_par_partie(base[nom], nb_parties_base)
        if b > 0 and abs(a - b) / b > 0.05:
            ecarts.append(f"{nom} {a:.3f} vs {b:.3f}")
    return _c(
        "R5",
        "l'unite -- observations par partie -- coincide, numerateurs non regardes",
        True,
        f"{len(ecarts)} compteur(s) dont l'unite differe de plus de 5 % : "
        + (", ".join(ecarts) if ecarts else "aucun")
        + ". Un ecart n'est pas fautif en soi -- un denominateur d'action depend de la "
        "politique -- mais il doit etre lu avant de comparer les taux.",
    )


def controle_seeds_disjoints(
    donnes_verdict: int, donnes_pool: int, nb_checkpoints: int, parties_entrainement: int
) -> Controle:
    """**Q3.** Les donnes du verdict sont-elles disjointes de celles de l'entrainement ?

    Juger sur les donnes d'entrainement donnerait a l'agent un avantage qui n'est pas de
    l'habilete, et le chiffre serait juste sur une population que sa phrase ne nomme pas.

    **Ce controle a trouve un vrai defaut avant la mesure.** La premiere version de
    `phase3_mesure` decalait les compositions du pool de `+100 000` et `+200 000` a partir de
    `30 000`, donc a `130 000` et `230 000+` -- **dans la plage d'entrainement**, qui part a
    `100 000` et consomme une donne par partie jouee. Les plages sont desormais toutes sous
    `100 000`.

    Les bornes sont **calculees depuis les comptes reels**, pas declarees a la main : une
    plage declaree plus etroite qu'elle ne l'est laisserait passer exactement le defaut que ce
    controle cherche.
    """
    from agents import campagne, entrainement

    plages: dict[str, tuple[int, int]] = {
        "dimensionnement": (phase3.DEPART_DONNE, phase3.DEPART_DONNE + donnes_verdict),
        "garde-fou": (
            campagne.DEPART_DONNE_GARDE_FOU,
            campagne.DEPART_DONNE_GARDE_FOU + campagne.DONNES_GARDE_FOU,
        ),
        "verdict": (
            phase3_mesure.DEPART_CAMPAGNE_FINALE,
            phase3_mesure.DEPART_CAMPAGNE_FINALE + donnes_verdict,
        ),
        "pool aleatoire": (
            phase3_mesure.DEPART_CAMPAGNE_FINALE + phase3_mesure.DECALAGE_POOL_ALEATOIRE,
            phase3_mesure.DEPART_CAMPAGNE_FINALE
            + phase3_mesure.DECALAGE_POOL_ALEATOIRE
            + donnes_pool,
        ),
        "variante deterministe": (
            phase3_mesure.DEPART_CAMPAGNE_FINALE
            + phase3_mesure.DECALAGE_VARIANTE_DETERMINISTE,
            phase3_mesure.DEPART_CAMPAGNE_FINALE
            + phase3_mesure.DECALAGE_VARIANTE_DETERMINISTE
            + donnes_verdict,
        ),
        "entrainement": (
            entrainement.DEPART_DONNE_ENTRAINEMENT,
            entrainement.DEPART_DONNE_ENTRAINEMENT + parties_entrainement,
        ),
    }
    for indice in range(max(nb_checkpoints, 1)):
        debut = (
            phase3_mesure.DEPART_CAMPAGNE_FINALE
            + phase3_mesure.DECALAGE_POOL_CHECKPOINTS
            + phase3_mesure.PAS_ENTRE_CHECKPOINTS * indice
        )
        plages[f"pool checkpoint {indice + 1}"] = (debut, debut + donnes_pool)

    chevauchements = []
    noms = sorted(plages)
    for i, un in enumerate(noms):
        for autre in noms[i + 1 :]:
            (a0, a1), (b0, b1) = plages[un], plages[autre]
            if a0 < b1 and b0 < a1:
                chevauchements.append(f"{un} [{a0}, {a1}) x {autre} [{b0}, {b1})")
    return _c(
        "Q3",
        "les plages de donnes ne se chevauchent pas",
        not chevauchements,
        "; ".join(f"{nom} [{a}, {b})" for nom, (a, b) in sorted(plages.items()))
        + (f" ; CHEVAUCHEMENTS : {chevauchements}" if chevauchements else " ; disjointes"),
    )


def controle_bootstrap_par_donne(campagne: phase3.Campagne) -> Controle:
    """**Q2.** Le bootstrap rechantillonne-t-il des DONNES et non des parties ?

    Tirer des parties detruirait la structure qu'on mesure -- c'est elle qui porte le `rho`
    negatif, donc le gain de variance de la permutation. Le controle compare l'effet de plan
    rendu par le bootstrap a celui de l'analyse de variance : deux routes independantes qui
    doivent concorder. Si le bootstrap tirait des parties, son effet vaudrait 1,0 par
    construction.
    """
    gains = campagne.gains_par_donne()
    effet_bootstrap = boot.bootstrap_par_donne(
        gains, phase3.RECHANTILLONS, random.Random(phase3.GRAINE_BOOTSTRAP)
    ).effet
    rho = boot.correlation_intra_donne(gains)
    effet_anova = (
        None if rho is None else 1.0 + (campagne.replicats_par_donne - 1) * rho
    )
    concordent = (
        effet_anova is not None and abs(effet_bootstrap - effet_anova) / effet_anova < 0.10
    )
    return _c(
        "Q2",
        "le bootstrap tire des donnes -- deux routes vers l'effet de plan concordent",
        concordent,
        f"effet bootstrap {effet_bootstrap:.4f}, effet par analyse de variance "
        + ("non defini" if effet_anova is None else f"{effet_anova:.4f}")
        + " ; un bootstrap qui tirerait des parties rendrait 1,0000",
    )


def auditer(
    mesure: phase3_mesure.Mesure,
    campagne: phase3.Campagne,
    pool: Sequence[phase3_mesure.Mesure],
    comparaisons: Sequence[phase3_mesure.Comparaison],
    base: dict[str, comp.Compte],
    nb_parties_base: int,
    donnes_calibration: int,
    donnes_pool: int,
    nb_checkpoints: int,
    parties_entrainement: int,
) -> list[Controle]:
    """Joue tous les controles et rend leurs verdicts, dans l'ordre des questions."""
    return [
        controle_niveau_nul(donnes_calibration, phase3_mesure.DEPART_CAMPAGNE_FINALE),
        controle_somme_nulle(mesure, campagne),
        controle_plan_equilibre(campagne),
        controle_bootstrap_par_donne(campagne),
        controle_seeds_disjoints(
            donnes_verdict=donnes_calibration,
            donnes_pool=donnes_pool,
            nb_checkpoints=nb_checkpoints,
            parties_entrainement=parties_entrainement,
        ),
        controle_denominateur(mesure),
        controle_populations_nommees(pool),
        controle_grains(comparaisons),
        controle_zeros(comparaisons),
        controle_unite_avant_valeur(mesure, base, nb_parties_base),
    ]


__all__ = ["Controle", "auditer"]
