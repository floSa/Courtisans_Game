"""Point d'entrée Streamlit pour le jeu Courtisans (humain vs IA)."""

from __future__ import annotations

import os
import sys

import streamlit as st

# Ajout du dossier parent au path pour importer `app` quand on lance via
# `streamlit run streamlit_app/courtisans_app.py`.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.jeu import GameEnv  # noqa: E402
from app.mcts_network import TrainConfig, load_model, train  # noqa: E402
from streamlit_app import state as state_mod  # noqa: E402
from streamlit_app.ai_runner import auto_resolve_assassins, pick_ai_action  # noqa: E402
from streamlit_app.ui import board as board_ui  # noqa: E402
from streamlit_app.ui import hand_picker  # noqa: E402
from streamlit_app.ui import logs as logs_ui  # noqa: E402
from streamlit_app.ui.assets import BOARD_IMG  # noqa: E402

# ======================================================================================
# CONFIGURATION
# ======================================================================================
st.set_page_config(page_title="Courtisans AI", layout="wide")
st.markdown(
    """
    <style>
    .block-container {
        max-width: 950px;
        padding-left: 2rem;
        padding-right: 2rem;
        margin: auto;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ======================================================================================
# STATE
# ======================================================================================
state_mod.init_session()
env: GameEnv = st.session_state.game_env
ai_net = load_model("models/model_2.pth", env)

# ======================================================================================
# SIDEBAR
# ======================================================================================
st.sidebar.title("Paramètres")
mode = st.sidebar.radio("Mode", ["Jouer vs IA", "Entraînement"])

if mode == "Entraînement":
    st.sidebar.header("Configuration Entraînement")
    nb_iter = st.sidebar.number_input(
        "Nombre de Parties", min_value=10, max_value=2000, value=50, step=10
    )
    num_sims_train = st.sidebar.number_input(
        "Simulations MCTS / coup", min_value=5, max_value=400, value=30, step=5
    )
    lr = st.sidebar.number_input(
        "Learning rate", min_value=1e-5, max_value=1e-2, value=1e-3, step=1e-4, format="%.5f"
    )

    if st.sidebar.button("Lancer l'entraînement"):
        progress_bar = st.sidebar.progress(0)
        status_text = st.sidebar.empty()

        def update_progress(p: float, txt: str) -> None:
            progress_bar.progress(min(1.0, max(0.0, p)))
            status_text.text(txt)

        train(
            config=TrainConfig(
                num_players=2,
                iterations=int(nb_iter),
                num_sims=int(num_sims_train),
                lr=float(lr),
            ),
            progress_callback=update_progress,
        )
        st.sidebar.success("Entraînement terminé ! Modèle sauvegardé.")

elif mode == "Jouer vs IA":
    st.sidebar.header("Partie")
    num_sims_inf = st.sidebar.slider("Simulations MCTS (IA)", 5, 200, 30, step=5)
    if st.sidebar.button("Nouvelle Partie"):
        state_mod.new_game()
        st.rerun()

# ======================================================================================
# APP PRINCIPALE
# ======================================================================================

# Domaine IA
ia_domain_cards = [env.cartes[i] for i in env.plateau_indices if env.cartes[i].domaine_id == 1]
board_ui.render_zone_7cols(ia_domain_cards, "Domaine Adversaire (IA)")

# Banquet Reine
st.markdown("---")
reine_cards = [env.cartes[i] for i in env.plateau_indices if env.cartes[i].position is not None]
estime, disgrace = board_ui.split_reine(reine_cards)

st.markdown("<h4 style='text-align: center;'>Estime</h4>", unsafe_allow_html=True)
board_ui.render_zone_7cols(estime)
st.image(BOARD_IMG, use_container_width=True)
st.markdown("<h4 style='text-align: center;'>Disgrâce</h4>", unsafe_allow_html=True)
board_ui.render_zone_7cols(disgrace)
st.markdown("---")

# Domaine joueur
me_cards = [env.cartes[i] for i in env.plateau_indices if env.cartes[i].domaine_id == 0]
board_ui.render_zone_7cols(me_cards, "Votre Domaine")

# ======================================================================================
# INTERACTION : MAIN DU JOUEUR
# ======================================================================================
hand_indices = env.mains[env.current_player]

# -------- résolution manuelle d'un assassin du joueur ---------------------------------
if env.pending_assassin_context and env.current_player == 0:
    st.warning("Un assassin a été joué. Sélectionnez sa victime.")
    targets = env.pending_assassin_context["targets"]
    target_options = {f"{env.cartes[i]} (id={i})": i for i in targets}
    target_options["(passer)"] = None
    choice_label = st.radio("Cibles disponibles :", list(target_options.keys()))
    if st.button("Résoudre l'assassin"):
        _, _, _, info = env.resolve_assassin_manual(target_options[choice_label])
        auto_resolve_assassins(env, info)
        if env.is_done():
            st.session_state.game_over = True
        st.rerun()

elif env.current_player == 0 and not st.session_state.game_over and hand_indices:
    card_objs = [env.cartes[i] for i in hand_indices]
    hand_picker.render(card_objs)

    def play_turn_callback() -> None:
        mapping = hand_picker.get_mapping_result()
        if not mapping:
            st.session_state.error_msg = "Veuillez assigner une carte à chaque destination."
            return

        perm = (mapping[0], mapping[1], mapping[2])
        queen_pos = hand_picker.queen_position()

        try:
            action = env.mapper.encode(perm, queen_pos, target_relative_idx=0)
        except ValueError as exc:
            st.session_state.error_msg = f"Erreur encodage action : {exc}"
            return

        # Log joueur
        player_hand = env.mains[0]
        logs_ui.log_turn(
            st.session_state.logs,
            "Vous",
            env.cartes[player_hand[mapping[0]]],
            env.cartes[player_hand[mapping[1]]],
            env.cartes[player_hand[mapping[2]]],
        )

        _, _, done, info = env.step(action)
        if info.get("assassin_pending"):
            # On laisse l'UI rerender et passer en mode "résolution assassin"
            hand_picker.reset_selection()
            st.session_state.error_msg = None
            return

        if done:
            st.session_state.game_over = True
            hand_picker.reset_selection()
            st.session_state.error_msg = None
            return

        hand_picker.reset_selection()
        st.session_state.error_msg = None

        # Tour IA
        if not env.is_done():
            ai_action = pick_ai_action(env, ai_net, num_sims=int(num_sims_inf))
            ai_hand = env.mains[env.current_player]
            p, _q, _t = env.mapper.decode(ai_action)
            logs_ui.log_turn(
                st.session_state.logs,
                "IA",
                env.cartes[ai_hand[p[0]]],
                env.cartes[ai_hand[p[1]]],
                env.cartes[ai_hand[p[2]]],
                suffix=" (IA)",
            )
            _, _, done, info = env.step(ai_action)
            done, _ = auto_resolve_assassins(env, info)
            if done or env.is_done():
                st.session_state.game_over = True

    current_map = hand_picker.get_mapping_result()
    btn_type = "primary" if current_map else "secondary"
    st.markdown("---")
    st.button("VALIDER L'ACTION", type=btn_type, on_click=play_turn_callback)

    if st.session_state.error_msg:
        st.warning(st.session_state.error_msg)

elif st.session_state.game_over:
    st.success("Partie Terminée !")
    scores = env._calcul_scores()
    st.write(f"Scores : Vous {scores[0]} - IA {scores[1]}")
    if scores[0] > scores[1]:
        st.balloons()

else:
    st.error("État inattendu : c'est le tour de l'IA mais l'action n'a pas été déclenchée.")
    if st.button("Forcer l'IA à jouer"):
        ai_action = pick_ai_action(env, ai_net, num_sims=int(num_sims_inf))
        ai_hand = env.mains[env.current_player]
        p, _q, _t = env.mapper.decode(ai_action)
        logs_ui.log_turn(
            st.session_state.logs,
            "IA (Forcé)",
            env.cartes[ai_hand[p[0]]],
            env.cartes[ai_hand[p[1]]],
            env.cartes[ai_hand[p[2]]],
            suffix=" (IA)",
        )
        _, _, done, info = env.step(ai_action)
        done, _ = auto_resolve_assassins(env, info)
        if done or env.is_done():
            st.session_state.game_over = True
        st.rerun()

# ======================================================================================
# LOGS
# ======================================================================================
logs_ui.render_logs(st.session_state.logs)
