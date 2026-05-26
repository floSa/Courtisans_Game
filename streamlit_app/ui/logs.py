"""Rendu de l'historique des tours."""

from __future__ import annotations

import streamlit as st

from streamlit_app.ui.assets import load_image


def render_logs(logs: list[dict | str]) -> None:
    with st.expander("Logs"):
        for entry in reversed(logs):
            if isinstance(entry, dict) and entry.get("type") == "turn":
                st.markdown(f"**{entry['player']}**")
                cols = st.columns(3)
                for i, move in enumerate(entry["moves"]):
                    card = move["card"]
                    dest = move["dest"]
                    with cols[i]:
                        st.image(load_image(card.famille, card.role), width=40)
                        st.caption(dest)
            elif isinstance(entry, dict) and entry.get("type") == "info":
                st.text(entry["msg"])
            else:
                st.text(str(entry))


def log_turn(logs: list, player_label: str, c_reine, c_moi, c_adv, suffix: str = "") -> None:
    logs.append(
        {
            "type": "turn",
            "player": player_label,
            "moves": [
                {"card": c_reine, "dest": "Reine"},
                {"card": c_moi, "dest": f"Moi{suffix}"},
                {"card": c_adv, "dest": f"Adv{suffix}"},
            ],
        }
    )
