"""Courtisans-redeal — mini-instance à 2 manches avec pioche (brique 2.2).

On ajoute au mini 3-familles la **2ᵉ manche avec pioche** : l'horizon s'allonge
(3 décisions au lieu de 2), le board grossit en cours de partie et un joueur
rejoue avec des cartes piochées — le mécanisme « multi-manches » du vrai jeu,
isolé de tout le reste (pas d'assassins : un mécanisme à la fois).

Structure : 3 familles × 3 rôles {Noble(2), Espion(caché,1), Simple(1)} = 9 cartes.
  - Donne : main P0 (3) × main P1 (3) → C(9,3)×C(6,3) = 1680 ; les 3 restantes
    forment la **pioche** (face cachée).
  - Manche 1 : P0 joue ses 3 cartes (12 actions composites), puis P1 les siennes.
  - Manche 2 : P0 pioche les 3 cartes restantes et les joue (12 actions).
    La pioche est déterminée par la donne (pas de nœud de chance en cours de
    partie) mais reste de l'information PRIVÉE : P1 ne peut l'inférer que
    partiellement (les espions de P0 posés face cachée brouillent son comptage).
  - Asymétrie assumée (P0 joue 2 manches, P1 une) : c'est la plus petite
    instance qui exhibe le mécanisme en gardant l'oracle tabulaire vivant.

Taille : 1 + 1680×(1 + 12 + 144 + 1728) = 3 166 801 états (≈12× le mini 3fam).
Scoring et payoff identiques au mini (majorité d'influence, victoire {+1,0,−1}).

v1 : canon désactivé (identité) pour limiter les variables ; à ajouter ensuite.
"""
from itertools import combinations

import pyspiel

NOBLE, ESPION, SIMPLE = 0, 1, 2
ROLE_NAME = {NOBLE: "N", ESPION: "E", SIMPLE: "S"}
NUM_FAMILIES = 3

CARDS = [(f, r) for f in range(NUM_FAMILIES) for r in (NOBLE, ESPION, SIMPLE)]
NUM_CARDS = len(CARDS)   # 9
HAND = 3


def card_value(r):
    return 2 if r == NOBLE else 1


def is_hidden(r):
    return r == ESPION


def card_str(cid):
    f, r = CARDS[cid]
    return f"{f}{ROLE_NAME[r]}"


# Les 12 actions composites : (idx carte Reine, Estime?, idx carte domaine perso).
_COMBOS = []
for _qi in range(3):
    for _est in (True, False):
        for _own_rel in range(2):
            _COMBOS.append((_qi, _est, _own_rel))

# Donnes : (main P0, main P1) ; les 3 restantes = pioche de la manche 2.
_DEALS = []
for _p0 in combinations(range(NUM_CARDS), HAND):
    _rest = [c for c in range(NUM_CARDS) if c not in set(_p0)]
    for _p1 in combinations(_rest, HAND):
        _DEALS.append((_p0, _p1))

# Géométrie du tenseur d'info-state (lossless, même schéma que le mini).
ZONE_IDX = {"E": 0, "D": 1, "dom": 2}
SLOT = (NUM_CARDS + 1) + 3 + 3 + 2   # card(+inconnu) + zone + owner + placer
MAX_SLOTS = 6                        # ≤ 6 cartes posées à un point de décision
# [player2][manche2][main nc][board MAX_SLOTS*SLOT]
TENSOR_SIZE = 2 + 2 + NUM_CARDS + MAX_SLOTS * SLOT

_GAME_TYPE = pyspiel.GameType(
    short_name="courtisans_redeal",
    long_name="Courtisans Redeal",
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
    num_distinct_actions=len(_COMBOS),
    max_chance_outcomes=len(_DEALS),
    num_players=2,
    min_utility=-1.0,
    max_utility=1.0,
    utility_sum=0.0,
    max_game_length=4,   # donne + P0 + P1 + P0(manche 2)
)


class CourtisansRedealGame(pyspiel.Game):
    def __init__(self, params=None):
        super().__init__(_GAME_TYPE, _GAME_INFO, params or {})

    def new_initial_state(self):
        return CourtisansRedealState(self)


class CourtisansRedealState(pyspiel.State):
    def __init__(self, game):
        super().__init__(game)
        self._hands = {0: [], 1: []}
        self._draw = []           # pioche (cartes restantes de la donne)
        self._board = []          # dicts : card, zone('E'|'D'|'dom'), owner, placer, hidden
        self._cur = pyspiel.PlayerId.CHANCE
        self._round = 1           # 1 = manche 1, 2 = manche 2 (P0 a repioché)
        self._terminal = False

    # ---- mécanique ----
    def current_player(self):
        if self._terminal:
            return pyspiel.PlayerId.TERMINAL
        return self._cur

    def _legal_actions(self, player):
        return list(range(len(_COMBOS)))   # la main fait toujours 3

    def chance_outcomes(self):
        p = 1.0 / len(_DEALS)
        return [(i, p) for i in range(len(_DEALS))]

    def _apply_action(self, action):
        if self._cur == pyspiel.PlayerId.CHANCE:
            p0, p1 = _DEALS[action]
            dealt = set(p0) | set(p1)
            self._hands[0] = sorted(p0)
            self._hands[1] = sorted(p1)
            self._draw = sorted(c for c in range(NUM_CARDS) if c not in dealt)
            self._cur = 0
            return
        player = self._cur
        qi, est, own_rel = _COMBOS[action]
        hand = sorted(self._hands[player])
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
        if player == 0 and self._round == 1:
            self._cur = 1
        elif player == 1:
            # Manche 2 : P0 pioche les 3 cartes restantes et rejoue.
            self._hands[0] = list(self._draw)
            self._draw = []
            self._round = 2
            self._cur = 0
        else:                      # P0 vient de jouer la manche 2
            self._terminal = True

    # ---- scoring (identique au mini) ----
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

    # ---- information ----
    # Rappel parfait : la main passée d'un joueur est intégralement sur le board,
    # visible de lui (placer == lui), et l'action jouée se lit dans les zones.
    def information_state_string(self, player=None):
        if player is None:
            player = self._cur
        hand = ",".join(card_str(c) for c in sorted(self._hands[player]))
        seen = []
        for e in self._board:
            visible = (not e["hidden"]) or (e["placer"] == player)
            ident = card_str(e["card"]) if visible else "??"
            owner = "Q" if e["owner"] is None else f"d{e['owner']}"
            seen.append(f"{ident}@{e['zone']}{owner}<p{e['placer']}")
        return f"P{player}|m{self._round}|main:{hand}|board:{';'.join(seen)}"

    def information_state_tensor(self, player=None):
        """Encodage lossless (même contenu que la string).

        Layout (TENSOR_SIZE dims) :
          [0:2]   perspective (one-hot p0/p1)
          [2:4]   manche (one-hot m1/m2)
          [4:4+NUM_CARDS] main : multi-hot
          puis MAX_SLOTS blocs de SLOT dims (board, ordre de pose) :
            card NUM_CARDS+1 (+1 = espion adverse caché), zone 3, owner 3, placer 2.
        """
        if player is None:
            player = self._cur
        nc = NUM_CARDS
        v = [0.0] * TENSOR_SIZE
        v[player] = 1.0
        v[2 + (self._round - 1)] = 1.0
        for c in self._hands[player]:
            v[4 + c] = 1.0
        base = 4 + nc
        for i, e in enumerate(self._board[:MAX_SLOTS]):
            off = base + i * SLOT
            known = (not e["hidden"]) or (e["placer"] == player)
            v[off + (e["card"] if known else nc)] = 1.0          # card (nc+1)
            v[off + (nc + 1) + ZONE_IDX[e["zone"]]] = 1.0        # zone (3)
            owner_i = 0 if e["owner"] is None else e["owner"] + 1
            v[off + (nc + 1 + 3) + owner_i] = 1.0                # owner (3)
            v[off + (nc + 1 + 3 + 3) + e["placer"]] = 1.0        # placer (2)
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
        b = ";".join(f"{card_str(e['card']) if not e['hidden'] else '??'}@{e['zone']}"
                     for e in self._board)
        return f"cur={self._cur} m{self._round} board[{b}] term={self._terminal}"


pyspiel.register_game(_GAME_TYPE, CourtisansRedealGame)


def make_game():
    return CourtisansRedealGame()
