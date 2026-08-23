"""La mecanique du reseau et de la boucle, testee AVANT d'entrainer.

Ce fichier ne teste pas si l'agent joue bien -- ca, c'est la mesure. Il teste que **la machine
ne peut pas mentir en silence** : les gardes levent, le masque ne laisse passer aucune action
illegale, les trajectoires portent le gain du bon siege, et un checkpoint fige ne contribue
jamais a la mise a jour.

Chacun de ces quatre points a la meme propriete : s'il etait faux, **rien ne le signalerait**.
La perte descendrait, l'agent apprendrait, et il apprendrait autre chose que ce qu'on croit.
C'est le mode de defaut de ce projet, transpose a une boucle d'apprentissage.
"""

from __future__ import annotations

import math
import random

import pytest
import torch

from agents import entrainement
from agents import reseau as reseau_module
from courtisans.engine import Engine
from courtisans.infoset import tenseur
from mesure.instance import ENTRAINEMENT_3J

CONFIG = ENTRAINEMENT_3J
APPAREIL = torch.device("cpu")


def _reseau(graine: int = 0) -> reseau_module.ReseauPolitiqueValeur:
    torch.manual_seed(graine)
    etat = Engine(CONFIG).reset(0)
    return reseau_module.ReseauPolitiqueValeur(
        len(tenseur(etat, 0)), 6 * 2 * (CONFIG.joueurs - 1)
    )


# ---------------------------------------------------------------------------------
# Le masque -- il refuse le vide, et il met a EXACTEMENT zero
# ---------------------------------------------------------------------------------


def test_le_masque_leve_sur_une_ligne_sans_action_legale():
    """Masquer tout produirait un softmax de -inf partout, donc des NaN **silencieux**.

    Le NaN ne leve pas : il se propage dans le gradient, et la perte devient NaN plusieurs
    etapes plus tard, loin de la cause. C'est pourquoi la garde est au moment du masque.
    """
    with pytest.raises(ValueError, match="aucune action legale"):
        reseau_module.masque([[0, 1], []], nb_actions=4)


def test_le_masque_leve_sur_une_action_hors_de_la_tete():
    """La tete du reseau et l'espace d'action du moteur ne doivent pas diverger en silence."""
    with pytest.raises(ValueError, match="hors de la tete"):
        reseau_module.masque([[0, 7]], nb_actions=4)


def test_le_masque_leve_sur_un_lot_vide():
    with pytest.raises(ValueError, match="ne se construit pas sur du vide"):
        reseau_module.masque([], nb_actions=4)


def test_les_actions_illegales_ont_une_probabilite_EXACTEMENT_nulle():
    """« Tres petite » ne suffit pas : elle finirait par etre tiree.

    Une probabilite de 1e-30 sort une fois sur 1e30 tirages -- jamais, en pratique. Mais une
    probabilite de 1e-8 sort une fois sur cent millions, et le moteur leverait alors sur une
    action illegale, tres loin de la cause. Le cas exige donc le zero **exact**, avec des
    logits volontairement enormes sur les actions interdites.
    """
    logits = torch.tensor([[1000.0, -1.0, 1000.0, 0.0]])
    plan = reseau_module.masque([[1, 3]], nb_actions=4)
    loi = reseau_module.probabilites(logits, plan)
    assert loi[0, 0].item() == 0.0
    assert loi[0, 2].item() == 0.0
    assert loi[0, 1].item() > 0.0 and loi[0, 3].item() > 0.0
    assert math.isclose(loi[0].sum().item(), 1.0, rel_tol=1e-6)


def test_probabilites_leve_si_le_masque_n_a_pas_la_forme_des_logits():
    with pytest.raises(ValueError, match="memes \\(ligne, action\\)"):
        reseau_module.probabilites(torch.zeros(2, 4), reseau_module.masque([[0]], 4))


@pytest.mark.parametrize("graine", [0, 1, 2, 3, 4])
def test_un_tirage_ne_rend_jamais_une_action_masquee(graine: int):
    """Le controle de bout en bout du masque : mille tirages, aucune action interdite.

    Il est fait sur des logits **aleatoires et grands**, pour que les actions interdites soient
    parfois celles que le reseau prefererait de loin.
    """
    alea = random.Random(graine)
    generateur = torch.Generator().manual_seed(graine)
    for _ in range(200):
        logits = torch.randn(1, 8, generator=generateur) * 20
        legales = sorted(alea.sample(range(8), alea.randint(1, 4)))
        loi = reseau_module.probabilites(logits, reseau_module.masque([legales], 8))
        for _ in range(5):
            assert reseau_module.tirer(loi[0].tolist(), alea) in legales


# ---------------------------------------------------------------------------------
# Le tirage -- il refuse une loi qui ne somme pas a 1
# ---------------------------------------------------------------------------------


def test_tirer_leve_sur_une_loi_qui_ne_somme_pas_a_un():
    """Une loi qui ne somme pas a 1 est le symptome d'un masque mal applique.

    Sans cette garde, le tirage rendrait quand meme un indice -- un indice sans signification,
    qui serait joue, appris, et mesure.
    """
    with pytest.raises(ValueError, match="la loi somme a"):
        reseau_module.tirer([0.3, 0.3], random.Random(0))
    with pytest.raises(ValueError, match="la loi somme a"):
        reseau_module.tirer([float("nan"), 1.0], random.Random(0))


def test_tirer_respecte_la_loi():
    """Un tirage qui ignorerait la loi passerait toutes les autres epreuves de ce fichier.

    On tire 20 000 fois une loi tres asymetrique et on exige que la frequence observee soit a
    moins de 2 points de la loi. C'est large, et c'est voulu : le cas cherche une erreur de
    construction, pas un defaut de generateur.
    """
    loi = [0.7, 0.2, 0.1]
    alea = random.Random(12345)
    comptes = [0, 0, 0]
    for _ in range(20_000):
        comptes[reseau_module.tirer(loi, alea)] += 1
    for indice, attendu in enumerate(loi):
        observe = comptes[indice] / 20_000
        assert abs(observe - attendu) < 0.02, (
            f"indice {indice} : observe {observe:.4f}, attendu {attendu}"
        )


# ---------------------------------------------------------------------------------
# Le reseau -- sa forme vient du moteur, jamais d'une constante
# ---------------------------------------------------------------------------------


def test_la_forme_du_reseau_est_mesuree_sur_le_moteur():
    """205 entrees et 24 actions ne sont pas ecrites en dur : elles sont demandees au moteur."""
    modele = entrainement.construire(APPAREIL)
    etat = Engine(CONFIG).reset(0)
    assert modele.taille_observation == len(tenseur(etat, 0))
    assert modele.nb_actions > max(etat.legal_actions())


def test_le_reseau_refuse_une_forme_absurde():
    with pytest.raises(ValueError, match="a besoin d'une observation"):
        reseau_module.ReseauPolitiqueValeur(0, 4)
    with pytest.raises(ValueError, match="au moins une couche cachee"):
        reseau_module.ReseauPolitiqueValeur(10, 4, profondeur=0)


#: Le seuil de « quasi uniforme », en multiples de l'uniforme `1/len(actions_legales)`.
#:
#: **MESURE, pas devine.** Sur 10 graines d'initialisation x 20 etats de decision tires au
#: hasard, l'etendue relative de la politique initiale vaut au plus **0,1452**, mediane 0,0625.
#: Une politique volontairement piquee -- meme reseau, gain de la tete porte a 5,0 -- atteint
#: **23,9**. Le seuil de 0,30 est donc au-dessus du maximum observe d'un facteur 2, et
#: **deux ordres de grandeur** sous une politique piquee : il separe reellement les deux.
#:
#: Une premiere redaction posait 0,05, un nombre choisi sans rien mesurer, et le cas echouait
#: sur une politique parfaitement saine. Un seuil de test se mesure comme un seuil de mesure.
ETENDUE_QUASI_UNIFORME = 0.30


def test_la_politique_initiale_est_quasi_uniforme_sur_les_actions_legales():
    """Le gain de 0,01 sur la tete de politique, verifie plutot que suppose.

    Une politique initiale piquee explorerait mal, et le premier checkpoint du pool serait une
    convention arbitraire plutot qu'un point de depart neutre.
    """
    modele = _reseau()
    etat = Engine(CONFIG).reset(0)
    legales = etat.legal_actions()
    with torch.no_grad():
        logits, _ = modele(torch.tensor([tenseur(etat, 0)], dtype=torch.float32))
    loi = reseau_module.probabilites(logits, reseau_module.masque([legales], modele.nb_actions))
    valeurs = [loi[0, a].item() for a in legales]
    uniforme = 1.0 / len(legales)
    etendue = (max(valeurs) - min(valeurs)) / uniforme
    assert etendue < ETENDUE_QUASI_UNIFORME, (
        f"politique initiale trop piquee : etendue relative {etendue:.4f}"
    )


def test_le_critere_de_quasi_uniformite_rejette_bien_une_politique_piquee():
    """Un critere qui ne peut pas echouer ne prouve rien : on lui donne une politique piquee.

    Meme reseau, meme etat, mais la tete de politique est reinitialisee avec un gain de 5,0 au
    lieu de 0,01. Le critere doit la rejeter -- et largement, sinon il ne separe rien.
    """
    modele = _reseau()
    torch.nn.init.orthogonal_(modele.tete_politique.weight, gain=5.0)
    etat = Engine(CONFIG).reset(0)
    legales = etat.legal_actions()
    with torch.no_grad():
        logits, _ = modele(torch.tensor([tenseur(etat, 0)], dtype=torch.float32))
    loi = reseau_module.probabilites(logits, reseau_module.masque([legales], modele.nb_actions))
    valeurs = [loi[0, a].item() for a in legales]
    etendue = (max(valeurs) - min(valeurs)) * len(legales)
    assert etendue > ETENDUE_QUASI_UNIFORME * 10, (
        f"une politique de gain 5,0 passe le critere avec une etendue de {etendue:.4f} : "
        f"le critere ne separe pas une politique piquee d'une politique uniforme."
    )


# ---------------------------------------------------------------------------------
# La vague -- les trajectoires portent le gain du BON siege
# ---------------------------------------------------------------------------------


def test_chaque_noeud_porte_le_gain_terminal_de_SON_siege():
    """La faute qui ne se signalerait pas : attribuer a un nœud le gain d'un autre siege.

    Le cas rejoue chaque partie **seule**, hors de toute vague, et reconstruit
    independamment quel siege decidait a quel nœud et quel gain ce siege a obtenu. Demander a
    la boucle de se confirmer elle-meme ne testerait rien.

    **C'est ce cas qui a fait corriger la boucle.** Sa premiere version echouait, et pas parce
    que la boucle attribuait mal les gains : la vague avancait en **lock-step** avec un
    aleatoire partage, donc rejouer les parties l'une apres l'autre en produisait d'autres. La
    boucle n'etait pas fausse, elle etait **irreproductible a l'unite** -- une vague de 6 et
    une vague de 64 ne jouaient pas les memes parties sur les memes donnes. Chaque partie
    derive desormais son aleatoire de sa donne, et ce cas est ce qui le tient.
    """
    modele = _reseau()
    trajectoires, nb = entrainement.jouer_une_vague(
        modele, [], 6, entrainement.DEPART_DONNE_ENTRAINEMENT, APPAREIL
    )
    assert nb == 6
    assert len(trajectoires) > 0

    # La reconstruction est rangee par `(donne, siege)`, pas dans l'ordre du lock-step :
    # comparer deux entrelacements ne dirait rien sur l'attribution des gains.
    moteur = Engine(CONFIG)
    attendus: dict[tuple[int, int], list[float]] = {}
    for indice in range(6):
        donne = entrainement.DEPART_DONNE_ENTRAINEMENT + indice
        etat = moteur.reset(donne)
        alea = random.Random(entrainement.DECALAGE_TIRAGE + donne)
        sieges: list[int] = []
        while not etat.is_terminal():
            siege = etat.current_player()
            legales = etat.legal_actions()
            with torch.no_grad():
                logits, _ = modele(
                    torch.tensor([tenseur(etat, siege)], dtype=torch.float32)
                )
            loi = reseau_module.probabilites(
                logits, reseau_module.masque([legales], modele.nb_actions)
            )
            etat.apply(reseau_module.tirer(loi[0].tolist(), alea))
            sieges.append(siege)
        gains = etat.returns()
        for siege in sieges:
            attendus.setdefault((donne, siege), []).append(gains[siege])

    obtenus = {
        cle: [trajectoires.gains[rang] for rang in rangs]
        for cle, rangs in trajectoires.par_partie().items()
    }
    assert obtenus == attendus, (
        "un nœud porte le gain d'un autre siege que le sien : la boucle attribuerait le "
        "credit au mauvais joueur, et rien ne le signalerait."
    )


def test_une_partie_donne_le_meme_deroulement_quelle_que_soit_la_taille_de_la_vague():
    """La propriete que la correction ci-dessus a fait apparaitre, tenue explicitement.

    Les six premieres parties d'une vague de 6 et d'une vague de 64 doivent etre **les memes
    parties**. Sans ca, « la donne 100 000 » ne designerait pas un objet fixe, et aucun
    chiffre de cette phase ne serait rejouable a l'unite.
    """
    modele = _reseau()
    petite, _ = entrainement.jouer_une_vague(
        modele, [], 6, entrainement.DEPART_DONNE_ENTRAINEMENT, APPAREIL
    )
    grande, _ = entrainement.jouer_une_vague(
        modele, [], 64, entrainement.DEPART_DONNE_ENTRAINEMENT, APPAREIL
    )
    par_petite = petite.par_partie()
    par_grande = grande.par_partie()
    assert set(par_petite) <= set(par_grande)
    for cle, rangs in par_petite.items():
        assert [petite.actions[r] for r in rangs] == [
            grande.actions[r] for r in par_grande[cle]
        ], f"la partie {cle} ne se deroule pas pareil selon la taille de la vague"
        assert [petite.gains[r] for r in rangs] == [
            grande.gains[r] for r in par_grande[cle]
        ]
    assert len(grande) > len(petite)


def test_les_gains_collectes_sont_ceux_du_paragraphe_5_2():
    """Aucun gain hors de {-0,5 ; 0 ; +0,25 ; +1}. Un gain hors de ce lot serait un moteur faux."""
    modele = _reseau()
    trajectoires, _ = entrainement.jouer_une_vague(
        modele, [], 20, entrainement.DEPART_DONNE_ENTRAINEMENT, APPAREIL
    )
    autorises = {-0.5, 0.0, 0.25, 1.0}
    vus = set(trajectoires.gains)
    assert vus <= autorises, f"gains hors du paragraphe 5.2 : {sorted(vus - autorises)}"


def test_un_checkpoint_fige_joue_mais_n_est_JAMAIS_collecte():
    """La faute la plus silencieuse de toutes : melanger deux politiques dans une mise a jour.

    Les nœuds d'un checkpoint fige viennent d'une autre politique. Les collecter rendrait la
    mise a jour hors-politique **sans que le ratio de PPO le sache** : il comparerait la
    politique courante a elle-meme, en croyant corriger un ecart qui n'est pas celui-la.

    Le cas compare le nombre de nœuds collectes avec et sans pool, sur les memes donnes. Avec
    un pool, une partie sur trois environ voit un ou deux sieges tenus par un fige, donc il
    doit y avoir **strictement moins** de nœuds collectes.
    """
    modele = _reseau()
    fige = _reseau(graine=1)

    sans, _ = entrainement.jouer_une_vague(
        modele, [], 40, entrainement.DEPART_DONNE_ENTRAINEMENT, APPAREIL
    )
    avec, _ = entrainement.jouer_une_vague(
        modele, [fige], 40, entrainement.DEPART_DONNE_ENTRAINEMENT, APPAREIL
    )
    assert len(avec) < len(sans), (
        f"autant de nœuds collectes avec pool ({len(avec)}) que sans ({len(sans)}) : les "
        f"nœuds des checkpoints figes entrent dans la mise a jour."
    )
    # Et le pool ne peut pas tout prendre : l'apprenant occupe toujours un siege.
    assert len(avec) > len(sans) / 3


def test_la_composition_donne_toujours_un_siege_a_l_apprenant():
    """Sans ce cas, une partie pourrait n'avoir aucun siege collecte et personne ne le verrait."""
    fige = _reseau(graine=1)
    alea = random.Random(0)
    for _ in range(2000):
        tenu = entrainement._composer(alea, [fige, fige])  # noqa: SLF001
        assert tenu.count(None) >= 1, f"aucun siege pour l'apprenant : {tenu}"
        assert len(tenu) == CONFIG.joueurs


def test_sans_pool_la_composition_est_du_self_play_pur():
    """Au tout debut du run le pool est vide : les trois sieges sont la politique courante."""
    alea = random.Random(0)
    for _ in range(100):
        assert entrainement._composer(alea, []) == [None] * CONFIG.joueurs  # noqa: SLF001


# ---------------------------------------------------------------------------------
# La mise a jour -- elle refuse le vide, et elle bouge les poids
# ---------------------------------------------------------------------------------


def test_la_mise_a_jour_leve_sur_une_vague_vide():
    modele = _reseau()
    optimiseur = torch.optim.Adam(modele.parameters())
    with pytest.raises(ValueError, match="vague vide"):
        entrainement.mettre_a_jour(
            modele, optimiseur, entrainement.Trajectoires(), APPAREIL, random.Random(0)
        )


def test_la_mise_a_jour_change_les_poids_et_rend_ses_pertes():
    """Une mise a jour qui ne bougerait rien passerait inapercue et le run serait perdu."""
    modele = _reseau()
    optimiseur = torch.optim.Adam(modele.parameters(), lr=entrainement.TAUX_APPRENTISSAGE)
    avant = [p.detach().clone() for p in modele.parameters()]

    trajectoires, _ = entrainement.jouer_une_vague(
        modele, [], 24, entrainement.DEPART_DONNE_ENTRAINEMENT, APPAREIL
    )
    pertes = entrainement.mettre_a_jour(
        modele, optimiseur, trajectoires, APPAREIL, random.Random(0)
    )

    assert set(pertes) == {"politique", "valeur", "entropie"}
    assert all(math.isfinite(v) for v in pertes.values()), pertes
    bouges = sum(
        1 for a, p in zip(avant, modele.parameters(), strict=True) if not torch.equal(a, p)
    )
    assert bouges > 0, "aucun poids n'a bouge : la mise a jour ne fait rien"


def test_l_avantage_est_R_moins_V_et_non_un_GAE_bootstrappe():
    """`lambda = 1` est une decision de correction, pas de paresse : elle se verifie.

    A trois joueurs entrelaces, « l'etat suivant du siege i » n'est pas le nœud suivant de la
    partie. Un GAE qui bootstrapperait sur le nœud suivant amorcerait sur la valeur d'un
    ADVERSAIRE, et la faute serait silencieuse. Le cas verifie qu'aucune valeur d'un autre nœud
    n'entre dans le retour : le retour d'un nœud est **exactement** le gain terminal de son
    siege, donc il ne prend que quatre valeurs.
    """
    modele = _reseau()
    trajectoires, _ = entrainement.jouer_une_vague(
        modele, [], 12, entrainement.DEPART_DONNE_ENTRAINEMENT, APPAREIL
    )
    assert set(trajectoires.gains) <= {-0.5, 0.0, 0.25, 1.0}, (
        "un retour prend une valeur intermediaire : il a ete bootstrappe sur une valeur "
        "apprise, ce qui n'est pas ce que `lambda = 1` fait."
    )


# ---------------------------------------------------------------------------------
# La politique de bout en bout -- elle joue des parties legales
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_la_politique_du_reseau_joue_une_partie_entiere_et_legale(seed: int):
    from agents.politique_reseau import politique_reseau

    modele = _reseau()
    politique = politique_reseau(modele, random.Random(seed))
    etat = Engine(CONFIG).reset(seed)
    coups = 0
    while not etat.is_terminal():
        action = politique(etat)
        assert action in etat.legal_actions()
        etat.apply(action)
        coups += 1
    assert etat.is_terminal()
    assert coups >= CONFIG.tours * CONFIG.joueurs
    assert abs(sum(etat.returns())) < 1e-12


def test_la_variante_deterministe_joue_aussi_et_differe_de_la_stochastique():
    """Elle existe, elle est biaisee, et son ecart avec la reference est un chiffre.

    Si les deux donnaient toujours la meme partie, la rapporter a cote ne dirait rien.
    """
    from agents.politique_reseau import politique_reseau, politique_reseau_deterministe

    modele = _reseau()
    actions_st, actions_det = [], []
    for politique, sortie in (
        (politique_reseau(modele, random.Random(0)), actions_st),
        (politique_reseau_deterministe(modele), actions_det),
    ):
        etat = Engine(CONFIG).reset(0)
        while not etat.is_terminal():
            action = politique(etat)
            assert action in etat.legal_actions()
            sortie.append(action)
            etat.apply(action)
    assert actions_st != actions_det, (
        "les deux departages donnent la meme partie : la variante ne mesure rien"
    )
