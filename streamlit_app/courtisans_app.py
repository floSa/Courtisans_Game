import streamlit as st
import os
import sys
import time
import torch
import random
from PIL import Image

# Ajout du dossier parent au path pour importer app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.jeu import GameEnv, NUM_FAMILLES, Role, Famille
from app.mcts_network import train, CourtisansNet, DEVICE

# ======================================================================================
# CONFIGURATION
# ======================================================================================
st.set_page_config(page_title="Courtisans AI", layout="wide")

# CSS pour limiter la largeur max
st.markdown("""
<style>
.block-container {
    max-width: 950px;
    padding-left: 2rem;
    padding-right: 2rem;
    margin: auto;
}
</style>
""", unsafe_allow_html=True)

IMAGE_DIR = os.path.join("images")
FAMILLES_DIR = os.path.join(IMAGE_DIR, "familles_cartes")
BOARD_IMG = os.path.join(IMAGE_DIR, "courtisans_reine_board.png")
BACK_CARD_IMG = os.path.join(IMAGE_DIR, "back_card.png")

# UI CONFIG
UI_CARD_WIDTH = 120
# UI_STACK_OVERLAP removed: dynamic calculation (1/6 height) used instead
# UI_BOARD_WIDTH supprimé car on passe en dynamic full width
# UI_BOARD_WIDTH supprimé car on passe en dynamic full width

# Mappe Role -> Filename letter
ROLE_TO_FILE = {
    Role.ASSASSIN: "A",
    Role.GARDE: "S", 
    Role.NOBLE: "N",
    Role.ESPION: "E",
    Role.NEUTRE: "I"
}

# ======================================================================================
# FONCTIONS UTILITAIRES
# ======================================================================================
@st.cache_data
def load_image(famille_idx, role_idx, visible=True):
    """Charge et cache l'image d'une carte"""
    if not visible:
         if os.path.exists(BACK_CARD_IMG):
             return Image.open(BACK_CARD_IMG)
         else:
             return Image.new('RGB', (200, 300), color = 'gray')

    # Famille 1-based dans les dossiers ? User said "1", "2"... 
    # Mes list_dir montrent "1", "2"... donc famille_idx + 1
    fam_str = str(famille_idx + 1)
    
    role = Role(role_idx)
    letter = ROLE_TO_FILE[role]
    
    # Extension peut varier jpg/png
    # On teste les deux
    path_base = os.path.join(FAMILLES_DIR, fam_str, letter)
    if os.path.exists(path_base + ".jpg"):
        return Image.open(path_base + ".jpg")
    elif os.path.exists(path_base + ".png"):
        return Image.open(path_base + ".png")
    else:
        # Placeholder rouge
        img = Image.new('RGB', (200, 300), color = 'red')
        return img

def render_stack(cards):
    """
    Crée une image composite de cartes empilées verticalement.
    cards: liste d'objets carte
    Overlap dynamique : 1/6 de la hauteur de l'image.
    """
    if not cards:
        return None
    
    # On charge les images
    imgs = [load_image(c.famille, c.role, visible=c.visible) for c in cards]
    
    if not imgs: return None

    # Dimensions de base (on suppose toutes les cartes de meme taille ou on resize)
    base_w, base_h = imgs[0].size
    
    # Calcul overlap dynamique : 1/6 de la hauteur
    overlap_y = base_h // 6
    
    # Taille totale canvas
    total_h = base_h + (len(imgs) - 1) * overlap_y
    composite = Image.new("RGBA", (base_w, total_h), (0,0,0,0))
    
    for i, img in enumerate(imgs):
        # Convertir en RGBA pour transparence si PNG
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        composite.paste(img, (0, i * overlap_y), img)
        
    return composite

def render_zone_7cols(cards, label=None):
    """
    Affiche une zone de jeu en 7 colonnes :
    Fam 1, Fam 2, Fam 3, ESPIONS (Face Cachée), Fam 4, Fam 5, Fam 6
    """
    if label:
        st.markdown(f"#### {label}")
    
    cols = st.columns(7)
    
    # 1. Trier les cartes
    # Familles 0..2 -> indices 0..2
    # Espions (tout type) -> indice 3
    # Familles 3..5 -> indices 4..6
    
    buckets = {i: [] for i in range(7)}
    
    for c in cards:
        if c.role == Role.ESPION.value:
            buckets[3].append(c)
        else:
            # Familles
            f_idx = c.famille # 0..5
            if f_idx < 3:
                buckets[f_idx].append(c)
            else:
                buckets[f_idx + 1].append(c) # 3->4, 4->5, 5->6
                
    # 2. Afficher
    headers = ["Fam 1", "Fam 2", "Fam 3", "Espions", "Fam 4", "Fam 5", "Fam 6"]
    
    for i in range(7):
        with cols[i]:
            # st.caption(headers[i])
            
            current_cards = buckets[i]
            
            if i == 3 and current_cards: 
                # SPY COLUMN : Face cachée forcée
                # On utilise render_stack mais on doit charger images cachées
                # Astuce : render_stack utilise c.visible. 
                # On va charger manuellement les images "back" pour cette colonne
                # car modifier c.visible affecterait l'état du jeu si on passait par ref.
                
                # Logic copied/adapted from previous manual spy rendering
                imgs = [load_image(c.famille, c.role, visible=False) for c in current_cards]
                if imgs:
                    base_w, base_h = imgs[0].size
                    overlap_y = base_h // 6
                    total_h = base_h + (len(imgs) - 1) * overlap_y
                    composite = Image.new("RGBA", (base_w, total_h), (0,0,0,0))
                    for k, img in enumerate(imgs):
                        if img.mode != 'RGBA': img = img.convert('RGBA')
                        composite.paste(img, (0, k * overlap_y), img)
                    st.image(composite, use_container_width=True)
                
            else:
                # Normal behavior
                if current_cards:
                    stack_img = render_stack(current_cards)
                    if stack_img:
                        st.image(stack_img, use_container_width=True)
                else:
                    st.text("-")

def get_ai_model(num_players):
    """Charge le dernier modèle ou None"""
    path = f"models/model_{num_players}.pth"
    if os.path.exists(path):
        env = GameEnv(num_players)
        net = CourtisansNet(env.get_state_vector_size(), env.mapper.get_action_space_size()).to(DEVICE)
        net.load_state_dict(torch.load(path, map_location=DEVICE, weights_only=True))
        net.eval()
        return net
    return None

# ======================================================================================
# INTERFACE SIDEBAR
# ======================================================================================
st.sidebar.title("Paramètres")

mode = st.sidebar.radio("Mode", ["Jouer vs IA", "Entraînement"])

if mode == "Entraînement":
    st.sidebar.header("Configuration Entraînement")
    nb_iter = st.sidebar.number_input("Nombre de Parties", min_value=10, max_value=2000, value=50, step=10)
    
    if st.sidebar.button("Lancer l'entraînement"):
        progress_bar = st.sidebar.progress(0)
        status_text = st.sidebar.empty()
        
        def update_progress(p, txt):
            progress_bar.progress(p)
            status_text.text(txt)
            
        trained_net = train(num_players=2, iterations=nb_iter, progress_callback=update_progress)
        st.sidebar.success("Entraînement terminé ! Modèle sauvegardé.")
        # Reload model logic if needed
        
elif mode == "Jouer vs IA":
    st.sidebar.header("Partie")
    if st.sidebar.button("Nouvelle Partie"):
        st.session_state.game_env = GameEnv(num_players=2)
        st.session_state.game_over = False
        st.session_state.logs = []
        st.rerun()

# ======================================================================================
# STATE MANAGEMENT
# ======================================================================================
if "game_env" not in st.session_state:
    st.session_state.game_env = GameEnv(num_players=2)
    st.session_state.game_over = False
    
if "logs" not in st.session_state:
    st.session_state.logs = [{"type": "info", "msg": "Bienvenue dans Courtisans !"}]

# Mode d'interaction (playing / assassin)
if "interaction_mode" not in st.session_state:
    st.session_state.interaction_mode = "playing"

env = st.session_state.game_env

# Charge l'IA
ai_net = get_ai_model(2)

# ======================================================================================
# APPLICATION PRINCIPALE
# ======================================================================================

# --- HEADER STATUS ---
# st.write(f"### Tour : {'Joueur (Vous)' if env.current_player == 0 else 'IA'}")


# --- ZONE SUPERIEURE : IA (Adversaire) ---
# render_zone_7cols filtrera et affichera
ia_domain_cards = [env.cartes[i] for i in env.plateau_indices if env.cartes[i].domaine_id == 1]
render_zone_7cols(ia_domain_cards, "Domaine Adversaire (IA)")


# --- ZONE CENTRALE : REINE ---
st.markdown("---")

reine_cards = [env.cartes[i] for i in env.plateau_indices if env.cartes[i].position is not None]
estime = [c for c in reine_cards if c.position == 'Estime']
disgrace = [c for c in reine_cards if c.position == 'Disgrace']

# Tri par famille pour Estime et Disgrace
estime_by_fam = {f: [] for f in range(NUM_FAMILLES)}
for c in estime: estime_by_fam[c.famille].append(c)

disgrace_by_fam = {f: [] for f in range(NUM_FAMILLES)}
for c in disgrace: disgrace_by_fam[c.famille].append(c)


# 1. HAUT : ESTIME (Lumière)
st.markdown("<h4 style='text-align: center;'>Estime</h4>", unsafe_allow_html=True)
render_zone_7cols(estime)

# 2. MILIEU : PLATEAU
# On supprime les colonnes pour avoir vrai FULL WIDTH
st.image(BOARD_IMG, use_container_width=True)

# 3. BAS : DISGRACE (Obscurité)
st.markdown("<h4 style='text-align: center;'>Disgrâce</h4>", unsafe_allow_html=True)
render_zone_7cols(disgrace)

st.markdown("---")

# --- ZONE INFERIEURE : JOUEUR (Moi) ---
me_cards = [env.cartes[i] for i in env.plateau_indices if env.cartes[i].domaine_id == 0]
render_zone_7cols(me_cards, "Votre Domaine")

# --- ZONE MAIN (ACTIONS) ---
# st.markdown("### Votre Main") # Removed as requested
hand_indices = env.mains[env.current_player]

if env.current_player == 0 and not st.session_state.game_over:
    if not hand_indices:
        st.warning("Plus de cartes en main ! (Fin de manche ?)")
    else:
        # --- CSS : CERCLAGE ET ALIGNEMENT ---
        st.markdown("""
            <style>
            /* Transforme les cases à cocher des colonnes 5 et 6 en cercles (Status Reine) */
            div[data-testid="stHorizontalBlock"] > div:nth-child(5) input[type="checkbox"],
            div[data-testid="stHorizontalBlock"] > div:nth-child(6) input[type="checkbox"] {
                border-radius: 50% !important;
                transform: scale(1.3);
            }
            /* Centrage vertical */
            div[data-testid="stHorizontalBlock"] {
                align-items: center;
            }
            </style>
        """, unsafe_allow_html=True)

        # --- LOGIQUE ET CALLBACKS ---
        if "v3_lumiere" not in st.session_state:
            st.session_state.v3_lumiere = True
            st.session_state.v3_disgrace = False

        def handle_v3_mapping(d_sel, c_sel):
            key_sel = f"map_{d_sel}_{c_sel}"
            if st.session_state.get(key_sel):
                for d in range(3):
                    for c in range(3):
                        if (d == d_sel or c == c_sel) and (d, c) != (d_sel, c_sel):
                            st.session_state[f"map_{d}_{c}"] = False

        def handle_v3_status(clicked):
            if clicked == "lumiere":
                st.session_state.v3_lumiere = True
                st.session_state.v3_disgrace = False
            else:
                st.session_state.v3_lumiere = False
                st.session_state.v3_disgrace = True

        st.markdown("---")
        st.write("#### Cartes à jouer")

        # Config Grid
        A_ITEMS = [
            {"label": "Reine", "icon": "👑"},
            {"label": "Mon Domaine", "icon": "🏰"},
            {"label": "Adversaire", "icon": "⚔️"}
        ]
        card_objs = [env.cartes[i] for i in hand_indices]
        
        # Cols: Label + 3 Cards + 2 Status
        # Alignement parfait demandé : on met les mêmes poids pour les colonnes images et status
        # Cela garantit que responsive width -> same height
        cols_config = [1.5, 1, 1, 1, 1, 1]

        # 1. En-tête de la grille (Images)
        h3 = st.columns(cols_config)
        h3[0].write("**Destinations**")
        for idx, c in enumerate(card_objs):
            with h3[idx+1]:
                img = load_image(c.famille, c.role)
                st.image(img, use_container_width=True) # Meme taille que les autres
                st.caption(f"Carte {idx+1}")
        
        
        
        # Spacer invisible pour aligner le texte avec les "Carte X" qui sont sous des images
        # On utilise la taille de la premère carte de la main pour avoir le meme ratio
        spacer_size = (200, 300) # Default
        if card_objs:
             # On charge la première pour avoir la ref
             ref_img = load_image(card_objs[0].famille, card_objs[0].role)
             spacer_size = ref_img.size
             
        spacer = Image.new("RGBA", spacer_size, (0,0,0,0))

        with h3[4]:
             st.image(spacer, use_container_width=True)
             st.caption("**Lumière**")
        with h3[5]:
             st.image(spacer, use_container_width=True)
             st.caption("**Disgrâce**")
        
        # 2. Lignes de la grille
        for d_idx, item in enumerate(A_ITEMS):
            r3 = st.columns(cols_config)
            r3[0].markdown(f"### {item['icon']} {item['label']}")
            
            for c_idx in range(3):
                key = f"map_{d_idx}_{c_idx}"
                if key not in st.session_state: st.session_state[key] = False
                r3[c_idx+1].checkbox("", key=key, on_change=handle_v3_mapping, args=(d_idx, c_idx))
            
            if d_idx == 0: # Reine
                r3[4].checkbox("", key="v3_lumiere", on_change=handle_v3_status, args=("lumiere",))
                r3[5].checkbox("", key="v3_disgrace", on_change=handle_v3_status, args=("disgrace",))
            else:
                r3[4].write("") 
                r3[5].write("")
        
        # Labels du bas supprimés et déplacés en haut
        
        


        # --- LOGIQUE DE VALIDATION (CALLBACK) ---
        st.markdown("---")

        def get_mapping_result():
            mapping = {}
            used_cards = set()
            for d in range(3):
                found = False
                for c in range(3):
                    if st.session_state.get(f"map_{d}_{c}"):
                        mapping[d] = c
                        used_cards.add(c)
                        found = True
                        break
                if not found: return None 
            if len(used_cards) != 3: return None
            return mapping

        def play_turn_callback():
            current_mapping = get_mapping_result()
            if not current_mapping:
                st.session_state.error_msg = "Veuillez assigner une carte à chaque destination."
                return

            # Indices réels des cartes dans la main
            idx_reine = current_mapping[0]
            idx_soi = current_mapping[1]
            idx_adv = current_mapping[2]
            
            perm = (idx_reine, idx_soi, idx_adv)
            
            q_sub = "Estime" if st.session_state.v3_lumiere else "Disgrace"
            target_idx = 0
            
            found_act = -1
            for act in range(env.mapper.get_action_space_size()):
                p, q, t = env.mapper.decode(act)
                if p == perm and q == q_sub and t == target_idx:
                    found_act = act
                    break
            
            if found_act != -1:
                # JOUEUR JOUE
                # -- LOGGING START --
                player_hand_indices = env.mains[0]
                # p in logic above is (idx_reine, idx_soi, idx_adv)
                # But careful, p comes from decode which we don't use directly for player (we have perm)
                # perm = (idx_reine, idx_soi, idx_adv)
                
                # Retrieve Card Objects
                c_reine = env.cartes[player_hand_indices[idx_reine]]
                c_moi   = env.cartes[player_hand_indices[idx_soi]]
                c_adv   = env.cartes[player_hand_indices[idx_adv]]
                
                log_entry = {
                    "type": "turn",
                    "player": "Vous",
                    "moves": [
                        {"card": c_reine, "dest": "Reine"},
                        {"card": c_moi,   "dest": "Moi"},
                        {"card": c_adv,   "dest": "Adv"}
                    ]
                }
                st.session_state.logs.append(log_entry)
                # -- LOGGING END --

                # -- LOGGING END --

                # -- LOGGING END --

                _, _, done, info = env.step(found_act)
                
                if info.get("assassin_pending"):
                    st.session_state.interaction_mode = "assassin"
                    st.session_state.assassin_info = env.pending_assassin_context
                    return # On sort, l'UI se rechargera en mode assassin

                if done: st.session_state.game_over = True
                # st.session_state.logs.append(f"Vous avez joué.") # Remplace par visuel
                
                # Reset selections - Maintenant safe car fait pendant le callback
                for d in range(3):
                    for c in range(3):
                        st.session_state[f"map_{d}_{c}"] = False
                st.session_state.error_msg = None

                # IA JOUE
                if not st.session_state.game_env.deck_indices and not any(env.mains.values()):
                    st.session_state.game_over = True
                else:
                    if ai_net:
                        from app.mcts_network import MCTS
                        mcts = MCTS(ai_net, num_sims=30)
                        probs = mcts.search(env)
                        ai_action = int(torch.argmax(torch.tensor(probs)))
                    else:
                        ai_action = random.choice(env.get_legal_actions())
                    
                    
                    # -- LOGGING AI START --
                    # Decode to get cards
                    p, q, t = env.mapper.decode(ai_action) 
                    # p is (idx_reine, idx_soi, idx_adv)
                    ai_hand_indices = env.mains[env.current_player]
                    
                    c_reine = env.cartes[ai_hand_indices[p[0]]]
                    c_moi   = env.cartes[ai_hand_indices[p[1]]] # AI's "Moi" (Domaine IA)
                    c_adv   = env.cartes[ai_hand_indices[p[2]]] # AI's "Adv" (Votre Domaine)
                    
                    log_entry = {
                        "type": "turn",
                        "player": "IA",
                        "moves": [
                            {"card": c_reine, "dest": "Reine"},
                            {"card": c_moi,   "dest": "Moi (IA)"},
                            {"card": c_adv,   "dest": "Adv (Vous)"}
                        ]
                    }
                    st.session_state.logs.append(log_entry)
                    # -- LOGGING AI END --

                    # -- LOGGING AI END --

                    _, _, done, _ = env.step(ai_action)
                    if done: st.session_state.game_over = True
                    # st.session_state.logs.append(f"L'IA a joué.")

            else:
                st.session_state.error_msg = "Erreur encodage action (Bug)."

        # Check mapping state for visual feedback (enable/disable button visuals only)
        # Note: Button callback handles logic, but user wants visual safety
        current_map_check = get_mapping_result()
        btn_type = "primary" if current_map_check else "secondary"
        
        st.button("VALIDER L'ACTION", type=btn_type, on_click=play_turn_callback)
        
        if "error_msg" in st.session_state and st.session_state.error_msg:
             st.warning(st.session_state.error_msg)


                        
elif st.session_state.game_over:
    st.success("Partie Terminée !")
    scores = env._calcul_scores()
    st.write(f"Scores : Vous {scores[0]} - IA {scores[1]}")
    if scores[0] > scores[1]: st.balloons()
    
else:
    st.error("État inattendu : C'est le tour de l'IA mais l'action n'a pas été déclenchée automatiquement.")
    st.write("### Infos de Debug")
    st.write(f"**Joueur Actuel (env.current_player):** {env.current_player} (devrait être 1 pour IA)")
    st.write(f"**Game Over:** {st.session_state.game_over}")
    st.write(f"**Cartes en main Joueur:** {len(env.mains[0])}")
    st.write(f"**Cartes en main IA:** {len(env.mains[1])}")
    st.write(f"**Cartes dans la pioche:** {len(env.deck_indices)}")
    
    # Bouton de secours pour forcer l'IA à jouer si bloqué
    if st.button("Forcer l'IA à jouer"):
        # Logique copiée du callback
        if ai_net:
            from app.mcts_network import MCTS
            mcts = MCTS(ai_net, num_sims=30)
            probs = mcts.search(env)
            ai_action = int(torch.argmax(torch.tensor(probs)))
        else:
            ai_action = random.choice(env.get_legal_actions())
        
        # -- LOGGING FORCED AI START --
        p, q, t = env.mapper.decode(ai_action)
        ai_hand_indices = env.mains[env.current_player]
        c_reine = env.cartes[ai_hand_indices[p[0]]]
        c_moi   = env.cartes[ai_hand_indices[p[1]]]
        c_adv   = env.cartes[ai_hand_indices[p[2]]]
        
        log_entry = {
            "type": "turn",
            "player": "IA (Forcé)",
            "moves": [
                {"card": c_reine, "dest": "Reine"},
                {"card": c_moi,   "dest": "Moi (IA)"},
                {"card": c_adv,   "dest": "Adv (Vous)"}
            ]
        }
        st.session_state.logs.append(log_entry)
        # -- LOGGING FORCED AI END --
        
        _, _, done, _ = env.step(ai_action)
        if done: st.session_state.game_over = True
        st.rerun()

# Logs
with st.expander("Logs"):
    # Reverse logs to show specific latest first ? Or keep append order.
    # User said "je souhaite avoir... dans les logs".
    # Usually logs are top-down or bottom-up. Standard is often bottom-up for chat, but here it's a list.
    # Let's keep order but maybe reverse for display so latest is top? 
    # User didn't specify order, but usually latest on top is better for games. Let's do latest on top.
    
    for l in reversed(st.session_state.logs):
        if isinstance(l, dict) and l.get("type") == "turn":
            st.markdown(f"**{l['player']}**")
            cols = st.columns(3)
            for i, move in enumerate(l['moves']):
                card = move['card']
                dest = move['dest']
                with cols[i]:
                    img = load_image(card.famille, card.role)
                    st.image(img, width=40) # Tiny image
                    st.caption(dest)
        elif isinstance(l, dict) and l.get("type") == "info":
             st.text(l['msg'])
        else:
            # Legacy string support
            st.text(str(l))
