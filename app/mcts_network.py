import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
import os
import random
from collections import deque
import datetime
from app.jeu import GameEnv # Import du moteur de jeu

# ======================================================================================
# CONFIGURATION
# ======================================================================================
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ======================================================================================
# 1. RESEAU DE NEURONES (ResNet)
# ======================================================================================
class ResidualBlock(nn.Module):
    def __init__(self, hidden_dim):
        super().__init__()
        self.fc1 = nn.Linear(hidden_dim, hidden_dim)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.bn2 = nn.BatchNorm1d(hidden_dim)

    def forward(self, x):
        residual = x
        out = F.relu(self.bn1(self.fc1(x)))
        out = self.bn2(self.fc2(out))
        out += residual
        return F.relu(out)

class CourtisansNet(nn.Module):
    def __init__(self, input_dim, action_dim):
        super().__init__()
        self.input_dim = input_dim
        self.action_dim = action_dim
        
        # Tronc commun
        self.start_fc = nn.Linear(input_dim, 512)
        self.bn_start = nn.BatchNorm1d(512)
        
        # Profondeur : 5 Blocs Résiduels
        self.res_blocks = nn.ModuleList([ResidualBlock(512) for _ in range(5)])
        
        # Tête Politique (Policy)
        self.policy_head = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, action_dim) # Logits
        )
        
        # Tête Valeur (Value)
        self.value_head = nn.Sequential(
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Tanh()
        )

    def forward(self, x):
        # x: (batch, input_dim)
        x = F.relu(self.bn_start(self.start_fc(x)))
        
        for block in self.res_blocks:
            x = block(x)
            
        pi = self.policy_head(x)
        v = self.value_head(x)
        return pi, v

# ======================================================================================
# 2. MCTS
# ======================================================================================
class MCTSNode:
    def __init__(self, parent=None, prior=0):
        self.parent = parent
        self.children = {}
        self.visit_count = 0
        self.value_sum = 0
        self.prior = prior

    def value(self):
        if self.visit_count == 0: return 0
        return self.value_sum / self.visit_count

class MCTS:
    def __init__(self, model, num_sims=50, c_puct=1.5):
        self.model = model
        self.num_sims = num_sims
        self.c_puct = c_puct

    def search(self, env):
        # On utilise une simulation déterminisée (Oracle) pour l'apprentissage
        root_env = env.clone_determinized()
        root = MCTSNode()
        
        # Expansion Racine
        self._expand(root, root_env)
        
        for _ in range(self.num_sims):
            node = root
            sim_env = root_env.clone_determinized()
            
            # 1. Selection
            while node.children and not self._is_terminal(sim_env):
                # UCB Score
                # Penser à inverser la value pour le joueur adverse ?
                # Dans AlphaZero Zero-Sum : Value est toujours "Prob de gagner pour le joueur Courant du noeud"
                # Donc quand on descend dans un enfant (coup joué), le noeud enfant est "Joueur Adverse".
                # Sa value est "Prob que Adverse gagne".
                # Donc pour NOUS (parent), on veut minimiser la victoire adverse => maximiser (-value).
                
                best_score = -float('inf')
                best_action = -1
                best_child = None
                
                total_visits = sum(c.visit_count for c in node.children.values())
                sqrt_total = np.sqrt(total_visits) if total_visits > 0 else 1
                
                for action, child in node.children.items():
                    # Q = Moyenne des values vues par ce noeud.
                    # IMPORTANT : la value stockée dans 'child' est vue du point de vue de 'child.player'.
                    # Child.player != Node.player.
                    # Donc Q = -child.value()
                    q_value = -child.value()
                    
                    u = self.c_puct * child.prior * sqrt_total / (1 + child.visit_count)
                    score = q_value + u
                    
                    if score > best_score:
                        best_score = score
                        best_action = action
                        best_child = child
                
                node = best_child
                if node is None: break # Should not happen if children exist
                sim_env.step(best_action)
            
            # 2. Expansion & Evaluation
            if not self._is_terminal(sim_env):
                value = self._expand(node, sim_env)
            else:
                # Terminal
                scores = sim_env._calcul_scores()
                # On calcule le reward RELATIF au joueur qui DOIT jouer à ce noeud (c'est à dire personne, c'est fini).
                # On prend le reward du dernier joueur ayant joué (= current_player du parent) ?
                # Non, Value doit être : "Est-ce que current_player de sim_env a gagné ?"
                # Mais current_player change à la fin du step.
                # Astuce : step() retourne done.
                # Reward calculé par step() est pour le joueur qui VIENT de jouer.
                # Ici on veut value pour le joueur A QUI C'ETAIT LE TOUR.
                # C'est un peu tricky. Simplifions :
                # On utilise sim_env._calcul_scores().
                # Value = Score(CurrentPlayer) - Score(Adversaire)
                cp = sim_env.current_player
                # Attention : si la partie est finie, current_player ne veut rien dire (ou c'est le vainqueur ?)
                # On peut dire value = 0 car pas d'action future.
                # MAIS pour la Backprop, on a besoin du résultat final.
                # Reprenons la logique step() : elle renvoie reward PENDANT la transition.
                # Ici on est statique.
                
                # Hack simple : On laisse step() calculer le reward terminal lors de la dernière transition.
                # Mais là on est dans "Simulation".
                pass
                
                # Pour faire simple : _expand retourne la Value estimée par le réseau.
                # Si terminal, le réseau n'est pas appelé. On calcule le Vrai Score.
                s = sim_env._calcul_scores()
                 # Supposons 2 joueurs
                p_id = sim_env.current_player # Celui qui 'devrait' jouer
                adv_id = (p_id + 1) % sim_env.num_players
                value = (s[p_id] - s[adv_id]) / 20.0 

            # 3. Backprop
            while node:
                node.value_sum += value
                node.visit_count += 1
                value = -value
                node = node.parent
                
        # Probas finales
        counts = np.zeros(env.mapper.get_action_space_size())
        for act, child in root.children.items():
            counts[act] = child.visit_count
            
        if np.sum(counts) > 0:
            counts /= np.sum(counts)
        return counts

    def _expand(self, node, env):
        # Prépare l'input
        vec = env.get_state_vector()
        tensor = torch.FloatTensor(vec).unsqueeze(0).to(DEVICE)
        
        self.model.eval()
        with torch.no_grad():
            pi, v = self.model(tensor)
            
        # Masquage actions illégales
        legal = env.get_legal_actions()
        if not legal:
            return v.item() # Terminal ou impasse
            
        pi_probs = F.softmax(pi, dim=1).cpu().numpy()[0]
        
        # Filtre
        final_probs = np.zeros_like(pi_probs)
        final_probs[legal] = pi_probs[legal]
        s = np.sum(final_probs)
        if s > 0:
            final_probs /= s
        else:
            final_probs[legal] = 1.0 / len(legal)
            
        # Création enfants
        for idx in legal:
            if final_probs[idx] > 0:
                node.children[idx] = MCTSNode(node, prior=final_probs[idx])
                
        return v.item()

    def _is_terminal(self, env):
        return not env.deck_indices and not any(env.mains.values())

# ======================================================================================
# 3. ENTRAINEMENT
# ======================================================================================
def train(num_players=2, iterations=100, progress_callback=None):
    # 1. Init
    env_tmp = GameEnv(num_players)
    input_dim = env_tmp.get_state_vector_size()
    action_dim = env_tmp.mapper.get_action_space_size()
    
    # print(f"Start Training {num_players} Players. In={input_dim}, Out={action_dim}")
    
    net = CourtisansNet(input_dim, action_dim).to(DEVICE)
    optimizer = optim.Adam(net.parameters(), lr=0.001)
    mcts = MCTS(net, num_sims=30)
    
    memory = deque(maxlen=5000)
    batch_size = 64
    
    model_dir = "models"
    os.makedirs(model_dir, exist_ok=True)
    
    # 2. Loop
    for it in range(iterations):
        if progress_callback:
            progress_callback(it / iterations, f"Iteration {it}/{iterations}")
            
        env = GameEnv(num_players)
        history = []
        done = False
        
        # Self Play
        while not done:
            s_vec = env.get_state_vector()
            probs = mcts.search(env)
            
            # Exploration
            if it < 20: 
                action = np.random.choice(len(probs), p=probs)
            else:
                # Argmax avec un peu de bruit
                if random.random() < 0.1:
                    action = np.random.choice(len(probs), p=probs)
                else:
                    action = np.argmax(probs)
            
            history.append([s_vec, probs, env.current_player])
            _, reward, done, _ = env.step(action)
            
        # Fin de partie : calcul reward final
        scores = env._calcul_scores()
        # On doit attribuer un reward pour CHAQUE état de l'historique
        # selon le joueur qui devait jouer.
        
        for step in history:
            s, p, player_id = step
            # Score relatif de Ce Joueur vs Moyenne des autres
            my_score = scores[player_id]
            others = [v for k,v in scores.items() if k != player_id]
            avg_others = sum(others) / len(others)
            
            val = (my_score - avg_others) / 20.0
            val = max(-1.0, min(1.0, val)) # Clip
            
            memory.append((s, p, val))
            
        # Training Step
        if len(memory) > batch_size:
            batch = random.sample(memory, batch_size)
            bs = torch.FloatTensor(np.array([x[0] for x in batch])).to(DEVICE)
            bp = torch.FloatTensor(np.array([x[1] for x in batch])).to(DEVICE)
            bv = torch.FloatTensor(np.array([x[2] for x in batch])).unsqueeze(1).to(DEVICE)
            
            pi_pred, v_pred = net(bs)
            
            loss_pi = -torch.sum(bp * F.log_softmax(pi_pred, dim=1)) / batch_size
            loss_v = F.mse_loss(v_pred, bv)
            loss = loss_pi + loss_v
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            if it % 10 == 0:
                print(f"Iter {it} | Loss: {loss.item():.4f} | WinnerScore: {max(scores.values())}")

    # Save
    path = f"{model_dir}/model_{num_players}.pth"
    torch.save(net.state_dict(), path)
    print(f"Saved: {path}")
    return net

def play_vs_ai(model_path="models/model_2.pth"):
    # Chargement
    num_players = 2 
    # TODO: Déduire num_players du nom de fichier ou config
    
    env = GameEnv(num_players)
    net = CourtisansNet(env.get_state_vector_size(), env.mapper.get_action_space_size()).to(DEVICE)
    
    try:
        net.load_state_dict(torch.load(model_path))
        print("Model loaded.")
    except:
        print("No model found, playing with random init.")
        
    mcts = MCTS(net, num_sims=50)
    net.eval()
    
    done = False
    print("=== IA vs HUMAIN (Console) ===")
    
    while not done:
        print(f"\n--- Tour Joueur {env.current_player} ---")
        if env.current_player == 0: # Humain
            print("Votre main : ", env.mains[0])
            # Input simple : un entier 0-11
            # Pour aider, on pourrait lister les actions
            actions = env.get_legal_actions()
            print(f"Actions possibles (ids): {actions}")
            # Afficher le décodage
            for a in actions:
                perm, q, t = env.mapper.decode(a)
                print(f" {a}: M{perm}->[R({q}), S, A({t})]")
            
            try:
                c = int(input("Choix > "))
                env.step(c)
            except: 
                pass
        else:
            print("IA réfléchit...")
            probs = mcts.search(env)
            action = np.argmax(probs)
            env.step(action)
            
        if not env.deck_indices and not any(env.mains.values()):
            done = True
            
    print("Scores:", env._calcul_scores())

if __name__ == "__main__":
    # Point d'entrée pour lancer l'entrainement manuellement
    # python -m app.mcts_network
    train(num_players=2, iterations=50)