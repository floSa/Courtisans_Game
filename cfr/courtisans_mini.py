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
from itertools import combinations

import numpy as np
import pyspiel

NOBLE, ESPION, SIMPLE = 0, 1, 2
ROLE_NAME = {NOBLE: "N", ESPION: "E", SIMPLE: "S"}
NUM_FAMILIES = 2

# 6 cartes distinctes : (famille, rôle).
CARDS = [(f, r) for f in range(NUM_FAMILIES) for r in (NOBLE, ESPION, SIMPLE)]
HAND = 3


def card_value(r):
    return 2 if r == NOBLE else 1


def is_hidden(r):
    return r == ESPION


def card_str(cid):
    f, r = CARDS[cid]
    return f"{f}{ROLE_NAME[r]}"


# Les 12 actions composites : (idx carte Reine, Estime?, idx carte domaine perso parmi le reste).
_COMBOS = []
for _qi in range(3):
    for _est in (True, False):
        _rem = [x for x in range(3) if x != _qi]
        for _own_rel in range(2):
            _COMBOS.append((_qi, _est, _own_rel))  # 3*2*2 = 12

# Les 20 donnes : quelles 3 cartes (sur 6) vont au joueur 0 (le 1 récupère le reste).
_DEALS = list(combinations(range(6), 3))  # C(6,3) = 20

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
    provides_information_state_tensor=False,
    provides_observation_string=False,
    provides_observation_tensor=False,
    parameter_specification={},
)
_GAME_INFO = pyspiel.GameInfo(
    num_distinct_actions=max(len(_COMBOS), len(_DEALS)),  # 20
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
            p0 = set(_DEALS[action])
            self._hands[0] = sorted(p0)
            self._hands[1] = sorted(set(range(6)) - p0)
            self._cur = 0
            return
        player = self._cur
        qi, est, own_rel = _COMBOS[action]
        hand = self._hands[player]
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
    def information_state_string(self, player=None):
        if player is None:
            player = self._cur
        hand = ",".join(card_str(c) for c in self._hands[player])
        seen = []
        for e in self._board:
            ident = card_str(e["card"]) if (not e["hidden"] or e["placer"] == player) else "??"
            owner = "Q" if e["owner"] is None else f"d{e['owner']}"
            seen.append(f"{ident}@{e['zone']}{owner}<p{e['placer']}")
        return f"P{player}|main:{hand}|board:{';'.join(seen)}"

    def _action_to_string(self, player, action):
        if player == pyspiel.PlayerId.CHANCE:
            return f"deal:P0={[card_str(c) for c in _DEALS[action]]}"
        qi, est, own_rel = _COMBOS[action]
        return f"a{action}(reine={'E' if est else 'D'})"

    def __str__(self):
        if self._cur == pyspiel.PlayerId.CHANCE:
            return "chance(deal)"
        b = ";".join(f"{card_str(e['card']) if not e['hidden'] else '??'}@{e['zone']}" for e in self._board)
        return f"cur={self._cur} board[{b}] term={self._terminal}"


pyspiel.register_game(_GAME_TYPE, CourtisansMiniGame)
