import random
import numpy as np
import copy
from enum import IntEnum
from itertools import permutations

# ======================================================================================
# 1. CONFIGURATION & CONSTANTES
# ======================================================================================
NUM_FAMILLES = 6
NUM_ROLES = 5
NUM_CARD_TYPES = NUM_FAMILLES * NUM_ROLES

class Famille(IntEnum):
    F1 = 0; F2 = 1; F3 = 2; F4 = 3; F5 = 4; F6 = 5

class Role(IntEnum):
    ASSASSIN = 0; GARDE = 1; NOBLE = 2; ESPION = 3; NEUTRE = 4

class Zone(IntEnum):
    REINE = 0; SOI = 1; ADV = 2

# ======================================================================================
# 2. LOGIQUE DE JEU
# ======================================================================================
class Carte:
    def __init__(self, famille, role, uid):
        self.famille = famille
        self.role = role
        self.id = uid
        self.valeur = 2 if role == Role.NOBLE else 1
        self.proprietaire_idx = -1 # -1 pour Reine/Deck
        self.visible = False
        self.position = None # 'Estime', 'Disgrace' pour Reine
        self.domaine_id = -1
        
        # Pour le tri
        self.sort_key = (famille * NUM_ROLES) + role

    @property
    def vector_id(self):
        return self.famille * NUM_ROLES + self.role

    def __repr__(self):
        return f"[{Famille(self.famille).name}-{Role(self.role).name}]"

    def copy(self):
        c = Carte(self.famille, self.role, self.id)
        c.proprietaire_idx = self.proprietaire_idx
        c.visible = self.visible
        c.position = self.position
        c.domaine_id = self.domaine_id
        return c

class ActionMapper:
    """
    Gère le mapping entre un index d'action unique (pour l'IA)
    et la sémantique du jeu (qui joue quoi où).
    
    Structure de l'action :
    1. Permutation des 3 cartes en main : 6 possibilités.
       (Carte A, Carte B, Carte C) -> (Reine, Soi, Adv) ou (Reine, Adv, Soi) etc.
    2. Choix Reine : Estime (0) ou Disgrâce (1) -> 2 possibilités.
    3. Choix Cible Adversaire : Index relatif parmi les N-1 adversaires.
    
    Total Actions = 6 * 2 * (N-1)
    """
    def __init__(self, num_players):
        self.num_players = num_players
        self.perms = list(permutations([0, 1, 2])) # Les indices de la main triée
        # Ex: (0, 1, 2) signifie:
        # - Carte 0 de la main -> Reine
        # - Carte 1 de la main -> Soi
        # - Carte 2 de la main -> Adv
        
    def get_action_space_size(self):
        return 6 * 2 * (self.num_players - 1)

    def decode(self, action_idx):
        # 1. Target Adversaire (le reste de la division)
        nb_adv = self.num_players - 1
        target_relative_idx = action_idx % nb_adv
        remainder = action_idx // nb_adv
        
        # 2. Reine Position (Estime/Disgrace)
        queen_pos_idx = remainder % 2 # 0 ou 1
        queen_pos = 'Estime' if queen_pos_idx == 0 else 'Disgrace'
        remainder = remainder // 2
        
        # 3. Permutation
        perm_idx = remainder % 6
        perm = self.perms[perm_idx] # Ex: (2, 0, 1) -> Main[2]=>Reine, Main[0]=>Soi, Main[1]=>Adv
        
        return perm, queen_pos, target_relative_idx

class GameEnv:
    def __init__(self, num_players=2):
        self.num_players = num_players
        self.mapper = ActionMapper(num_players)
        self.pending_assassin_context = None # Contexte si intervention manuelle requise
        self.reset()

    def reset(self):
        # Création Deck
        self.cartes = []
        uid = 0
        # Création Deck (3 exemplaires de chaque carte)
        self.cartes = []
        uid = 0
        for _ in range(3):
            for f in range(NUM_FAMILLES):
                for r in range(NUM_ROLES):
                    self.cartes.append(Carte(f, r, uid))
                    uid += 1
        
        self.deck_indices = list(range(len(self.cartes)))
        random.shuffle(self.deck_indices)
        self.plateau_indices = [] # Cartes posées
        self.current_player = 0
        self.mains = {i: [] for i in range(self.num_players)} 
        self._piocher(self.current_player)
        return self

    def _piocher(self, p_idx):
        # On complète la main à 3 cartes
        needed = 3 - len(self.mains[p_idx])
        for _ in range(needed):
            if self.deck_indices:
                self.mains[p_idx].append(self.deck_indices.pop())
        # TRI OBLIGATOIRE pour la cohérence des permutations
        # La main est toujours vue triée par l'IA (et par action_mapper)
        self.mains[p_idx].sort(key=lambda idx: self.cartes[idx].sort_key)

    def get_legal_actions(self):
        # Dans ce jeu, tant qu'on a 3 cartes, toutes les permutations sont valides.
        # Si fin de partie (moins de 3 cartes), on gèrera le cas limite (ou fin).
        if len(self.mains[self.current_player]) < 3:
            return [] # Ne devrait pas arriver sauf toute fin
        return list(range(self.mapper.get_action_space_size()))

    def step(self, action_idx):
        """
        Joue un tour complet.
        action_idx : int entre 0 et ActionSize
        """
        # 1. Décodage
        perm, queen_pos, target_relative_idx = self.mapper.decode(action_idx)
        
        hand_indices = self.mains[self.current_player]
        if len(hand_indices) < 3:
             # Fin de partie prématurée ou bug
             return self.get_state_vector(), 0, True, {}

        # Les cartes sont jouées dans l'ordre défini par la permutation
        # perm[0] -> Reine
        # perm[1] -> Soi
        # perm[2] -> Adversaire
        
        # On récupère les indices réels des cartes
        c_reine_idx = hand_indices[perm[0]]
        c_soi_idx = hand_indices[perm[1]]
        c_adv_idx = hand_indices[perm[2]]
        
        # Calcul de l'ID réel de l'adversaire visé
        # target_relative 0 -> prochain joueur, 1 -> celui d'après...
        target_abs_idx = (self.current_player + 1 + target_relative_idx) % self.num_players
        
        # --- APPLICATION REINE ---
        c_reine = self.cartes[c_reine_idx]
        c_reine.position = queen_pos
        c_reine.visible = True
        c_reine.proprietaire_idx = -1 # Appartient à la cour
        self.plateau_indices.append(c_reine_idx)
        
        # --- APPLICATION SOI ---
        c_soi = self.cartes[c_soi_idx]
        c_soi.domaine_id = self.current_player
        c_soi.position = None
        c_soi.proprietaire_idx = self.current_player
        c_soi.visible = (c_soi.role != Role.ESPION) # Espion caché
        self.plateau_indices.append(c_soi_idx)
        
        # --- APPLICATION ADV ---
        c_adv = self.cartes[c_adv_idx]
        c_adv.domaine_id = target_abs_idx
        c_adv.position = None
        c_adv.proprietaire_idx = target_abs_idx
        c_adv.visible = (c_adv.role != Role.ESPION)
        self.plateau_indices.append(c_adv_idx)
        
        # Vidage main
        self.mains[self.current_player] = []
        
        # --- EFFETS ASSASSIN ---
        # Si une des cartes jouées est un Assassin, il tue.
        jouees = [c_reine, c_soi, c_adv]
        
        # Gestion Assassins
        # On doit gérer le cas où le joueur humain joue un Assassin -> Intervention Manuelle
        assassin_pending = False
        
        for c in jouees:
            if c.role == Role.ASSASSIN:
                if self.current_player == 0: # Joueur Humain
                    targets = self._get_valid_assassin_targets(c)
                    if targets:
                        # On sauvegarde le contexte et on met en pause
                        self.pending_assassin_context = {
                            "assassin_card": c,
                            "targets": targets,
                            "remaining_jouees": [] # Pour gérer multiples assassins ? (Simplification: On gère le premier trouvé)
                        }
                        assassin_pending = True
                        break # On s'arrête au premier assassin qui demande une intervention
                    else:
                        # Pas de cible, rien ne se passe (ou auto resolve vide)
                        pass
                else:
                    self._resolve_assassin_auto(c)

        if assassin_pending:
            return self.get_state_vector(), 0, False, {"assassin_pending": True}

        # --- FIN DE TOUR ---
        return self._finish_turn()

    def _finish_turn(self):
        # Piocher pour le prochain joueur si ce n'est pas déjà fait
        # (Dans ce jeu on pioche au début de son tour, ou fin du précédent, peu importe)
        # Check fin de partie : Si plus de pioche
        done = False
        if not self.deck_indices:
            done = True
        
        reward = 0
        if done:
            scores = self._calcul_scores()
            if self.num_players == 2:
                reward = (scores[0] - scores[1]) / 20.0
            else:
                my_score = scores[self.current_player]
                avg_others = sum(s for i,s in scores.items() if i != self.current_player) / (self.num_players - 1)
                reward = (my_score - avg_others) / 20.0
        
        if not done:
            self.current_player = (self.current_player + 1) % self.num_players
            self._piocher(self.current_player)

        return self.get_state_vector(), reward, done, {}

    def resolve_assassin_manual(self, victim_idx):
        """Appelé par l'UI pour résoudre l'assassinat en attente"""
        if not self.pending_assassin_context:
            return # Should not happen
            
        if victim_idx in self.pending_assassin_context["targets"]:
            self.plateau_indices.remove(victim_idx)
            # La carte victime est retirée
            
        self.pending_assassin_context = None
        # On reprend le fil normal (Check fin de tour)
        # Note: S'il y avait un 2ème assassin joué dans le même tour, il est ignoré ici par simplification.
        return self._finish_turn()

    def _get_valid_assassin_targets(self, assassin_card):
        targets = []
        for i in self.plateau_indices:
            c = self.cartes[i]
            if c.id == assassin_card.id: continue
            if c.role in [Role.GARDE, Role.ASSASSIN]: continue
            
            match = False
            # Cas Reine
            if assassin_card.position is not None: 
                if c.position == assassin_card.position: match = True
            # Cas Domaine
            elif assassin_card.domaine_id != -1:
                if c.domaine_id == assassin_card.domaine_id: match = True
            
            if match: targets.append(i)
        return targets

    def _resolve_assassin_auto(self, assassin_card):
        # Cible valide :
        # - Pas l'assassin lui-même
        # - Pas Garde, Pas Assassin (protégés)
        # - Si Assassin chez Reine : Tue dans MEME zone (Estime/Disgrace)
        # - Si Assassin chez Joueur : Tue dans le MEME domaine
        
        targets = []
        for i in self.plateau_indices:
            c = self.cartes[i]
            if c.id == assassin_card.id: continue
            if c.role in [Role.GARDE, Role.ASSASSIN]: continue
            
            match = False
            # Cas Reine
            if assassin_card.position is not None: 
                if c.position == assassin_card.position: match = True
            # Cas Domaine
            elif assassin_card.domaine_id != -1:
                if c.domaine_id == assassin_card.domaine_id: match = True
            
            if match: targets.append(i)
        
        if targets:
            victim_idx = random.choice(targets)
            self.plateau_indices.remove(victim_idx)
            # La carte victime est retirée du jeu (défausse)

    def _calcul_scores(self):
        # 1. Influence des familles
        infl = {f: 0 for f in range(NUM_FAMILLES)}
        for i in self.plateau_indices:
            c = self.cartes[i]
            if c.position == 'Estime': infl[c.famille] += 1 # Nombre de cartes ? Ou valeur ?
            # Règle : "Majorité". On compte les cartes ? 
            # Règle MD : "majoritairement dans la lumière". Donc compte.
            elif c.position == 'Disgrace': infl[c.famille] -= 1
        
        # 2. Points
        scores = {p: 0 for p in range(self.num_players)}
        for i in self.plateau_indices:
            c = self.cartes[i]
            if c.domaine_id != -1 and c.visible:
                # La famille est-elle Lumière (>0) ou Obscurité (<0) ?
                fam_stat = infl[c.famille]
                val = c.valeur
                
                if fam_stat > 0: scores[c.domaine_id] += val
                elif fam_stat < 0: scores[c.domaine_id] -= val
                # Si neutre (0), 0 points
                
        return scores

    def get_state_vector(self):
        # Encodage pour le NN.
        # On doit avoir une taille FIXE. Mais N joueurs varie.
        # Solution: On encode toujours jusqu'au MAX de joueurs (ex 5) avec padding ?
        # Ou on génère dynamiquement selon l'instance. Le NN s'adaptera lors de l'init.
        
        # Structure vecteur :
        # 1. Reine Estime : [OneHot Famille+Role] cumulés (Multi-Hot avec 'intensite')
        # 2. Reine Disgrace : idem
        # 3. Moi (Joueur Courant) : idem
        # 4. Adv 1 : idem
        # ...
        # 5. Adv N-1 : idem
        # 6. Ma Main : idem (3 cartes)
        
        total_zones = 2 + 1 + (self.num_players - 1) # Reine(2) + Moi + Advs
        # Pour simplifier, on utilise une matrice aplatie
        # Size = (TotalZones * NUM_CARD_TYPES) + (3 * NUM_CARD_TYPES) ?
        # Non, pour la main, c'est mieux d'avoir 3 slots de carte (car on joue Carte 1, 2 ou 3)
        # Mais on a trié la main ! Donc Slot 1 = Petite carte, Slot 3 = Grande carte.
        
        vec_size = (total_zones * NUM_CARD_TYPES) + NUM_CARD_TYPES # Main agrégée aussi
        # Note : Encoder la main en "slots" (3 * 30) ou en "count" (1 * 30) ?
        # Count est mieux invariant par permutation, mais ici l'ordre compte pour l'action mapper (0,1,2).
        # Comme on a trié, l'ordre est déterministe.
        # Utilisons "Count" pour la main aussi pour simplifier l'entrée (30 floats).
        # L'IA saura que ses actions 0..5 tapent dans les indices triés.
        
        vec = np.zeros(vec_size, dtype=np.float32)
        
        def fill(offset_zone, card_vec_id):
            idx = offset_zone * NUM_CARD_TYPES + card_vec_id
            vec[idx] += 1
            
        # Plateau
        for i in self.plateau_indices:
            c = self.cartes[i]
            vid = c.vector_id
            
            if c.position == 'Estime': fill(0, vid)
            elif c.position == 'Disgrace': fill(1, vid)
            elif c.domaine_id != -1:
                # Il faut relativiser les indices domaines par rapport au joueur courant
                # Moi = 0 relatif. Adv suivant = 1 relatif...
                owner = c.domaine_id
                rel_owner = (owner - self.current_player) % self.num_players
                
                # Zone 2 = Moi (rel 0). Zone 3 = Adv 1 (rel 1)...
                zone_idx = 2 + rel_owner
                
                # Visibilité : Je vois mes cartes, je vois les visibles des autres.
                # Je ne vois pas les cachées des autres.
                visible = True
                if owner != self.current_player and not c.visible:
                    visible = False
                    
                if visible:
                    fill(zone_idx, vid)
                    
        # Main
        main_zone_idx = total_zones
        for i in self.mains[self.current_player]:
            c = self.cartes[i]
            fill(main_zone_idx, c.vector_id)
            
        return vec
    
    def get_state_vector_size(self):
        # 2 (Reine) + N (Joueurs) 
        nb_zones_board = 2 + self.num_players
        # + 1 (Main)
        total = nb_zones_board + 1
        return total * NUM_CARD_TYPES

    def clone_determinized(self):
        """Simulation information parfaite pour MCTS (Oracle)"""
        # Pour l'instant on fait une copie parfaite (triche)
        # C'est standard pour AlphaZero débutant.
        return copy.deepcopy(self)

if __name__ == "__main__":
    # Test rapide
    env = GameEnv(num_players=2)
    print(f"Action Space Size (2p): {env.mapper.get_action_space_size()}") # 12
    print(f"State Vector Size: {env.get_state_vector_size()}")
    
    s, r, d, _ = env.step(0) # Joue action 0
    print(f"Step done. Reward: {r}, Done: {d}")