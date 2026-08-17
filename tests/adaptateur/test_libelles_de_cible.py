"""Les libelles de ciblage ne nomment jamais une carte que personne ne voit.

Ecrit d'apres `documentations/01_regles.md`, paragraphes 2.6, 4.1 et 4.2, et l'arbitrage
du 17/08. Aucun de ces tests ne lit le libelle produit par le code pour en deduire son
attendu : la forme est transcrite ici depuis l'arbitrage, comme le paragraphe 1 des
conventions l'exige.

Ce que l'arbitrage tranche
--------------------------
Un libelle de cible dit **ce que la carte est** et **laquelle c'est**, sans jamais reveler
ce que le joueur ignore :

  - carte **visible** -- on nomme tout, famille et role compris ;
  - carte **cachee**  -- on ne nomme ni la famille ni le role. On dit que c'est un dos, et
    on le situe.

Trois raisons de ne pas s'en remettre a l'invariant I7
------------------------------------------------------
I7 ne surveille que `information_state_string` (paragraphe 5 de la specification), pas
`action_to_string`. Un libelle qui nomme un Espion adverse ne fait donc echouer aucun test
existant, ne fausse aucun coup, et ne se voit dans aucune metrique -- il ne mord qu'en aval,
dans une interface, une trace consommee par un agent, ou un journal d'entrainement.

La contrainte qui interdit la solution paresseuse
-------------------------------------------------
**Deux actions legales distinctes doivent porter deux libelles distincts** : OpenSpiel
l'exige et son harnais `random_sim_test` le verifie. Effacer l'identite d'un dos sans rien
mettre a la place rendrait deux dos d'une meme zone indistinguables, ce qui rouvrirait le
defaut 7 de l'audit de la phase 0. C'est ce que l'ordinal apporte, et c'est pourquoi il est
teste ici sur les dos **comme** sur les cartes visibles : deux exemplaires du meme couple
(famille, role) dans une meme zone sont deux cibles distinctes que la seule apparence ne
separe pas.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    NB_PARTIES_BALAYAGE,
    RAPIDE_3J,
    Instance,
    cle,
    construire_config,
    module,
    noms,
    paquet_ordonne,
    parcourir_decisions,
)

# ---------------------------------------------------------------------------------
# Les regles, transcrites -- jamais demandees au moteur
# ---------------------------------------------------------------------------------

#: 01_regles.md paragraphe 4.2 : seul l'Espion est pose face cachee.
ROLES_CACHES_SELON_LES_REGLES: frozenset[str] = frozenset({"ESPION"})

#: 01_regles.md paragraphe 4.3 : le Garde est immunise, il n'est jamais une cible.
ROLES_IMMUNISES_SELON_LES_REGLES: frozenset[str] = frozenset({"GARDE"})

#: Ce qu'un libelle doit dire d'un dos, a la place de son identite (arbitrage du 17/08).
APPARENCE_DU_DOS = "dos"


def _apparence_publique(posee) -> str:  # noqa: ANN001 - le type vit dans le moteur
    """Ce que **tout le monde** voit de cette carte posee, en une chaine.

    C'est la seule chose qu'un libelle a le droit de nommer.
    """
    if posee.carte.role.name in ROLES_CACHES_SELON_LES_REGLES:
        return APPARENCE_DU_DOS
    return f"f{posee.carte.famille}-{posee.carte.role.name}"


def _ordinal(rang: int) -> str:
    """L'ordinal francais du rang, compte a partir de 1."""
    return "1er" if rang == 1 else f"{rang}e"


def _zone_en_clair(zone) -> str:  # noqa: ANN001
    """La zone d'une carte, telle que l'arbitrage demande de la situer."""
    if zone.genre.name == "BANQUET":
        return f"en {zone.position.name}"
    return f"dans le domaine de J{zone.proprietaire}"


def _libelle_attendu(etat, cible) -> str:  # noqa: ANN001
    """Le libelle qu'une cible doit porter, recalcule ici depuis l'arbitrage.

    Le rang se compte sur les cartes **encore en jeu** dans la zone qui partagent la meme
    apparence publique -- ce qu'un joueur humain compte sur la table, pas l'ordre
    historique des poses.
    """
    apparence = _apparence_publique(cible)
    memes = [
        posee
        for posee in etat.vue_privilegiee().posees
        if posee.zone == cible.zone and _apparence_publique(posee) == apparence
    ]
    rang = 1 + next(
        indice for indice, posee in enumerate(memes) if cle(posee.carte) == cle(cible.carte)
    )
    return f"tuer le {_ordinal(rang)} {apparence} {_zone_en_clair(cible.zone)}"


# ---------------------------------------------------------------------------------
# Acces au jeu et lecture des libelles
# ---------------------------------------------------------------------------------


def _jeu(instance: Instance):  # noqa: ANN202 - le type vit dans l'adaptateur
    return module("openspiel_adapter").CourtisansGame(config=construire_config(instance))


def _libelles(etat) -> list[str]:  # noqa: ANN001
    """Les libelles des actions legales, dans l'ordre croissant des actions."""
    joueur = etat.current_player()
    return [etat.action_to_string(joueur, action) for action in sorted(etat.legal_actions())]


def _libelle_de_cible(etat, indice: int) -> str:  # noqa: ANN001
    return etat.action_to_string(etat.current_player(), indice)


def _noeuds_de_ciblage(instance: Instance, nb_parties: int):  # noqa: ANN202
    """Les etats de la phase CIBLAGE rencontres sur un balayage de vraies parties."""
    for _seed, etat in parcourir_decisions(_jeu(instance), nb_parties):
        if etat.phase().name == "CIBLAGE":
            yield etat


# ---------------------------------------------------------------------------------
# 1. Une cible cachee n'est ni nommee, ni deductible du libelle
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_le_libelle_d_une_cible_cachee_ne_nomme_ni_sa_famille_ni_son_role(
    instance: Instance,
) -> None:
    """01_regles.md paragraphe 2.6 : de l'Espion d'un autre, on ne voit qu'un dos.

    Le joueur qui choisit la cible ignore son identite ; le libelle ne doit donc contenir
    ni son role, ni sa famille. Le compteur d'occurrences interdit le vert par vacuite :
    un balayage qui ne croiserait aucune cible cachee ne prouverait rien.
    """
    caches_vus = 0

    for etat in _noeuds_de_ciblage(instance, NB_PARTIES_BALAYAGE):
        for indice, cible in enumerate(etat.cibles_courantes()):
            if cible.carte.role.name not in ROLES_CACHES_SELON_LES_REGLES:
                continue
            caches_vus += 1
            libelle = _libelle_de_cible(etat, indice)
            assert cible.carte.role.name not in libelle, (
                f"{instance.nom} : le libelle {libelle!r} nomme le role d'une carte posee "
                f"face cachee"
            )
            assert f"f{cible.carte.famille}" not in libelle, (
                f"{instance.nom} : le libelle {libelle!r} nomme la famille "
                f"{cible.carte.famille} d'une carte posee face cachee"
            )
            assert APPARENCE_DU_DOS in libelle, (
                f"{instance.nom} : le libelle {libelle!r} ne dit pas que la cible est un dos"
            )

    assert caches_vus > 0, (
        f"{instance.nom} : aucune cible cachee sur {NB_PARTIES_BALAYAGE} parties, le test "
        f"ne prouve rien"
    )


# ---------------------------------------------------------------------------------
# 2. Une cible visible est nommee, elle
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_le_libelle_d_une_cible_visible_nomme_sa_famille_et_son_role(
    instance: Instance,
) -> None:
    """01_regles.md paragraphe 2.6 : les faces visibles sont publiques, tout est nommable.

    Le pendant du test precedent, et son garde-fou : un correctif qui se contenterait de
    tout anonymiser passerait le premier test et echouerait ici.
    """
    visibles_vues = 0

    for etat in _noeuds_de_ciblage(instance, NB_PARTIES_BALAYAGE):
        for indice, cible in enumerate(etat.cibles_courantes()):
            if cible.carte.role.name in ROLES_CACHES_SELON_LES_REGLES:
                continue
            visibles_vues += 1
            libelle = _libelle_de_cible(etat, indice)
            assert cible.carte.role.name in libelle, (
                f"{instance.nom} : le libelle {libelle!r} ne nomme pas le role d'une carte "
                f"posee face visible"
            )
            assert f"f{cible.carte.famille}" in libelle, (
                f"{instance.nom} : le libelle {libelle!r} ne nomme pas la famille "
                f"{cible.carte.famille} d'une carte posee face visible"
            )

    assert visibles_vues > 0, (
        f"{instance.nom} : aucune cible visible sur {NB_PARTIES_BALAYAGE} parties, le test "
        f"ne prouve rien"
    )


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_chaque_libelle_de_cible_est_celui_que_l_arbitrage_prescrit(
    instance: Instance,
) -> None:
    """Le libelle complet, recalcule ici, sur toutes les cibles d'un balayage.

    Les deux tests precedents portent sur ce que le libelle ne doit pas contenir et sur ce
    qu'il doit contenir ; celui-ci fixe la chaine entiere, apparence, ordinal et zone.
    """
    cibles_vues = 0

    for etat in _noeuds_de_ciblage(instance, NB_PARTIES_BALAYAGE):
        for indice, cible in enumerate(etat.cibles_courantes()):
            cibles_vues += 1
            attendu = _libelle_attendu(etat, cible)
            obtenu = _libelle_de_cible(etat, indice)
            assert obtenu == attendu, (
                f"{instance.nom} : cible {indice} -- libelle {obtenu!r}, attendu {attendu!r}"
            )

    assert cibles_vues > 0, f"{instance.nom} : aucune cible sur {NB_PARTIES_BALAYAGE} parties"


# ---------------------------------------------------------------------------------
# Le plateau construit -- une zone qui porte tout ce qui peut mal tourner
#
# Une zone du banquet contenant, dans cet ordre de pose :
#   1. un Espion pose par J0        -- un dos
#   2. un Espion pose par J1        -- un second dos, d'une autre famille
#   3. un Noble, exemplaire 0       -- une carte visible
#   4. le meme Noble, exemplaire 1  -- son jumeau, que l'apparence seule ne separe pas
#   5. un Garde                     -- temoin : immunise, donc jamais une cible
#   6. l'Assassin de J2             -- celui qui choisit, exclu de ses propres cibles
#
# Rien n'est laisse au hasard : la pioche est fixee carte par carte, et chaque pose est
# choisie par ce qu'elle FAIT -- "mettre cette carte-la au banquet, a cette position" --
# jamais par son numero, qui depend du tri canonique de la main.
# ---------------------------------------------------------------------------------

#: La position du banquet ou tout se joue. N'importe laquelle conviendrait.
POSITION_CONSTRUITE = "ESTIME"

#: La famille des deux Noble jumeaux, et celle du Garde temoin et de l'Assassin. Deux
#: familles distinctes, pour qu'aucune coincidence ne masque une confusion.
FAMILLE_DES_JUMEAUX = 2
FAMILLE_DU_TEMOIN = 3

#: Les deux familles des deux dos, dans l'ordre de pose. L'echange des deux est la
#: construction hostile.
FAMILLES_DES_DOS: tuple[int, int] = (0, 1)

#: Combien de tours de table la construction demande.
TOURS_CONSTRUITS = 2


def _cartes_du_banquet(familles_des_dos: tuple[int, int]) -> list:
    """Les six cartes a poser au banquet, dans l'ordre des mains qui les portent."""
    carte = module("cards").Carte
    role = module("cards").Role
    return [
        carte(familles_des_dos[0], role.ESPION, 0),
        carte(familles_des_dos[1], role.ESPION, 0),
        carte(FAMILLE_DES_JUMEAUX, role.NOBLE, 0),
        carte(FAMILLE_DES_JUMEAUX, role.NOBLE, 1),
        carte(FAMILLE_DU_TEMOIN, role.GARDE, 0),
        carte(FAMILLE_DU_TEMOIN, role.ASSASSIN, 0),
    ]


def _pioche_construite(instance: Instance, familles_des_dos: tuple[int, int]) -> tuple[list, list]:
    """Une pioche qui met les six cartes voulues dans les six premieres mains.

    Regle R-b : les `3 x joueurs` premieres cartes forment le premier tour de table, dans
    l'ordre des joueurs. Chaque main recoit donc sa carte de banquet suivie de deux cartes
    de remplissage, qui partiront dans les domaines.

    **Aucun Assassin dans le remplissage.** Un Assassin pose dans un domaine ouvrirait un
    noeud de ciblage supplementaire, et la construction ne serait plus le seul de la partie.
    """
    au_banquet = _cartes_du_banquet(familles_des_dos)
    assert len(au_banquet) == TOURS_CONSTRUITS * instance.joueurs, (
        f"{len(au_banquet)} cartes de banquet pour "
        f"{TOURS_CONSTRUITS * instance.joueurs} mains : une main pose exactement une carte "
        f"au banquet"
    )

    designees = {cle(carte) for carte in au_banquet}
    paquet = paquet_ordonne(instance)

    nb_remplissage = 2 * len(au_banquet)
    remplissage = [
        carte
        for carte in paquet
        if cle(carte) not in designees and carte.role.name != "ASSASSIN"
    ][:nb_remplissage]
    assert len(remplissage) == nb_remplissage, (
        f"{instance.nom} : pas assez de cartes non-Assassin pour remplir les mains"
    )

    utilisees = designees | {cle(carte) for carte in remplissage}
    queue = [carte for carte in paquet if cle(carte) not in utilisees]

    pioche: list = []
    for rang, principale in enumerate(au_banquet):
        pioche.append(principale)
        pioche.extend(remplissage[2 * rang : 2 * rang + 2])
    pioche.extend(queue)
    return pioche, au_banquet


def _action_qui_pose_au_banquet(etat, config, carte_visee, position: str) -> int:  # noqa: ANN001
    """L'action de pose qui met `carte_visee` au banquet, a `position`.

    Choisie par sa semantique, jamais par son numero : le tri canonique de la main
    (regle R-c) fait qu'une meme action ne designe pas la meme carte dans deux mains
    differentes. C'est exactement le piege que la construction hostile tend.
    """
    rules = module("rules")
    main = etat.vue_privilegiee().mains[etat.current_player()]
    indices = [rang for rang, carte in enumerate(main) if cle(carte) == cle(carte_visee)]
    assert len(indices) == 1, (
        f"la carte {cle(carte_visee)} figure {len(indices)} fois dans la main "
        f"{[cle(carte) for carte in main]}"
    )

    candidates = []
    for action in sorted(etat.legal_actions()):
        pose = rules.decoder_action_pose(action, config)
        if pose.position.name == position and pose.indices_main[0] == indices[0]:
            candidates.append(action)
    assert candidates, (
        f"aucune action ne pose {cle(carte_visee)} au banquet en {position}"
    )
    return candidates[0]


def _plateau_construit(
    instance: Instance = RAPIDE_3J, familles_des_dos: tuple[int, int] = FAMILLES_DES_DOS
):  # noqa: ANN202
    """Joue la construction et rend l'etat, arrete au noeud de ciblage de l'Assassin."""
    assert instance.joueurs >= 3, f"{instance.nom} : la construction demande 3 joueurs"
    assert instance.tours >= TOURS_CONSTRUITS, f"{instance.nom} : moins de deux tours"
    assert instance.exemplaires >= 2, f"{instance.nom} : pas de jumeau possible"

    config = construire_config(instance)
    jeu = module("openspiel_adapter").CourtisansGame(config=config)
    pioche, au_banquet = _pioche_construite(instance, familles_des_dos)
    etat = jeu.reset_depuis_pioche(pioche)

    for principale in au_banquet:
        assert etat.phase().name == "POSE", (
            f"phase {etat.phase().name} au moment de poser {cle(principale)}, attendu POSE"
        )
        etat.apply_action(
            _action_qui_pose_au_banquet(etat, config, principale, POSITION_CONSTRUITE)
        )

    assert etat.phase().name == "CIBLAGE", (
        f"la construction devait s'arreter sur un noeud de ciblage, phase "
        f"{etat.phase().name}"
    )
    return etat


def _cibles_par_apparence(etat) -> dict[str, list[int]]:  # noqa: ANN001
    """Les indices des cibles, regroupes par ce que tout le monde voit d'elles."""
    groupes: dict[str, list[int]] = {}
    for indice, cible in enumerate(etat.cibles_courantes()):
        groupes.setdefault(_apparence_publique(cible), []).append(indice)
    return groupes


# ---------------------------------------------------------------------------------
# 3. La construction porte bien ce qu'elle annonce
# ---------------------------------------------------------------------------------


def test_le_plateau_construit_porte_deux_dos_et_deux_jumeaux_visibles() -> None:
    """Sans ce controle, les trois tests suivants pourraient etre verts par vacuite."""
    etat = _plateau_construit()
    groupes = _cibles_par_apparence(etat)

    assert len(groupes.get(APPARENCE_DU_DOS, [])) == 2, (
        f"la zone devait porter deux dos ciblables, elle en porte "
        f"{len(groupes.get(APPARENCE_DU_DOS, []))} -- cibles "
        f"{[cle(cible.carte) for cible in etat.cibles_courantes()]}"
    )
    jumeaux = f"f{FAMILLE_DES_JUMEAUX}-NOBLE"
    assert len(groupes.get(jumeaux, [])) == 2, (
        f"la zone devait porter deux {jumeaux} ciblables, elle en porte "
        f"{len(groupes.get(jumeaux, []))}"
    )
    roles_cibles = {cible.carte.role.name for cible in etat.cibles_courantes()}
    assert not roles_cibles & ROLES_IMMUNISES_SELON_LES_REGLES, (
        f"un role immunise figure parmi les cibles : {sorted(roles_cibles)}"
    )


# ---------------------------------------------------------------------------------
# 4. Deux cartes de meme apparence dans une meme zone restent distinguables
# ---------------------------------------------------------------------------------


def test_deux_dos_d_une_meme_zone_portent_deux_libelles_distincts() -> None:
    """La contrainte d'OpenSpiel, sur le cas que l'anonymisation menace directement.

    Effacer l'identite d'un dos sans mettre un ordinal a la place ferait porter le meme
    nom aux deux dos de la zone -- le defaut 7 de l'audit de la phase 0, rouvert.
    """
    etat = _plateau_construit()
    indices = _cibles_par_apparence(etat)[APPARENCE_DU_DOS]
    libelles = [_libelle_de_cible(etat, indice) for indice in indices]

    assert len(set(libelles)) == len(libelles), (
        f"les {len(libelles)} dos de la zone portent {len(set(libelles))} libelle(s) "
        f"distinct(s) : {libelles}"
    )


def test_deux_cartes_visibles_identiques_d_une_meme_zone_portent_deux_libelles_distincts() -> None:
    """Le meme controle sur deux exemplaires du meme couple (famille, role).

    C15 exige `nb_cibles + 1` actions legales : les doublons ne sont pas masques en phase
    de ciblage, contrairement aux actions de pose. L'apparence seule ne les separe donc
    pas, et l'ordinal leur est aussi necessaire qu'aux dos.
    """
    etat = _plateau_construit()
    indices = _cibles_par_apparence(etat)[f"f{FAMILLE_DES_JUMEAUX}-NOBLE"]
    libelles = [_libelle_de_cible(etat, indice) for indice in indices]

    assert len(set(libelles)) == len(libelles), (
        f"les {len(libelles)} jumeaux visibles de la zone portent "
        f"{len(set(libelles))} libelle(s) distinct(s) : {libelles}"
    )


def test_les_libelles_du_plateau_construit_sont_exactement_ceux_de_l_arbitrage() -> None:
    """La forme entiere, ecrite en clair, sur un plateau dont on connait chaque carte.

    C'est le test qui fixe le vocabulaire. Les cinq chaines sont transcrites depuis
    l'arbitrage du 17/08, pas relevees sur une sortie du code.
    """
    etat = _plateau_construit()

    assert _libelles(etat) == [
        "tuer le 1er dos en ESTIME",
        "tuer le 2e dos en ESTIME",
        f"tuer le 1er f{FAMILLE_DES_JUMEAUX}-NOBLE en ESTIME",
        f"tuer le 2e f{FAMILLE_DES_JUMEAUX}-NOBLE en ESTIME",
        "ne pas tuer",
    ]


# ---------------------------------------------------------------------------------
# 5. Le test hostile -- I7 transpose aux libelles
# ---------------------------------------------------------------------------------


def test_echanger_les_deux_dos_ne_change_aucun_libelle() -> None:
    """Deux mondes qui ne different que par l'identite des deux dos portent les MEMES
    libelles.

    C'est la construction de l'invariant I7 transposee a `action_to_string`, et elle est
    strictement plus forte qu'une absence de sous-chaine : elle ne demande pas au test de
    savoir a l'avance sous quelle forme une identite pourrait fuiter. Si le libelle porte
    quoi que ce soit qui depende de la famille cachee -- son numero, sa lettre, un ordre de
    tri, un compte par famille -- les deux listes divergent.

    Le controle prealable que les deux plateaux **different reellement** est ce qui empeche
    ce test d'etre vert par construction.
    """
    familles = FAMILLES_DES_DOS
    etat_a = _plateau_construit(familles_des_dos=familles)
    etat_b = _plateau_construit(familles_des_dos=(familles[1], familles[0]))

    dos_a = [
        cle(cible.carte)
        for cible in etat_a.cibles_courantes()
        if _apparence_publique(cible) == APPARENCE_DU_DOS
    ]
    dos_b = [
        cle(cible.carte)
        for cible in etat_b.cibles_courantes()
        if _apparence_publique(cible) == APPARENCE_DU_DOS
    ]
    assert dos_a != dos_b, (
        f"les deux plateaux ne different pas : les dos sont {dos_a} des deux cotes, le "
        f"test ne prouve rien"
    )
    assert sorted(dos_a) == sorted(dos_b), (
        f"les deux plateaux devaient porter les memes cartes a l'echange pres, "
        f"{dos_a} contre {dos_b}"
    )

    assert list(etat_a.legal_actions()) == list(etat_b.legal_actions()), (
        "l'identite d'un dos change les actions legales -- c'est l'invariant I9, pas ce test"
    )
    assert _libelles(etat_a) == _libelles(etat_b), (
        f"echanger les deux dos change les libelles :\n  A : {_libelles(etat_a)}\n"
        f"  B : {_libelles(etat_b)}"
    )
