"""Courtisans-mini — instance réduite résoluble exactement, comme jeu OpenSpiel.

But (cf. rapport §27) : un ORACLE. Sur cette mini-instance, CFR+ tabulaire calcule
un Nash et une exploitabilité *exacts*, qui serviront à valider tout pipeline Deep CFR
(le Deep CFR doit y converger).

v0 — volontairement minuscule pour valider le pipeline :
  - 2 familles × 3 rôles {Noble(val2), Espion(caché, val1), Simple(val1)} = 6 cartes.
  - 2 joueurs, 3 cartes en main, 1 manche (donne 3+3, pioche vide).
  - Chaque tour : 1 carte chez la Reine (Estime|Disgrâce), 1 dans son domaine,
    1 chez l'adverse — encodé par les 12 actions composites (comme le vrai jeu).
  - Score : majorité Estime−Disgrâce par famille → statut ; cartes en domaine scorent
    ±valeur pour le propriétaire du domaine ; espions révélés en fin de partie.
  - Payoff = indicateur de victoire {+1, 0, −1} (vrai objectif du jeu).
  - Info cachée : un espion posé est face cachée pour l'adversaire (il en voit
    l'existence + le poseur, pas la famille).
"""
import os
from itertools import combinations, permutations

import numpy as np
import pyspiel

NOBLE, ESPION, SIMPLE = 0, 1, 2
ROLE_NAME = {NOBLE: "N", ESPION: "E", SIMPLE: "S"}
NUM_FAMILIES = 3

# Canonicalisation par symétrie des familles (quotient lossless, cf. rapport §31).
# Les NUM_FAMILIES familles sont interchangeables (automorphisme du jeu) → on relabel
# les familles dans l'ordre canonique pour fusionner les info-sets symétriques.
# Toggle (COURTISANS_CANON=0 pour désactiver et comparer) — défaut activé.
CANON = os.environ.get("COURTISANS_CANON", "1") == "1"

# NUM_FAMILIES × 3 rôles cartes distinctes : (famille, rôle).
CARDS = [(f, r) for f in range(NUM_FAMILIES) for r in (NOBLE, ESPION, SIMPLE)]
NUM_CARDS = len(CARDS)
HAND = 3


def card_value(r):
    return 2 if r == NOBLE else 1


def is_hidden(r):
    return r == ESPION


def card_str(cid):
    f, r = CARDS[cid]
    return f"{f}{ROLE_NAME[r]}"


# Relabel d'une carte sous une permutation de familles `perm` (perm[f] = nouveau label).
_FAMILY_PERMS = list(permutations(range(NUM_FAMILIES)))
_IDENTITY_PERM = tuple(range(NUM_FAMILIES))
_CANON_CACHE = {}   # signature de vue -> perm canonique (fonction pure, jamais périmé)


def _relabel(cid, perm):
    f, r = divmod(cid, 3)   # cid = f*3 + r (rôles 0..2)
    return perm[f] * 3 + r


# Les 12 actions composites : (idx carte Reine, Estime?, idx carte domaine perso parmi le reste).
_COMBOS = []
for _qi in range(3):
    for _est in (True, False):
        _rem = [x for x in range(3) if x != _qi]
        for _own_rel in range(2):
            _COMBOS.append((_qi, _est, _own_rel))  # 3*2*2 = 12

# Les donnes : (main P0, main P1) ; les cartes restantes sont hors-jeu (face cachée,
# inconnues des deux joueurs). À 2 familles : C(6,3)×C(3,3)=20, reste 0 (= v0).
# À 3 familles : C(9,3)×C(6,3)=1680, reste 3.
_DEALS = []
for _p0 in combinations(range(NUM_CARDS), HAND):
    _rest = [c for c in range(NUM_CARDS) if c not in set(_p0)]
    for _p1 in combinations(_rest, HAND):
        _DEALS.append((_p0, _p1))

# Géométrie du tenseur d'info-state (encodage lossless, cf. information_state_tensor).
ZONE_IDX = {"E": 0, "D": 1, "dom": 2}
SLOT = (NUM_CARDS + 1) + 3 + 3 + 2   # card(+inconnu) + zone + owner + placer
MAX_SLOTS = 3                        # board ≤ 3 entrées à un point de décision
TENSOR_SIZE = 2 + NUM_CARDS + MAX_SLOTS * SLOT

_GAME_TYPE = pyspiel.GameType(
    short_name="courtisans_mini",
    long_name="Courtisans Mini",
    dynamics=pyspiel.GameType.Dynamics.SEQUENTIAL,
    chance_mode=pyspiel.GameType.ChanceMode.EXPLICIT_STOCHASTIC,
    information=pyspiel.GameType.Information.IMPERFECT_INFORMATION,
    utility=pyspiel.GameType.Utility.ZERO_SUM,
    reward_model=pyspiel.GameType.RewardModel.TERMINAL,
    max_num_players=2,
    min_num_players=2,
    provides_information_state_string=True,
    provides_information_state_tensor=True,
    provides_observation_string=False,
    provides_observation_tensor=False,
    parameter_specification={},
)
_GAME_INFO = pyspiel.GameInfo(
    num_distinct_actions=len(_COMBOS),  # 12 actions joueur (chance = espace séparé)
    max_chance_outcomes=len(_DEALS),
    num_players=2,
    min_utility=-1.0,
    max_utility=1.0,
    utility_sum=0.0,
    max_game_length=3,  # 1 donne + 2 placements
)


class CourtisansMiniGame(pyspiel.Game):
    def __init__(self, params=None):
        super().__init__(_GAME_TYPE, _GAME_INFO, params or {})

    def new_initial_state(self):
        return CourtisansMiniState(self)


class CourtisansMiniState(pyspiel.State):
    def __init__(self, game):
        super().__init__(game)
        self._hands = {0: [], 1: []}
        self._board = []          # liste de dicts : card, zone('E'|'D'|'dom'), owner, placer, hidden
        self._cur = pyspiel.PlayerId.CHANCE
        self._next_player = 0     # qui joue après la donne
        self._terminal = False

    # ---- mécanique ----
    def current_player(self):
        if self._terminal:
            return pyspiel.PlayerId.TERMINAL
        return self._cur

    def _legal_actions(self, player):
        return list(range(len(_COMBOS)))  # 12, la main fait toujours 3 en v0

    def chance_outcomes(self):
        p = 1.0 / len(_DEALS)
        return [(i, p) for i in range(len(_DEALS))]

    def _apply_action(self, action):
        if self._cur == pyspiel.PlayerId.CHANCE:
            p0, p1 = _DEALS[action]   # le reste des cartes est hors-jeu (face cachée)
            self._hands[0] = sorted(p0)
            self._hands[1] = sorted(p1)
            self._cur = 0
            return
        player = self._cur
        qi, est, own_rel = _COMBOS[action]
        # Les actions sont interprétées dans l'ordre canonique de la main (relabel des
        # familles par la perm canonique du joueur). Sans canon, perm=identité → ordre
        # par id de carte = comportement d'origine. Garantit que "action a" désigne la
        # même carte canonique pour tous les nœuds d'un même orbite (quotient correct).
        perm = self._canon_perm(player)
        hand = sorted(self._hands[player], key=lambda c: _relabel(c, perm))
        rem = [x for x in range(3) if x != qi]
        own_c = hand[rem[own_rel]]
        opp_c = hand[rem[1 - own_rel]]
        q_c = hand[qi]
        self._board.append(dict(card=q_c, zone=("E" if est else "D"),
                                owner=None, placer=player, hidden=is_hidden(CARDS[q_c][1])))
        self._board.append(dict(card=own_c, zone="dom", owner=player,
                                placer=player, hidden=is_hidden(CARDS[own_c][1])))
        self._board.append(dict(card=opp_c, zone="dom", owner=1 - player,
                                placer=player, hidden=is_hidden(CARDS[opp_c][1])))
        self._hands[player] = []
        if player == 0:
            self._cur = 1
        else:
            self._terminal = True

    # ---- scoring ----
    def _scores(self):
        infl = {f: 0 for f in range(NUM_FAMILIES)}
        for e in self._board:
            f = CARDS[e["card"]][0]
            if e["zone"] == "E":
                infl[f] += 1
            elif e["zone"] == "D":
                infl[f] -= 1
        score = {0: 0, 1: 0}
        for e in self._board:
            if e["zone"] != "dom":
                continue
            f, r = CARDS[e["card"]]
            s = infl[f]
            if s > 0:
                score[e["owner"]] += card_value(r)
            elif s < 0:
                score[e["owner"]] -= card_value(r)
        return score

    def is_terminal(self):
        return self._terminal

    def returns(self):
        if not self._terminal:
            return [0.0, 0.0]
        sc = self._scores()
        if sc[0] > sc[1]:
            r = 1.0
        elif sc[1] > sc[0]:
            r = -1.0
        else:
            r = 0.0
        return [r, -r]

    # ---- information (rappel parfait : 1 décision/joueur en v0) ----
    def _repr(self, player, perm):
        """Représentation de la vue de `player` avec relabel des familles par `perm`.
        Cartes cachées de l'adverse → '??' (inchangées par le relabel). Main triée
        sur l'id relabelé (ordre canonique) ; board gardé dans l'ordre de pose (public).
        """
        hand = ",".join(sorted(card_str(_relabel(c, perm)) for c in self._hands[player]))
        seen = []
        for e in self._board:
            visible = (not e["hidden"]) or (e["placer"] == player)
            ident = card_str(_relabel(e["card"], perm)) if visible else "??"
            owner = "Q" if e["owner"] is None else f"d{e['owner']}"
            seen.append(f"{ident}@{e['zone']}{owner}<p{e['placer']}")
        return f"P{player}|main:{hand}|board:{';'.join(seen)}"

    def _canon_perm(self, player):
        """Permutation de familles canonique pour la vue de `player` : celle qui
        minimise la représentation (puis la perm elle-même pour le tie-break).
        Ne dépend que de l'info visible par `player` → cohérente le long du tree.

        Mémoïsé dans un cache module-level indexé par une *signature immuable* de la
        vue (joueur + main + board visible). C'est une fonction pure de cette
        signature → jamais périmé, même si l'état est cloné/partagé. Évite le
        brute-force sur les perms à chaque appel (critique pour CFR/Deep CFR ;
        indispensable à 6 familles = 720 perms)."""
        if not CANON:
            return _IDENTITY_PERM
        key = (player, tuple(self._hands[player]),
               tuple(((e["card"] if (not e["hidden"] or e["placer"] == player) else -1),
                      e["zone"], e["owner"], e["placer"]) for e in self._board))
        p = _CANON_CACHE.get(key)
        if p is None:
            p = min(_FAMILY_PERMS, key=lambda pm: (self._repr(player, pm), pm))
            _CANON_CACHE[key] = p
        return p

    def information_state_string(self, player=None):
        if player is None:
            player = self._cur
        return self._repr(player, self._canon_perm(player))

    def information_state_tensor(self, player=None):
        """Encodage *lossless* de l'info-set (même contenu que la string).

        Layout (TENSOR_SIZE dims) :
          [0:2]            perspective du joueur (one-hot p0/p1)
          [2:2+NUM_CARDS]  main : multi-hot des cartes (sous-ensemble de taille 3)
          puis MAX_SLOTS blocs de SLOT dims (board, dans l'ordre de pose) :
            card  NUM_CARDS+1  (cartes connues + 1 "inconnu" si espion adverse caché)
            zone  3            (E, D, dom)
            owner 3            (Reine/None, d0, d1)
            placer 2           (p0, p1)
        Au point de décision le board a 0 (P0) ou 3 (P1) entrées ; les slots
        non remplis restent à zéro. Injectif vs information_state_string.
        """
        if player is None:
            player = self._cur
        nc = NUM_CARDS
        perm = self._canon_perm(player)   # relabel canonique (identité si CANON off)
        v = [0.0] * TENSOR_SIZE
        v[player] = 1.0
        for c in self._hands[player]:
            v[2 + _relabel(c, perm)] = 1.0
        base = 2 + nc
        for i, e in enumerate(self._board[:MAX_SLOTS]):
            off = base + i * SLOT
            known = (not e["hidden"]) or (e["placer"] == player)
            v[off + (_relabel(e["card"], perm) if known else nc)] = 1.0  # card (nc+1)
            v[off + (nc + 1) + ZONE_IDX[e["zone"]]] = 1.0       # zone (3)
            owner_i = 0 if e["owner"] is None else e["owner"] + 1
            v[off + (nc + 1 + 3) + owner_i] = 1.0               # owner (3)
            v[off + (nc + 1 + 3 + 3) + e["placer"]] = 1.0       # placer (2)
        return v

    def _action_to_string(self, player, action):
        if player == pyspiel.PlayerId.CHANCE:
            p0, p1 = _DEALS[action]
            return f"deal:P0={[card_str(c) for c in p0]}|P1={[card_str(c) for c in p1]}"
        qi, est, own_rel = _COMBOS[action]
        return f"a{action}(reine={'E' if est else 'D'})"

    def __str__(self):
        if self._cur == pyspiel.PlayerId.CHANCE:
            return "chance(deal)"
        b = ";".join(f"{card_str(e['card']) if not e['hidden'] else '??'}@{e['zone']}" for e in self._board)
        return f"cur={self._cur} board[{b}] term={self._terminal}"


pyspiel.register_game(_GAME_TYPE, CourtisansMiniGame)
