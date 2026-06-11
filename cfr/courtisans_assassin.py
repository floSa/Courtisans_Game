"""Courtisans-assassin — mini-instance avec Assassin + Garde (sous-jeu de ciblage).

Brique 2.1c (cf. rapport §32). On ajoute les rôles **Assassin** et **Garde** au
mini, ce qui introduit une **2ᵉ phase de décision** (l'assassin choisit sa victime)
— le « sous-jeu de ciblage » du vrai jeu.

Contrainte tabulaire : ajouter 2 rôles (→ 5 rôles, comme le jeu plein) ferait 15
cartes à 3 familles → ~16M états (oracle mort). On reste donc à **2 familles × 5
rôles = 10 cartes** pour garder l'oracle exact calculable et isoler le mécanisme.

Règles (cf. documentations/regles.md) :
  - Rôles : Noble(2), Espion(1, caché), Neutre(1), Garde(1), Assassin(1).
  - Un tour = poser 3 cartes (1 Reine Estime|Disgrâce, 1 domaine perso, 1 domaine
    adverse) — les 12 actions composites.
  - Quand un Assassin est posé, il TUE immédiatement une carte de SA zone (même
    Estime/Disgrâce chez la Reine, ou même domaine), qui n'est ni un Garde ni
    lui-même. Obligatoire s'il existe ≥1 cible valide ; sinon ne tue rien.
  - Assassins multiples d'un même tour : résolus séquentiellement.
  - Cartes tuées : retirées du décompte (influence et domaines).
  - Payoff = indicateur de victoire {+1, 0, −1}.

v1 : canon désactivé (identité) pour limiter les variables ; à ajouter ensuite.
"""
from itertools import combinations

import pyspiel

NOBLE, ESPION, NEUTRE, GARDE, ASSASSIN = 0, 1, 2, 3, 4
ROLE_NAME = {NOBLE: "N", ESPION: "E", NEUTRE: "U", GARDE: "G", ASSASSIN: "A"}
# v1 : on retire NEUTRE (valeur 1, sans effet, visible = redondant) pour garder
# l'oracle tabulaire calculable tout en conservant tous les mécanismes intéressants.
ROLES = (NOBLE, ESPION, GARDE, ASSASSIN)
NUM_ROLES = len(ROLES)
NUM_FAMILIES = 2

CARDS = [(f, r) for f in range(NUM_FAMILIES) for r in ROLES]
NUM_CARDS = len(CARDS)   # 10
HAND = 3


def card_value(r):
    return 2 if r == NOBLE else 1


def is_hidden(r):
    return r == ESPION


def card_str(cid):
    f, r = CARDS[cid]
    return f"{f}{ROLE_NAME[r]}"


# 12 actions composites : (idx carte Reine, Estime?, idx carte domaine perso parmi le reste).
_COMBOS = []
for _qi in range(3):
    for _est in (True, False):
        for _own_rel in range(2):
            _COMBOS.append((_qi, _est, _own_rel))

# Donnes : (main P0, main P1) ; reste hors-jeu face cachée. C(10,3)×C(7,3)=4200.
_DEALS = []
for _p0 in combinations(range(NUM_CARDS), HAND):
    _rest = [c for c in range(NUM_CARDS) if c not in set(_p0)]
    for _p1 in combinations(_rest, HAND):
        _DEALS.append((_p0, _p1))

# --- tenseur d'info-state (lossless) ---
ZONE_IDX = {"E": 0, "D": 1, "dom": 2}
# bloc carte board : card(nc+1) + zone(3) + owner(3) + placer(2) + dead(1)
SLOT = (NUM_CARDS + 1) + 3 + 3 + 2 + 1
MAX_SLOTS = 6                 # ≤ 3 (P0) + 3 (P1) cartes au board
# resolving assassin zone-key one-hot : Q-E, Q-D, dom0, dom1
RESOLV = 4
# [player2][phase2][hand nc][board MAX_SLOTS*SLOT][resolv RESOLV]
TENSOR_SIZE = 2 + 2 + NUM_CARDS + MAX_SLOTS * SLOT + RESOLV

_GAME_TYPE = pyspiel.GameType(
    short_name="courtisans_assassin",
    long_name="Courtisans Assassin",
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
    num_distinct_actions=len(_COMBOS),    # 12 (les actions de ciblage réutilisent 0..k-1 < 12)
    max_chance_outcomes=len(_DEALS),
    num_players=2,
    min_utility=-1.0,
    max_utility=1.0,
    utility_sum=0.0,
    max_game_length=9,                    # donne + P0(play+≤3 kills) + P1(play+≤3 kills)
)


def _zone_key(e):
    """Identifie la 'zone' d'une carte pour le ciblage assassin."""
    if e["owner"] is None:
        return ("Q", e["zone"])     # banquet : Estime vs Disgrâce
    return ("dom", e["owner"])      # domaine d'un joueur


class CourtisansAssassinGame(pyspiel.Game):
    def __init__(self, params=None):
        super().__init__(_GAME_TYPE, _GAME_INFO, params or {})

    def new_initial_state(self):
        return CourtisansAssassinState(self)


class CourtisansAssassinState(pyspiel.State):
    def __init__(self, game):
        super().__init__(game)
        self._hands = {0: [], 1: []}
        self._board = []            # dicts : card, zone, owner, placer, hidden, dead
        self._cur = pyspiel.PlayerId.CHANCE
        self._phase = "play"        # "play" | "target"
        self._pending = []          # indices board des assassins à résoudre (joueur courant)
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
            if _zone_key(e) == zk and CARDS[e["card"]][1] != GARDE:
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
        """Après une pose ou un kill : résout les assassins en attente (ceux sans
        cible valide sont sautés), sinon passe au joueur suivant / terminal."""
        while self._pending and not self._valid_targets(self._pending[0]):
            self._pending.pop(0)
        if self._pending:
            self._phase = "target"
            return
        self._phase = "play"
        if self._cur == 0:
            self._cur = 1
        else:
            self._terminal = True

    def _apply_action(self, action):
        if self._cur == pyspiel.PlayerId.CHANCE:
            p0, p1 = _DEALS[action]
            self._hands[0] = sorted(p0)
            self._hands[1] = sorted(p1)
            self._cur = 0
            self._phase = "play"
            return
        if self._phase == "target":
            victim = self._valid_targets(self._pending[0])[action]
            self._board[victim]["dead"] = True
            self._pending.pop(0)
            self._advance()
            return
        # phase "play" : coup composite
        player = self._cur
        qi, est, own_rel = _COMBOS[action]
        hand = self._hands[player]
        rem = [x for x in range(3) if x != qi]
        own_c = hand[rem[own_rel]]
        opp_c = hand[rem[1 - own_rel]]
        q_c = hand[qi]
        self._board.append(dict(card=q_c, zone=("E" if est else "D"),
                                owner=None, placer=player, hidden=is_hidden(CARDS[q_c][1]), dead=False))
        self._board.append(dict(card=own_c, zone="dom", owner=player,
                                placer=player, hidden=is_hidden(CARDS[own_c][1]), dead=False))
        self._board.append(dict(card=opp_c, zone="dom", owner=1 - player,
                                placer=player, hidden=is_hidden(CARDS[opp_c][1]), dead=False))
        self._hands[player] = []
        new = [len(self._board) - 3, len(self._board) - 2, len(self._board) - 1]
        self._pending = [i for i in new if CARDS[self._board[i]["card"]][1] == ASSASSIN]
        self._advance()

    # ---- scoring ----
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
    def _board_repr(self, player):
        out = []
        for e in self._board:
            visible = (not e["hidden"]) or (e["placer"] == player)
            ident = card_str(e["card"]) if visible else "??"
            owner = "Q" if e["owner"] is None else f"d{e['owner']}"
            dead = "!" if e["dead"] else ""
            out.append(f"{ident}{dead}@{e['zone']}{owner}<p{e['placer']}")
        return ";".join(out)

    def information_state_string(self, player=None):
        if player is None:
            player = self._cur
        hand = ",".join(card_str(c) for c in self._hands[player])
        s = f"P{player}|main:{hand}|board:{self._board_repr(player)}"
        if self._phase == "target":
            zk = _zone_key(self._board[self._pending[0]])
            s += f"|kill@{zk[0]}{zk[1]}"
        return s

    def information_state_tensor(self, player=None):
        if player is None:
            player = self._cur
        nc = NUM_CARDS
        v = [0.0] * TENSOR_SIZE
        v[player] = 1.0
        v[2 + (1 if self._phase == "target" else 0)] = 1.0
        base_hand = 4
        for c in self._hands[player]:
            v[base_hand + c] = 1.0
        base = base_hand + nc
        for i, e in enumerate(self._board[:MAX_SLOTS]):
            off = base + i * SLOT
            known = (not e["hidden"]) or (e["placer"] == player)
            v[off + (e["card"] if known else nc)] = 1.0                 # card (nc+1)
            v[off + (nc + 1) + ZONE_IDX[e["zone"]]] = 1.0               # zone (3)
            owner_i = 0 if e["owner"] is None else e["owner"] + 1
            v[off + (nc + 1 + 3) + owner_i] = 1.0                       # owner (3)
            v[off + (nc + 1 + 3 + 3) + e["placer"]] = 1.0              # placer (2)
            if e["dead"]:
                v[off + (nc + 1 + 3 + 3 + 2)] = 1.0                    # dead (1)
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
        return f"cur={self._cur} phase={self._phase} board[{self._board_repr(0)}] term={self._terminal}"


pyspiel.register_game(_GAME_TYPE, CourtisansAssassinGame)


def make_game():
    return CourtisansAssassinGame()
