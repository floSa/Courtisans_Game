"""Les controles hostiles de l'auditeur de la phase 1.

Un controle hostile sur une phase de mesure ne verifie pas qu'un chiffre est joli : il
cherche a le faire mentir. Les quatre familles annoncees avant d'ouvrir le travail du
constructeur :

  - **H1** -- parties construites par l'auditeur, resultat calcule de tete, avec deux
    negatifs : un meurtre en **domaine** ne doit rien changer au statut, et une famille
    jamais posee au banquet reste Indifferente ;
  - **H2** -- stabilite au seed : plusieurs blocs de 1 000 parties, l'ecart est publie ;
  - **H3** -- controles negatifs : sans Assassin, aucun retournement cause par un meurtre
    et aucun noeud de ciblage ; sans Noble, **aucune inversion** en un seul evenement ;
  - **H4** -- non-vacuite : la situation mesuree s'est-elle produite, et combien de fois.

Plus **H5**, ajoute par la consigne d'audit : le retournement invisible des trois sieges,
construit a la main.
"""

from __future__ import annotations

import pytest

from audit.construction import carte, pioche_avec_debut, politique_scriptee
from audit.mesure import INSTANCE_PHASE_1, joue_campagne
from audit.retournement import ANNULATION, INVERSION, rejoue
from audit.statut import (
    INDIFFERENTE,
    LUMIERE,
    OBSCURITE,
    influence_par_famille,
    statuts_par_famille,
)
from courtisans.cards import Position, Role
from courtisans.config import GameConfig
from courtisans.engine import Engine

E, D = Position.ESTIME, Position.DISGRACE
ASSASSIN, GARDE, NOBLE, ESPION, NEUTRE = (
    Role.ASSASSIN,
    Role.GARDE,
    Role.NOBLE,
    Role.ESPION,
    Role.NEUTRE,
)


# =================================================================================
# H1 -- trois parties construites par l'auditeur, attendu calcule de tete
# =================================================================================


def test_h1a_trajectoire_complete_dune_famille():
    """Une famille traverse les cinq transitions possibles ; j'ai compte 2 retournements.

    Sequence imposee au banquet sur la famille 0, et ce que j'ai calcule de tete :

    | # | carte posee            | `d`      | transition                  | retournement |
    |---|------------------------|----------|-----------------------------|--------------|
    | 1 | Noble f0 en Estime     | 0 -> +2  | Indifferente -> Lumiere     | non (etabl.) |
    | 2 | Neutre f0 en Disgrace  | +2 -> +1 | Lumiere -> Lumiere          | aucune       |
    | 3 | Neutre f0 en Disgrace  | +1 -> 0  | Lumiere -> **Indifferente** | **oui**      |
    | 4 | Garde f0 en Disgrace   | 0 -> -1  | Indifferente -> Obscurite   | non (etabl.) |
    | 5 | Noble f0 en Estime     | -1 -> +1 | Obscurite -> **Lumiere**    | **oui**      |

    Total attendu : **2 retournements** (1 annulation, 1 inversion) et 2 etablissements.
    Aucune carte de la famille 0 n'est cachee, donc les trois sieges voient la meme chose
    et **aucun** retournement n'est invisible.

    La famille 1 fournit le second negatif : ses **dix** cartes sont posees, toutes dans
    des domaines, aucune au banquet. Son `d` doit rester nul du premier au dernier
    evenement -- une carte de domaine ne change pas le statut de sa famille.
    """
    mains = [
        # J0 t1 : etablit la Lumiere sur f0
        [carte(0, NOBLE, 0), carte(1, NEUTRE, 0), carte(1, NEUTRE, 1)],
        # J1 t1 : entame la marge sans franchir de seuil
        [carte(0, NEUTRE, 0), carte(1, GARDE, 0), carte(1, GARDE, 1)],
        # J2 t1 : ANNULATION
        [carte(0, NEUTRE, 1), carte(1, ESPION, 0), carte(1, ESPION, 1)],
        # J0 t2 : etablit l'Obscurite
        [carte(0, GARDE, 0), carte(1, NOBLE, 0), carte(1, NOBLE, 1)],
        # J1 t2 : INVERSION
        [carte(0, NOBLE, 1), carte(1, ASSASSIN, 0), carte(1, ASSASSIN, 1)],
        # J2 t2 .. J2 t4 : plus une seule carte de f0 ni de f1 au banquet
        [carte(0, ASSASSIN, 0), carte(2, NEUTRE, 0), carte(2, NEUTRE, 1)],
        [carte(0, ASSASSIN, 1), carte(3, NEUTRE, 0), carte(3, NEUTRE, 1)],
        [carte(0, GARDE, 1), carte(2, GARDE, 0), carte(2, GARDE, 1)],
        [carte(0, ESPION, 0), carte(3, GARDE, 0), carte(3, GARDE, 1)],
        [carte(0, ESPION, 1), carte(2, NOBLE, 0), carte(2, NOBLE, 1)],
        [carte(3, NOBLE, 0), carte(3, NOBLE, 1), carte(2, ESPION, 0)],
        [carte(2, ESPION, 1), carte(3, ESPION, 0), carte(3, ESPION, 1)],
    ]
    script = [
        (carte(0, NOBLE, 0), E),
        (carte(0, NEUTRE, 0), D),
        (carte(0, NEUTRE, 1), D),
        (carte(0, GARDE, 0), D),
        (carte(0, NOBLE, 1), E),
        (carte(2, NEUTRE, 0), E),
        (carte(3, NEUTRE, 0), E),
        (carte(2, GARDE, 0), E),
        (carte(3, GARDE, 0), E),
        (carte(2, NOBLE, 0), E),
        (carte(3, NOBLE, 0), E),
        (carte(2, ESPION, 1), E),
    ]
    engine = Engine(INSTANCE_PHASE_1)
    pioche = pioche_avec_debut(INSTANCE_PHASE_1, [c for main in mains for c in main])
    partie = rejoue(engine, pioche, politique_scriptee(script))

    f0 = [t for t in partie.transitions if t.grain is None and t.famille == 0]
    assert [(t.d_avant, t.d_apres, t.classe) for t in f0] == [
        (0, 2, "etablissement"),
        (1, 0, ANNULATION),
        (0, -1, "etablissement"),
        (-1, 1, INVERSION),
    ], [str(t) for t in f0]

    retournements = [t for t in partie.retournements(None) if t.famille == 0]
    assert len(retournements) == 2
    assert [t.classe for t in retournements] == [ANNULATION, INVERSION]

    # Les trois sieges voient exactement la meme trajectoire : rien n'est cache sur f0.
    for siege in range(3):
        vue = [t for t in partie.transitions if t.grain == siege and t.famille == 0]
        assert [(t.d_avant, t.d_apres, t.classe) for t in vue] == [
            (t.d_avant, t.d_apres, t.classe) for t in f0
        ]
    assert partie.retournements_invisibles(3) == []

    # Negatif : la famille 1 n'a jamais de carte au banquet, malgre dix cartes posees.
    assert [str(t) for t in partie.transitions if t.famille == 1] == []


def test_h1b_un_meurtre_en_domaine_ne_change_aucun_statut():
    """Negatif : tuer une carte d'un **domaine** ne bouge pas `d`, meme a un cran du seuil.

    Construction : f0 a un Neutre en **Disgrace** au banquet (`d = -1`, Obscurite) et un
    **Noble** f0 dans le domaine de J0. Si un compteur incluait a tort les cartes de
    domaine du cote favorable, il lirait `d = +2 - 1 = +1`, donc Lumiere. Le tuer ferait
    alors passer `+1 -> -1` : une **inversion** qui n'existe pas.

    Attendu, calcule de tete : `d(f0) = -1` avant comme apres le meurtre, statut Obscurite,
    **zero transition** a cet evenement, dans les quatre grains.
    """
    mains = [
        # J0 t1 : Neutre f0 en Disgrace au banquet, Noble f0 dans SON domaine
        [carte(0, NEUTRE, 0), carte(0, NOBLE, 0), carte(2, NEUTRE, 0)],
        [carte(1, NEUTRE, 0), carte(1, NEUTRE, 1), carte(1, GARDE, 0)],
        [carte(2, NEUTRE, 1), carte(2, GARDE, 0), carte(2, GARDE, 1)],
        # J0 t2 : Assassin dans SON domaine -> il peut tuer le Noble f0 qui y est
        [carte(3, NEUTRE, 0), carte(1, ASSASSIN, 0), carte(3, NEUTRE, 1)],
    ]
    script = [
        (carte(0, NEUTRE, 0), D, carte(0, NOBLE, 0), carte(2, NEUTRE, 0)),
        (carte(1, NEUTRE, 0), E),
        (carte(2, NEUTRE, 1), E),
        (carte(3, NEUTRE, 0), E, carte(1, ASSASSIN, 0), carte(3, NEUTRE, 1)),
    ]
    engine = Engine(INSTANCE_PHASE_1)
    pioche = pioche_avec_debut(INSTANCE_PHASE_1, [c for main in mains for c in main])
    partie = rejoue(
        engine,
        pioche,
        politique_scriptee(script, cible_a_tuer={1: carte(0, NOBLE, 0)}),
    )

    assert partie.meurtres == 1, "un seul meurtre doit avoir lieu, et il est en domaine"
    # Ce meurtre-la ne peut avoir cause **aucune** transition, dans aucun grain.
    assert [str(t) for t in partie.transitions if t.cause == "meurtre"] == []

    # Et le meurtre s'est bien produit alors que f0 etait a **un cran** du seuil : c'est ce
    # qui rend le negatif mordant. Rejeu explicite pour lire `d` de part et d'autre.
    etat = engine.reset_depuis_pioche(pioche)
    politique = politique_scriptee(script, cible_a_tuer={1: carte(0, NOBLE, 0)})
    d_avant = d_apres = None
    while not etat.is_terminal():
        action = politique(etat)
        tue = (
            etat.phase().name == "CIBLAGE"
            and action < len(etat.cibles_courantes())
            and etat.cibles_courantes()[action].carte == carte(0, NOBLE, 0)
        )
        if tue:
            d_avant = influence_par_famille(etat.vue_privilegiee().posees, 4)[0]
        etat.apply(action)
        if tue:
            d_apres = influence_par_famille(etat.vue_privilegiee().posees, 4)[0]
            break
    assert (d_avant, d_apres) == (-1, -1), f"d(f0) {d_avant} -> {d_apres}"


def test_h1c_un_meurtre_au_banquet_est_bien_un_levier_de_retournement():
    """Un meurtre **au banquet** est, lui, un levier de retournement (paragraphe 2.2).

    Construction : Noble f0 en Estime (`d(f0) = +2`, Lumiere), puis un Assassin **de la
    famille 1** pose en Estime tue ce Noble.

    *Mon premier attendu etait faux, et je le laisse ecrit.* J'avais calcule `+2 -> +1`, en
    comptant l'Assassin dans `d(f0)` -- il est de famille 1, il ne compte que dans `d(f1)`.
    Le bon calcul est `d(f0) = +2 -> 0` : Lumiere -> Indifferente, une **annulation** de
    cause `meurtre`. Tuer un Noble en Estime fait varier `d` de -2, exactement ce que dit
    le paragraphe 2.2. L'erreur etait dans ma tete, pas dans le compteur.
    """
    mains = [
        [carte(0, NOBLE, 0), carte(1, NEUTRE, 0), carte(2, NEUTRE, 0)],
        [carte(1, ASSASSIN, 0), carte(1, NEUTRE, 1), carte(1, GARDE, 0)],
    ]
    script = [
        (carte(0, NOBLE, 0), E),
        (carte(1, ASSASSIN, 0), E),
    ]
    engine = Engine(INSTANCE_PHASE_1)
    pioche = pioche_avec_debut(INSTANCE_PHASE_1, [c for main in mains for c in main])
    partie = rejoue(
        engine, pioche, politique_scriptee(script, cible_a_tuer={1: carte(0, NOBLE, 0)})
    )
    assert partie.meurtres >= 1
    f0_debut = [
        t
        for t in partie.transitions
        if t.grain is None and t.famille == 0 and t.evenement <= 3
    ]
    assert [(t.d_avant, t.d_apres, t.classe, t.cause) for t in f0_debut] == [
        (0, 2, "etablissement", "pose"),
        (2, 0, ANNULATION, "meurtre"),
    ], [str(t) for t in f0_debut]


# =================================================================================
# H5 -- le retournement invisible des trois sieges, construit a la main
# =================================================================================


def test_h5_retournement_invisible_des_trois_sieges():
    """Un retournement **reel** qu'aucun des trois joueurs ne peut voir comme tel.

    Construction, avec deux Espions de la meme famille poses par deux joueurs differents :

      - J0 t1 : une carte de f1 au banquet -- f0 n'a rien de visible au banquet ;
      - J1 t1 : **Espion f0 en Estime**, face cachee. Vrai `d(f0) = +1` (Lumiere), seul J1
        le sait ;
      - J2 t1 : une carte de f2 au banquet ;
      - J0 t2 : **Espion f0 en Disgrace**, face cachee. C'est l'evenement.

    Ce que chacun calcule, verifie ci-dessous chiffre par chiffre :

    | grain  | `d(f0)` avant | apres | transition                | retournement |
    |--------|---------------|-------|---------------------------|--------------|
    | verite | +1            | 0     | Lumiere -> Indifferente   | **OUI**      |
    | J0     | 0             | -1    | Indifferente -> Obscurite | non (etabl.) |
    | J1     | +1            | +1    | aucune                    | non          |
    | J2     | 0             | 0     | aucune                    | non          |
    """
    mains = [
        [carte(1, NEUTRE, 0), carte(2, NEUTRE, 0), carte(3, NEUTRE, 0)],
        [carte(0, ESPION, 0), carte(1, GARDE, 0), carte(2, GARDE, 0)],
        [carte(2, NEUTRE, 1), carte(3, NEUTRE, 1), carte(1, NEUTRE, 1)],
        [carte(0, ESPION, 1), carte(3, GARDE, 0), carte(3, GARDE, 1)],
    ]
    script = [
        (carte(1, NEUTRE, 0), E),
        (carte(0, ESPION, 0), E),
        (carte(2, NEUTRE, 1), E),
        (carte(0, ESPION, 1), D),
    ]
    engine = Engine(INSTANCE_PHASE_1)
    pioche = pioche_avec_debut(INSTANCE_PHASE_1, [c for main in mains for c in main])
    partie = rejoue(engine, pioche, politique_scriptee(script))

    invisibles = partie.retournements_invisibles(3)
    assert len(invisibles) >= 1, "le cas construit n'a produit aucun retournement invisible"
    cible = next(t for t in invisibles if t.famille == 0)
    assert (cible.d_avant, cible.d_apres) == (1, 0)
    assert (cible.statut_avant, cible.statut_apres) == (LUMIERE, INDIFFERENTE)
    assert cible.classe == ANNULATION

    # Et aucun des trois sieges ne compte de retournement sur f0 a cet evenement.
    for siege in range(3):
        vus = [
            t
            for t in partie.retournements(siege)
            if t.famille == 0 and t.evenement == cible.evenement
        ]
        assert vus == [], f"J{siege} voit {[str(t) for t in vus]}"


# =================================================================================
# H3 -- controles negatifs : la mesure bouge-t-elle dans le sens attendu ?
# =================================================================================

#: Sans Assassin : 4 familles x 4 roles x 2 exemplaires = 32 cartes, 3 tours par joueur.
SANS_ASSASSIN = GameConfig(
    familles=4, roles=(GARDE, NOBLE, ESPION, NEUTRE), exemplaires=2, joueurs=3
)

#: Sans Noble : toutes les cartes pesent 1, donc `d` ne bouge jamais que de 1.
SANS_NOBLE = GameConfig(
    familles=4, roles=(ASSASSIN, GARDE, ESPION, NEUTRE), exemplaires=2, joueurs=3
)


def test_h3a_sans_assassin_aucun_noeud_de_ciblage_ni_meurtre():
    """Contro1e negatif exact : retirer l'Assassin fait tomber a **zero** ce qui en depend.

    Trois zeros, tous exacts et non statistiques : aucun noeud de ciblage, aucun meurtre,
    et **aucun retournement de cause `meurtre`**. Le troisieme est celui qui compte : il
    prouve que mon compteur attribue bien les retournements a leur levier.
    """
    campagne = joue_campagne(SANS_ASSASSIN, range(0, 300))
    assert campagne.noeuds_de_ciblage() == 0
    assert campagne.meurtres() == 0
    assert campagne.noeuds_avec_cible() == 0
    par_meurtre = [
        t
        for p in campagne.parties
        for t in p.retournements(None)
        if t.cause == "meurtre"
    ]
    assert par_meurtre == []
    # Et la mesure reste non vide : des retournements par pose subsistent.
    assert campagne.retournements_totaux(None) > 0


def test_h3b_sans_noble_aucune_inversion_en_un_seul_evenement():
    """Controle negatif exact : sans Noble, `d` ne bouge que de 1, donc **zero inversion**.

    Le paragraphe 2.2 est explicite : « Un Noble peut donc inverser une famille a lui seul
    [...] Une carte standard ne peut jamais qu'annuler. » Franchir Lumiere -> Obscurite
    demande de traverser `d = 0`, donc deux evenements. Un compteur qui trouverait une
    inversion ici mesurerait autre chose que ce que sa phrase dit.
    """
    campagne = joue_campagne(SANS_NOBLE, range(0, 300))
    assert campagne.par_classe(None)[INVERSION] == 0
    for siege in range(3):
        assert campagne.par_classe(siege)[INVERSION] == 0
    # Non-vacuite : les annulations, elles, existent bel et bien.
    assert campagne.par_classe(None)[ANNULATION] > 0


def test_h3c_avec_noble_les_inversions_existent():
    """Le pendant positif de H3b : sur l'instance de la phase 1, il y a des inversions.

    Sans ce test, H3b passerait aussi sur un compteur qui ne saurait pas compter les
    inversions du tout.
    """
    campagne = joue_campagne(INSTANCE_PHASE_1, range(0, 300))
    assert campagne.par_classe(None)[INVERSION] > 0


# =================================================================================
# H4 -- non-vacuite : la situation mesuree s'est-elle produite ?
# =================================================================================


def test_h4_non_vacuite_des_quatre_denominateurs():
    """Chaque taux du rapport a un denominateur non nul, et je le nomme.

    Un taux dont le denominateur est vide ou minuscule est un faux chiffre. Les quatre
    situations mesurees doivent s'etre reellement produites.
    """
    campagne = joue_campagne(INSTANCE_PHASE_1, range(0, 300))
    assert campagne.n == 300
    # D1 : chaque partie a bien 3 x 4 = 12 poses.
    assert campagne.tours_par_joueur() == {(4, 4, 4): 300}
    # D2 : les scores existent, 3 par partie.
    assert len(campagne.scores_a_plat()) == 900
    # D3 : des retournements ET des etablissements se sont produits -- si les
    # etablissements etaient nuls, la mesure porterait sur un jeu sans banquet.
    assert campagne.retournements_totaux(None) > 0
    assert campagne.etablissements(None) > 0
    # D4 : des noeuds de ciblage se sont produits, dont certains avec cible.
    assert campagne.noeuds_de_ciblage() > 0
    assert campagne.noeuds_avec_cible() > 0
    assert campagne.meurtres() > 0 and campagne.refus() > 0


def test_h4b_linstance_a_20_cartes_est_refusee_a_la_construction():
    """L'arbitrage « 20 cartes ou 40 » du paragraphe 3 de 05 n'est pas un arbitrage.

    `floor(20 / 9) = 2` tours, sous le plancher de 3 du paragraphe 8 des regles. La
    configuration doit **lever**, pas etre deconseillee.
    """
    with pytest.raises(ValueError, match="au moins 3 tours"):
        GameConfig(
            familles=4,
            roles=(ASSASSIN, GARDE, NOBLE, ESPION, NEUTRE),
            exemplaires=1,
            joueurs=3,
        )


# =================================================================================
# Coherence de mon propre instrument avec le moteur, sur ce qui est commun
# =================================================================================


def test_mes_statuts_et_mes_points_concordent_avec_le_moteur():
    """Mon calcul de statut et le sien doivent tomber d'accord sur 300 parties.

    C'est le seul test de ce fichier qui appelle `rules` : il ne sert pas a definir mon
    attendu -- il est ecrit ailleurs, depuis le texte -- mais a localiser un desaccord. Un
    ecart ici voudrait dire qu'une des deux lectures du paragraphe 2.2 est fausse, et le
    reste des controles dirait laquelle.
    """
    from courtisans import rules

    engine = Engine(INSTANCE_PHASE_1)
    comparaisons = 0
    for seed in range(1000):
        etat = engine.reset_depuis_pioche(engine.pioche_depuis_seed(seed))
        from audit.retournement import politique_aleatoire

        politique = politique_aleatoire(seed + 10**9)
        while not etat.is_terminal():
            etat.apply(politique(etat))
        vivantes = etat.vue_privilegiee().posees
        miens = statuts_par_famille(vivantes, INSTANCE_PHASE_1.familles)
        siens = rules.statuts(vivantes, INSTANCE_PHASE_1.familles)
        assert miens == {f: int(s) for f, s in siens.items()}, f"seed {seed}"
        mes_d = influence_par_famille(vivantes, INSTANCE_PHASE_1.familles)
        assert mes_d == rules.influence(vivantes, INSTANCE_PHASE_1.familles), f"seed {seed}"
        from audit.statut import points_par_joueur

        mes_points = points_par_joueur(
            vivantes, INSTANCE_PHASE_1.familles, INSTANCE_PHASE_1.joueurs
        )
        assert mes_points == list(etat.scores().values()), f"seed {seed}"
        comparaisons += 2 * INSTANCE_PHASE_1.familles + INSTANCE_PHASE_1.joueurs
    # 1000 parties x (4 statuts + 4 influences + 3 scores) = 11 000 comparaisons.
    assert comparaisons == 11_000


def test_les_seuils_de_statut_sont_ceux_du_texte():
    """Les trois seuils, un par un, sur les valeurs limites."""
    from audit.statut import statut_de

    assert statut_de(1) == LUMIERE
    assert statut_de(2) == LUMIERE
    assert statut_de(0) == INDIFFERENTE
    assert statut_de(-1) == OBSCURITE
    assert statut_de(-2) == OBSCURITE
