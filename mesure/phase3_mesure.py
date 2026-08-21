"""La mesure finale de la phase 3 : le juge, le pool, et les comportements au meme grain.

Ce module **n'invente aucun compteur et ne redefinit aucun seuil**. Il assemble ce qui existe :

  - le plan et le juge viennent de `mesure/phase3.py`, ecrits et commites avant l'entrainement ;
  - les dix-sept compteurs de comportement viennent de `mesure/comportements.py`, ecrits et
    **audites en phase 2**. Les reecrire ici dupliquerait une definition, ce que le paragraphe 2
    des conventions interdit -- et c'est la mesure qui aurait tort sans que rien ne le signale.

La ligne de base de comportement doit etre REGENEREE, et voici pourquoi
------------------------------------------------------------------------
La phase 2 publie ses compteurs sur deux populations : **un** greedy contre deux aleatoires
(un siege mesure) et **trois** greedys (trois sieges mesures). Aucune des deux n'est la mienne.

Ma composition est **un agent contre deux greedys**, un seul siege mesure. Sa ligne de base --
ce que le greedy obtiendrait a la place de l'agent -- est donc **trois greedys, UN seul siege
compte**. Elle n'existe pas dans le depot :

  - la colonne « 1 greedy, 2 hasards » a la bonne **granularite** mais pas la bonne
    **composition d'adversaires**. Pour `B1-collectif`, dont le numerateur peut etre produit
    entierement par les adversaires, ca change le chiffre ;
  - la colonne « 3 greedys » a la bonne composition mais pas le bon **grain** : elle agrege
    trois sieges mesures, et les lignes `-par-partie` -- « au moins un des N sieges » -- ne
    comptent alors pas la meme chose. `ecart_de_taux` **leve** dans ce cas, et c'est la parade
    posee au tour 2 de la phase 2.

**Ce module regenere donc la troisieme population a un seul siege compte, et rien d'autre ne
change** : memes seeds, meme composition, meme decalage de graine `6000000`. Seuls les sieges
**comptes** changent. Si autre chose bougeait, la ligne de base bougerait pour une seconde
raison et on ne saurait plus laquelle.

Ce qui n'est pas compare, et pourquoi -- deux criteres independants
---------------------------------------------------------------------
**Le budget.** Les marqueurs « hors budget » et « aveugle par le bas » sont des proprietes du
couple `(ligne, budget)`, pas de la ligne. Recalcules au budget de la phase 3 par
`mesure/phase3_budget_des_comportements.py` : **8 lignes hors budget** au lieu de 19, **0
aveugle** au lieu de 2.

**Le texte de la definition.** `B4-tout-dos` et `B5-renfort` ne se comparent pas entre
compositions differentes, et ca ne depend d'aucun budget : leurs taux bougent sous d'autres
agents pour une raison qui n'est pas l'habilete. Le critere se decide sur le TEXTE -- la
definition nomme-t-elle un autre joueur ? `B1-collectif` oui, ces deux-la non.

Les deux criteres sont **independants**. `B4-tout-dos` entre dans le budget a 6 000 parties et
reste exclu par le texte.
"""

from __future__ import annotations

from dataclasses import dataclass

from mesure import comportements as comp
from mesure import phase2, phase3

#: Le decalage de graine de la troisieme population de la phase 2. **Recopie tel quel**, et
#: c'est la contrainte : regenerer avec un autre decalage donnerait d'autres parties, donc une
#: ligne de base qui bouge pour une seconde raison.
DECALAGE_TROIS_GREEDYS = phase2.DECALAGE_POLITIQUE_3_GREEDYS

#: Les donnes de la campagne finale, et les deux decalages des compositions du pool.
#:
#: **TROUVE PAR MON PROPRE CONTROLE D'AUDIT, avant la mesure.** La premiere version partait a
#: `30000` et decalait les compositions du pool de `+100 000` et `+200 000`, ce qui les placait
#: a `130000` et `230000+` -- **dans la plage d'entrainement**. L'entrainement part a `100 000`
#: et, a 229 parties par seconde pendant 7 200 secondes, consomme jusqu'a environ `1 749 000`.
#: La mesure contre deux aleatoires et celles contre les checkpoints auraient donc juge l'agent
#: sur des donnes qu'il avait vues, ce qui lui aurait donne un avantage qui n'est pas de
#: l'habilete -- et le chiffre aurait ete juste sur une population que sa phrase ne nomme pas.
#:
#: Les quatre plages sont desormais **toutes sous 100 000**, la ou l'entrainement ne va jamais :
#:
#:   dimensionnement  20 000 - 21 999   (2 000 donnes)
#:   garde-fou        40 000 - 40 599   (600 donnes, les memes a chaque checkpoint)
#:   verdict          60 000 - 61 999   (2 000 donnes, un agent contre deux greedys)
#:   pool aleatoire   70 000 - 70 499   (500 donnes)
#:   pool checkpoints 80 000 + 1 000 x i (500 donnes chacun, jusqu'a 8 checkpoints)
#:   entrainement    100 000 +           (jamais en dessous)
DEPART_CAMPAGNE_FINALE = 60_000

#: Le decalage de la composition contre deux aleatoires.
DECALAGE_POOL_ALEATOIRE = 10_000

#: Le decalage du premier checkpoint, puis 1 000 par checkpoint suivant.
DECALAGE_POOL_CHECKPOINTS = 20_000
PAS_ENTRE_CHECKPOINTS = 1_000

#: Le decalage de la variante **deterministe** de l'agent. Rapportee a cote de la mesure de
#: reference, **jamais a sa place** -- exactement le statut du greedy a departage deterministe
#: en phase 2. L'indice d'une action de pose encode l'assignation, la position au banquet et
#: l'adversaire vise, donc une preference stable pour l'action la plus probable peut fabriquer
#: un artefact dans B2, B3 et B6. Son ecart avec la reference est un chiffre, pas un doublon.
DECALAGE_VARIANTE_DETERMINISTE = 30_000


@dataclass(frozen=True)
class Mesure:
    """Ce qu'une composition rend : son verdict, son dimensionnement, ses comportements.

    Attributes:
        intitule: la composition, en toutes lettres. Jamais deduite du contexte.
        verdict: gain moyen, part fractionnee, part stricte, gains par siege.
        dimensionnement: `sigma`, `rho`, effet de plan **remesures sur cette composition**.
        comportements: les dix-sept compteurs, aux deux grains.
        nb_donnes: le nombre de donnes.
        nb_parties: le nombre de parties. `nb_donnes x 3`.
        campagne: les parties brutes.

    **La campagne brute est gardee**, et ce n'est pas un oubli de nettoyage : c'est le
    **support** de tout ce qui precede. Sans elle, « la somme des gains vaut-elle zero dans
    chaque partie ? » et « chaque siege est-il occupe une fois par donne ? » ne sont plus des
    questions verifiables -- il ne reste que des agregats qui se confirment eux-memes. La
    phase 2 liberait ses campagnes pour tenir en memoire ; a 6 000 parties ce n'est pas
    necessaire, et l'auditabilite vaut mieux.
    """

    intitule: str
    verdict: phase3.Verdict
    dimensionnement: phase3.Dimensionnement
    comportements: dict[str, comp.Compte]
    nb_donnes: int
    nb_parties: int
    campagne: phase3.Campagne


def groupes_pour_m4(campagne: phase3.Campagne) -> list[phase2.Groupe]:
    """Traduit une campagne de la phase 3 en `Groupe` de la phase 2, pour `mesurer_m4`.

    **Une traduction, pas une reimplementation.** Les compteurs de la phase 2 prennent des
    `Groupe`, et ce sont eux qu'il faut faire tourner : ils sont audites, et trois tours d'audit
    ont porte sur leurs denominateurs.

    Le seul point delicat est le **grain** : `Groupe.sieges_mesures` porte, pour chaque trace,
    le **tuple** des sieges comptes. Ma campagne compte **un** siege par partie, donc chaque
    trace donne `(siege,)` -- un tuple d'un element, pas l'entier. Un entier passerait
    silencieusement dans `tous_les_comportements` et compterait autre chose.
    """
    return [
        phase2.Groupe(
            seed=donne,
            traces=traces,
            sieges_mesures=tuple((siege,) for siege in sieges),
        )
        for donne, traces, sieges in zip(
            campagne.donnes, campagne.traces, campagne.sieges_mesures, strict=True
        )
    ]


def mesurer(
    agent: phase3.Fabrique,
    adversaire: phase3.Fabrique,
    donnes: int,
    intitule: str,
    depart: int,
    decalage_agent: int = phase3.DECALAGE_AGENT,
    decalage_adversaire: int = phase3.DECALAGE_DEPARTAGE,
) -> Mesure:
    """Joue une composition, la juge, la dimensionne et compte ses comportements.

    `sigma` et `rho` sont **remesures ici**, sur la composition reelle. Ceux de la
    pre-inscription sont mesures sous l'hypothese nulle et n'ont aucune raison de valoir sous
    un agent different : l'ecart entre le SUPPOSE et le MESURE doit etre un chiffre, pas un
    oubli.
    """
    campagne = phase3.jouer_composition(
        agent=agent,
        adversaire=adversaire,
        donnes=donnes,
        intitule=intitule,
        depart=depart,
        decalage_agent=decalage_agent,
        decalage_adversaire=decalage_adversaire,
    )
    comportements = phase2.mesurer_m4(groupes_pour_m4(campagne))
    comp.verifier_inclusion_b1(comportements)
    return Mesure(
        intitule=intitule,
        verdict=phase3.juger(campagne),
        dimensionnement=phase3.dimensionner(campagne),
        comportements=comportements,
        nb_donnes=len(campagne.donnes),
        nb_parties=campagne.nb_parties,
        campagne=campagne,
    )


def ligne_de_base_trois_greedys_un_siege(donnes: int) -> dict[str, comp.Compte]:
    """La troisieme population de la phase 2, **regeneree a UN seul siege compte**.

    **Memes seeds, meme composition, meme decalage de graine.** Seuls les sieges COMPTES
    changent : `campagne_b(nb_greedys=3)` mesure les trois, et cette fonction n'en compte qu'un
    par partie -- celui qui tourne, donc les trois sont couverts a parts egales sur une donne.

    C'est la ligne de base de ma composition au grain de ma composition, et il n'y en a pas
    d'autre dans le depot.

    Raises:
        ValueError: si l'inclusion `B1-collectif >= B1-motif` tombe, sur l'un des deux grains.
            La chute de cette inclusion a deja revele un compteur faux une fois.
    """
    groupes = phase2.campagne_b(donnes, nb_greedys=3)
    reduits = [
        phase2.Groupe(
            seed=groupe.seed,
            traces=groupe.traces,
            # `campagne_b(nb_greedys=3)` rend `(0, 1, 2)` pour chaque trace. On garde le siege
            # dont l'indice est celui du replicat : la trace 0 compte le siege 0, la trace 1 le
            # siege 1, la trace 2 le siege 2. Chaque siege est donc compte exactement une fois
            # par donne, comme dans la composition de la phase 3.
            sieges_mesures=tuple(
                (replicat,) for replicat in range(len(groupe.traces))
            ),
        )
        for groupe in groupes
    ]
    comptes = phase2.mesurer_m4(reduits)
    comp.verifier_inclusion_b1(comptes)
    return comptes


@dataclass(frozen=True)
class Comparaison:
    """Un compteur, chez l'agent et chez sa ligne de base, avec ce que l'ecart vaut.

    Attributes:
        nom: le compteur.
        agent: son compte chez l'agent.
        base: son compte chez la ligne de base, **au meme grain**.
        ecart: `taux(agent) - taux(base)`, ou `None` si l'un des deux n'a pas de taux.
        detectable: l'ecart de taux detectable au budget de la campagne.
        separable: vrai si `|ecart| > detectable`.
        exclu: la raison de l'exclusion, ou `None` si la ligne est comparee.
    """

    nom: str
    agent: comp.Compte
    base: comp.Compte
    ecart: float | None
    detectable: float | None
    separable: bool
    exclu: str | None


#: Les compteurs exclus **par le texte de leur definition**, quel que soit le budget. Le critere
#: est : la definition nomme-t-elle un autre joueur ? `B1-collectif` oui, ces deux-la non, et
#: leurs taux bougent sous une autre composition pour une raison qui n'est pas l'habilete.
EXCLUS_PAR_LE_TEXTE: tuple[str, ...] = ("B4-tout-dos", "B5-renfort")


def comparer(
    agent: dict[str, comp.Compte],
    base: dict[str, comp.Compte],
    nb_parties_agent: int,
    nb_parties_base: int,
    budget: int,
) -> list[Comparaison]:
    """Compare deux jeux de compteurs **au meme grain**, ligne a ligne.

    `comp.ecart_de_taux` **leve** si les grains different : elle est appelee plutot que
    contournee, et une ligne dont le grain differe fait donc tomber la mesure au lieu de
    produire un nombre qu'il faudrait relire.

    Les exclusions sont **calculees**, jamais recopiees : le marqueur de budget vient de
    `phase2.budget_d_un_compteur` au budget reel de la campagne, et l'exclusion textuelle vient
    de la liste nommee ci-dessus.

    Le denominateur par partie n'est PAS re-verifie ici, et c'est delibere
    -----------------------------------------------------------------------
    Une premiere version de ce module ajoutait sa propre garde : « une ligne `-par-partie` doit
    valoir 1,0 observation par partie ». **Elle etait redondante.**
    `phase2.observations_par_partie` porte deja exactement ce controle et **leve**, avec un
    message plus precis -- « son denominateur EST le nombre de parties, or il vaut N contre M
    parties ». C'est la parade que l'audit du tour 2 de la phase 2 a imposee, apres qu'un
    facteur trois indu eut survecu a deux verifications reussies.

    Ecrire une seconde garde pour la meme regle est exactement ce que le paragraphe 2 des
    conventions interdit : deux definitions finissent par ne plus etre d'accord, et c'est la
    plus recente qui a tort sans que rien ne le signale. `budget_d_un_compteur`, appele
    ci-dessous, passe par `observations_par_partie` : le controle s'exerce, a son site unique.
    """
    resultats: list[Comparaison] = []
    for nom in sorted(set(agent) & set(base)):
        compte_agent, compte_base = agent[nom], base[nom]
        budget_agent = phase2.budget_d_un_compteur(
            compte_agent, nb_parties_agent, None, budget=budget
        )
        exclu: str | None = None
        if nom in EXCLUS_PAR_LE_TEXTE:
            exclu = "texte de la definition : elle ne nomme aucun autre joueur"
        elif budget_agent.hors_budget:
            exclu = f"hors budget a {budget} parties"
        elif budget_agent.aveugle_par_le_bas:
            exclu = f"aveugle par le bas a {budget} parties"

        # `ecart_de_taux` LEVE si les grains different. On ne l'attrape pas : un grain qui
        # differe est un defaut a corriger, pas une cellule a remplir.
        ecart = comp.ecart_de_taux(compte_agent, compte_base)
        detectable = budget_agent.detectable
        separable = (
            exclu is None
            and ecart is not None
            and detectable is not None
            and abs(ecart) > detectable
        )
        resultats.append(
            Comparaison(
                nom=nom,
                agent=compte_agent,
                base=compte_base,
                ecart=ecart,
                detectable=detectable,
                separable=separable,
                exclu=exclu,
            )
        )
    return resultats


def politique_de_checkpoint(chemin: str) -> phase3.Fabrique:
    """Une fabrique de politique a partir d'un checkpoint, pour les mesures contre le pool."""
    from agents import entrainement
    from agents.politique_reseau import charger, politique_reseau
    from courtisans.engine import Engine
    from courtisans.infoset import tenseur

    etat = Engine(entrainement.CONFIG).reset(0)
    modele = charger(
        chemin,
        taille_observation=len(tenseur(etat, 0)),
        nb_actions=6 * 2 * (entrainement.CONFIG.joueurs - 1),
    )
    return lambda alea: politique_reseau(modele, alea)


# ---------------------------------------------------------------------------------
# Le pilote de la mesure finale
# ---------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Joue toutes les compositions, compare les comportements, ecrit le rapport.

    **L'ordre compte, et il est celui de la pre-inscription.** Le juge d'abord -- un agent
    contre deux greedys --, le pool ensuite, la ligne de base regeneree enfin. Aucun seuil
    n'est relu apres avoir vu un chiffre.

    Reproduire :

        UV_LINK_MODE=copy uv run python -m mesure.phase3_mesure --donnes 2000
    """
    import argparse
    import json
    import sys
    import time
    from pathlib import Path

    from mesure import rapport_phase3

    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--dossier", type=Path, default=Path("models/phase3"))
    analyseur.add_argument("--donnes", type=int, default=2000)
    analyseur.add_argument("--donnes-pool", type=int, default=500)
    analyseur.add_argument(
        "--sortie", type=Path, default=Path("mesure/resultats/phase3.md")
    )
    arguments = analyseur.parse_args(argv)

    reconfigurer = getattr(sys.stdout, "reconfigure", None)
    if reconfigurer is not None:
        reconfigurer(encoding="utf-8")

    final = arguments.dossier / "final.pt"
    if not final.exists():
        raise SystemExit(
            f"aucun agent entraine en {final} : lancer `agents.campagne` d'abord. "
            f"Mesurer un reseau non entraine rendrait un chiffre juste sur une population "
            f"qui n'est pas celle que la phase 3 annonce."
        )
    agent = politique_de_checkpoint(str(final))

    durees: list[tuple[str, float]] = []

    def chronometre(nom: str, action):  # noqa: ANN001, ANN202
        debut = time.perf_counter()
        resultat = action()
        durees.append((nom, time.perf_counter() - debut))
        print(f"  {nom} : {durees[-1][1]:.1f} s", flush=True)
        return resultat

    print("# Mesure de la phase 3", flush=True)

    # --- 1. Le juge, et lui seul -------------------------------------------------------
    contre_greedys = chronometre(
        "1 agent contre 2 greedys",
        lambda: mesurer(
            agent=agent,
            adversaire=phase3.greedy_de_reference,
            donnes=arguments.donnes,
            intitule="1 agent entraine contre 2 greedys, sieges permutes",
            depart=DEPART_CAMPAGNE_FINALE,
        ),
    )

    # --- 2. Le pool, chaque composition nommee -----------------------------------------
    pool: list[Mesure] = [contre_greedys]
    pool.append(
        chronometre(
            "1 agent contre 2 aleatoires",
            lambda: mesurer(
                agent=agent,
                adversaire=phase3.uniforme,
                donnes=arguments.donnes_pool,
                intitule="1 agent entraine contre 2 aleatoires (garde-fou)",
                depart=DEPART_CAMPAGNE_FINALE + DECALAGE_POOL_ALEATOIRE,
                decalage_adversaire=phase3.DECALAGE_UNIFORME,
            ),
        )
    )
    from agents.politique_reseau import charger, politique_reseau_deterministe
    from courtisans.engine import Engine
    from courtisans.infoset import tenseur

    etat_zero = Engine(phase3.CONFIG).reset(0)
    modele_final = charger(
        str(final),
        taille_observation=len(tenseur(etat_zero, 0)),
        nb_actions=6 * 2 * (phase3.CONFIG.joueurs - 1),
    )
    pool.append(
        chronometre(
            "1 agent DETERMINISTE contre 2 greedys",
            lambda: mesurer(
                agent=lambda _alea: politique_reseau_deterministe(modele_final),
                adversaire=phase3.greedy_de_reference,
                donnes=arguments.donnes,
                intitule=(
                    "1 agent entraine, variante DETERMINISTE, contre 2 greedys "
                    "(robustesse -- jamais a la place de la reference)"
                ),
                depart=DEPART_CAMPAGNE_FINALE + DECALAGE_VARIANTE_DETERMINISTE,
            ),
        )
    )

    checkpoints = sorted(arguments.dossier.glob("checkpoint_*.pt"))
    for indice, chemin in enumerate(checkpoints):
        fige = politique_de_checkpoint(str(chemin))
        pool.append(
            chronometre(
                f"1 agent contre 2 x {chemin.name}",
                lambda fige=fige, chemin=chemin, indice=indice: mesurer(
                    agent=agent,
                    adversaire=fige,
                    donnes=arguments.donnes_pool,
                    intitule=f"1 agent entraine contre 2 copies de `{chemin.name}`",
                    depart=(
                        DEPART_CAMPAGNE_FINALE
                        + DECALAGE_POOL_CHECKPOINTS
                        + PAS_ENTRE_CHECKPOINTS * indice
                    ),
                ),
            )
        )

    # --- 3. La ligne de base regeneree, a UN seul siege compte -------------------------
    base = chronometre(
        "ligne de base : 3 greedys, 1 siege compte",
        lambda: ligne_de_base_trois_greedys_un_siege(arguments.donnes),
    )
    comparaisons = comparer(
        contre_greedys.comportements,
        base,
        nb_parties_agent=contre_greedys.nb_parties,
        nb_parties_base=arguments.donnes * phase3.CONFIG.joueurs,
        budget=contre_greedys.nb_parties,
    )

    # --- 4. Le journal du run ----------------------------------------------------------
    journal = arguments.dossier / "journal.jsonl"
    jalons = (
        [json.loads(x) for x in journal.read_text(encoding="utf-8").splitlines() if x]
        if journal.exists()
        else []
    )

    # --- 5. L'audit, joue SUR le resultat mais ecrit AVANT lui ------------------------
    from mesure import phase3_audit

    controles = chronometre(
        "auto-audit",
        lambda: phase3_audit.auditer(
            mesure=contre_greedys,
            campagne=contre_greedys.campagne,
            pool=pool,
            comparaisons=comparaisons,
            base=base,
            nb_parties_base=arguments.donnes * phase3.CONFIG.joueurs,
            donnes_calibration=arguments.donnes,
            donnes_pool=arguments.donnes_pool,
            nb_checkpoints=len(checkpoints),
            parties_entrainement=(jalons[-1]["parties"] if jalons else 0),
        ),
    )
    for controle in controles:
        if not controle.passe:
            print(f"  !! CONTROLE EN ECHEC -- {controle.code} {controle.intitule}", flush=True)

    # --- 6. Les durees, ACCUMULEES sur les passes ------------------------------------
    #
    # Le paragraphe 0.2 exige au moins TROIS passes avec leur etendue. Une passe unique ne se
    # cite pas -- c'est le cinquieme defaut mineur que j'ai releve dans le rapport de la
    # phase 2, et le repeter dans le mien serait la faute que ce projet nomme le plus souvent :
    # la correction est le lieu du defaut suivant.
    #
    # Chaque passe ajoute une ligne au journal des durees ; le rapport lit **toutes** les
    # lignes et publie l'etendue. Trois lancements de cette commande suffisent donc, sans
    # qu'aucun chiffre ne soit recopie a la main.
    chemin_durees = arguments.dossier / "durees.jsonl"
    with chemin_durees.open("a", encoding="utf-8") as fichier:
        fichier.write(json.dumps(dict(durees), ensure_ascii=False) + "\n")
    passes = [
        json.loads(x)
        for x in chemin_durees.read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]

    texte = rapport_phase3.rapport(contre_greedys, pool, comparaisons, jalons, controles)
    texte += rapport_phase3.section_durees(passes)
    rapport_phase3.ecrire(texte, arguments.sortie)
    print(f"# Rapport ecrit en {arguments.sortie}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DECALAGE_POOL_ALEATOIRE",
    "DECALAGE_POOL_CHECKPOINTS",
    "DECALAGE_VARIANTE_DETERMINISTE",
    "DEPART_CAMPAGNE_FINALE",
    "PAS_ENTRE_CHECKPOINTS",
    "EXCLUS_PAR_LE_TEXTE",
    "Comparaison",
    "Mesure",
    "comparer",
    "groupes_pour_m4",
    "ligne_de_base_trois_greedys_un_siege",
    "main",
    "mesurer",
    "politique_de_checkpoint",
]
