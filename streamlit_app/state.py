"""Initialisation et accès au session_state."""

from __future__ import annotations

import streamlit as st

from app.jeu import GameEnv


def init_session() -> None:
    if "game_env" not in st.session_state:
        st.session_state.game_env = GameEnv(num_players=2)
        st.session_state.game_over = False
    if "logs" not in st.session_state:
        st.session_state.logs = [{"type": "info", "msg": "Bienvenue dans Courtisans !"}]
    if "interaction_mode" not in st.session_state:
        st.session_state.interaction_mode = "playing"
    if "error_msg" not in st.session_state:
        st.session_state.error_msg = None


def new_game(num_players: int = 2) -> None:
    st.session_state.game_env = GameEnv(num_players=num_players)
    st.session_state.game_over = False
    st.session_state.logs = [{"type": "info", "msg": "Nouvelle partie !"}]
    st.session_state.interaction_mode = "playing"
    st.session_state.error_msg = None
