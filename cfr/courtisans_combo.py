"""Courtisans-combo — assassins + 2 manches avec pioche (brique 2.1e).

Combine les deux mécanismes validés séparément (2.1c assassins, 2.1d pioche)
dans une même instance : la dernière marche de validation avec oracle exact
avant le jeu complet.

Structure : 3 familles × 3 rôles {Noble(2), Espion(caché,1), Assassin(1)} = 9
cartes (le Garde de 2.1c est laissé de côté : il ne fait que restreindre les
cibles ; le mécanisme à valider est le ciblage × l'horizon long).
  - Donne : main P0 (3) × main P1 (3) → 1680 ; les 3 restantes = pioche.
  - Manche 1 : P0 joue (12 actions composites) puis résout ses assassins
    (phase "target", comme 2.1c) ; idem P1.
  - Manche 2 : P0 pioche les 3 restantes, joue, résout. Terminal.
  - L'espion posé reste face cachée pour l'adversaire ; un assassin peut tuer
    une carte cachée (présence publique, identité non).

Canonicalisation par symétrie des familles intégrée (méthode 2.1b/2.1d),
toggle COURTISANS_CANON (défaut on).
"""
import os
from itertools import combinations, permutations

import pyspiel

NOBLE, ESPION, ASSASSIN = 0, 1, 2
ROLE_NAME = {NOBLE: "N", ESPION: "E", ASSASSIN: "A"}
NUM_FAMILIES = 3

CANON = os.environ.get("COURTISANS_CANON", "1") == "1"

CARDS = [(f, r) for f in range(NUM_FAMILIES) for r in (NOBLE, ESPION, ASSASSIN)]
NUM_CARDS = len(CARDS)   # 9
HAND = 3

_FAMILY_PERMS = list(permutations(range(NUM_FAMILIES)))
_IDENTITY_PERM = tuple(range(NUM_FAMILIES))
_CANON_CACHE = {}


def _relabel(cid, perm):
    f, r = divmod(cid, 3)
    return perm[f] * 3 + r


def card_value(r):
    return 2 if r == NOBLE else 1


def is_hidden(r):
    return r == ESPION


def card_str(cid):
    f, r = CARDS[cid]
    return f"{f}{ROLE_NAME[r]}"


_COMBOS = []
for _qi in range(3):
    for _est in (True, False):
        for _own_rel in range(2):
            _COMBOS.append((_qi, _est, _own_rel))

_DEALS = []
for _p0 in combinations(range(NUM_CARDS), HAND):
    _rest = [c for c in range(NUM_CARDS) if c not in set(_p0)]
    for _p1 in combinations(_rest, HAND):
        _DEALS.append((_p0, _p1))

ZONE_IDX = {"E": 0, "D": 1, "dom": 2}
SLOT = (NUM_CARDS + 1) + 3 + 3 + 2 + 1   # card(+inconnu) + zone + owner + placer + dead
# 9 et non 6 : les ciblages de la manche 2 se décident board complet (9 cartes).
# (Au redeal, 6 suffisait : aucune DÉCISION ne s'y prend à plus de 6 cartes posées.)
MAX_SLOTS = 9
RESOLV = 4   # zone-clé de l'assassin en résolution : Q-E, Q-D, dom0, dom1
# [player2][manche2][phase2][main nc][board][resolv]
TENSOR_SIZE = 2 + 2 + 2 + NUM_CARDS + MAX_SLOTS * SLOT + RESOLV

_GAME_TYPE = pyspiel.GameType(
    short_name="courtisans_combo",
    long_name="Courtisans Combo",
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
    num_distinct_actions=len(_COMBOS),   # les ciblages réutilisent 0..k-1 < 12
    max_chance_outcomes=len(_DEALS),
    num_players=2,
    min_utility=-1.0,
    max_utility=1.0,
    utility_sum=0.0,
    max_game_length=13,   # donne + 3 poses + ≤9 kills
)


def _zone_key(e):
    if e["owner"] is None:
        return ("Q", e["zone"])
    return ("dom", e["owner"])


class CourtisansComboGame(pyspiel.Game):
    def __init__(self, params=None):
        super().__init__(_GAME_TYPE, _GAME_INFO, params or {})

    def new_initial_state(self):
        return CourtisansComboState(self)


class CourtisansComboState(pyspiel.State):
    def __init__(self, game):
        super().__init__(game)
        self._hands = {0: [], 1: []}
        self._draw = []
        self._board = []          # card, zone, owner, placer, hidden, dead
        self._cur = pyspiel.PlayerId.CHANCE
        self._round = 1
        self._phase = "play"      # "play" | "target"
        self._pending = []        # indices board des assassins à résoudre
        self._terminal = False

    # ---- mécanique ----
    def current_player(self):
        if self._terminal:
            return pyspiel.PlayerId.TERMINAL
        return self._cur

    def _valid_targets(self, a_idx):
        a = self._board[a_idx]
        zk = _zone_key(a)
        out = []
        for i, e in enumerate(self._board):
            if i == a_idx or e["dead"]:
                continue
            if _zone_key(e) == zk:
                out.append(i)
        return out

    def _legal_actions(self, player):
        if self._phase == "target":
            return list(range(len(self._valid_targets(self._pending[0]))))
        return list(range(len(_COMBOS)))

    def chance_outcomes(self):
        p = 1.0 / len(_DEALS)
        return [(i, p) for i in range(len(_DEALS))]

    def _advance(self):
        """Résout la file d'assassins (saute ceux sans cible), sinon passe au
        tour suivant : P0 m1 → P1 m1 → P0 pioche + m2 → terminal."""
        while self._pending and not self._valid_targets(self._pending[0]):
            self._pending.pop(0)
        if self._pending:
            self._phase = "target"
            return
        self._phase = "play"
        if self._cur == 0 and self._round == 1:
            self._cur = 1
        elif self._cur == 1:
            self._hands[0] = list(self._draw)
            self._draw = []
            self._round = 2
            self._cur = 0
        else:
            self._terminal = True

    def _apply_action(self, action):
        if self._cur == pyspiel.PlayerId.CHANCE:
            p0, p1 = _DEALS[action]
            dealt = set(p0) | set(p1)
            self._hands[0] = sorted(p0)
            self._hands[1] = sorted(p1)
            self._draw = sorted(c for c in range(NUM_CARDS) if c not in dealt)
            self._cur = 0
            return
        if self._phase == "target":
            victim = self._valid_targets(self._pending[0])[action]
            self._board[victim]["dead"] = True
            self._pending.pop(0)
            self._advance()
            return
        player = self._cur
        qi, est, own_rel = _COMBOS[action]
        # Actions interprétées dans l'ordre canonique de la main (cf. §31).
        perm = self._canon_perm(player)
        hand = sorted(self._hands[player], key=lambda c: _relabel(c, perm))
        rem = [x for x in range(3) if x != qi]
        own_c = hand[rem[own_rel]]
        opp_c = hand[rem[1 - own_rel]]
        q_c = hand[qi]
        self._board.append(dict(card=q_c, zone=("E" if est else "D"),
                                owner=None, placer=player,
                                hidden=is_hidden(CARDS[q_c][1]), dead=False))
        self._board.append(dict(card=own_c, zone="dom", owner=player,
                                placer=player, hidden=is_hidden(CARDS[own_c][1]), dead=False))
        self._board.append(dict(card=opp_c, zone="dom", owner=1 - player,
                                placer=player, hidden=is_hidden(CARDS[opp_c][1]), dead=False))
        self._hands[player] = []
        new = [len(self._board) - 3, len(self._board) - 2, len(self._board) - 1]
        self._pending = [i for i in new if CARDS[self._board[i]["card"]][1] == ASSASSIN]
        self._advance()

    # ---- scoring (morts exclus) ----
    def _scores(self):
        infl = {f: 0 for f in range(NUM_FAMILIES)}
        for e in self._board:
            if e["dead"]:
                continue
            f = CARDS[e["card"]][0]
            if e["zone"] == "E":
                infl[f] += 1
            elif e["zone"] == "D":
                infl[f] -= 1
        score = {0: 0, 1: 0}
        for e in self._board:
            if e["dead"] or e["zone"] != "dom":
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
    def _repr(self, player, perm):
        hand = ",".join(sorted(card_str(_relabel(c, perm)) for c in self._hands[player]))
        seen = []
        for e in self._board:
            visible = (not e["hidden"]) or (e["placer"] == player)
            ident = card_str(_relabel(e["card"], perm)) if visible else "??"
            owner = "Q" if e["owner"] is None else f"d{e['owner']}"
            dead = "!" if e["dead"] else ""
            seen.append(f"{ident}{dead}@{e['zone']}{owner}<p{e['placer']}")
        s = f"P{player}|m{self._round}|main:{hand}|board:{';'.join(seen)}"
        if self._phase == "target":
            zk = _zone_key(self._board[self._pending[0]])
            s += f"|kill@{zk[0]}{zk[1]}"
        return s

    def _canon_perm(self, player):
        """Perm canonique de la vue (cf. mini §31). Le suffixe kill@zone est
        invariant par relabel (les zones ne portent pas de famille) → il
        n'influence pas l'argmin mais fait partie de la clé de cache."""
        if not CANON:
            return _IDENTITY_PERM
        key = (player, self._round, self._phase,
               self._pending[0] if self._phase == "target" else -1,
               tuple(self._hands[player]),
               tuple(((e["card"] if (not e["hidden"] or e["placer"] == player) else -1),
                      e["zone"], e["owner"], e["placer"], e["dead"]) for e in self._board))
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
        """Encodage lossless : [player2][manche2][phase2][main][board][resolv]."""
        if player is None:
            player = self._cur
        nc = NUM_CARDS
        perm = self._canon_perm(player)
        v = [0.0] * TENSOR_SIZE
        v[player] = 1.0
        v[2 + (self._round - 1)] = 1.0
        v[4 + (1 if self._phase == "target" else 0)] = 1.0
        base_hand = 6
        for c in self._hands[player]:
            v[base_hand + _relabel(c, perm)] = 1.0
        base = base_hand + nc
        for i, e in enumerate(self._board[:MAX_SLOTS]):
            off = base + i * SLOT
            known = (not e["hidden"]) or (e["placer"] == player)
            v[off + (_relabel(e["card"], perm) if known else nc)] = 1.0
            v[off + (nc + 1) + ZONE_IDX[e["zone"]]] = 1.0
            owner_i = 0 if e["owner"] is None else e["owner"] + 1
            v[off + (nc + 1 + 3) + owner_i] = 1.0
            v[off + (nc + 1 + 3 + 3) + e["placer"]] = 1.0
            if e["dead"]:
                v[off + (nc + 1 + 3 + 3 + 2)] = 1.0
        if self._phase == "target":
            zk = _zone_key(self._board[self._pending[0]])
            ridx = {("Q", "E"): 0, ("Q", "D"): 1, ("dom", 0): 2, ("dom", 1): 3}[zk]
            v[base + MAX_SLOTS * SLOT + ridx] = 1.0
        return v

    def _action_to_string(self, player, action):
        if player == pyspiel.PlayerId.CHANCE:
            p0, p1 = _DEALS[action]
            return f"deal:P0={[card_str(c) for c in p0]}|P1={[card_str(c) for c in p1]}"
        if self._phase == "target":
            victim = self._valid_targets(self._pending[0])[action]
            return f"kill:{card_str(self._board[victim]['card'])}@idx{victim}"
        qi, est, own_rel = _COMBOS[action]
        return f"a{action}(reine={'E' if est else 'D'})"

    def __str__(self):
        if self._cur == pyspiel.PlayerId.CHANCE:
            return "chance(deal)"
        b = ";".join(f"{card_str(e['card']) if not e['hidden'] else '??'}{'!' if e['dead'] else ''}@{e['zone']}"
                     for e in self._board)
        return f"cur={self._cur} m{self._round} {self._phase} board[{b}] term={self._terminal}"


pyspiel.register_game(_GAME_TYPE, CourtisansComboGame)


def make_game():
    return CourtisansComboGame()
