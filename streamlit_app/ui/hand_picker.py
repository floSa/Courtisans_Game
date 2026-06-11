"""Grille interactive de sélection des cartes à jouer."""

from __future__ import annotations

import streamlit as st
from PIL import Image

from app.jeu import Carte
from streamlit_app.ui.assets import load_image

A_ITEMS = (
    {"label": "Reine", "icon": "👑"},
    {"label": "Mon Domaine", "icon": "🏰"},
    {"label": "Adversaire", "icon": "⚔️"},
)


def _ensure_state() -> None:
    if "v3_lumiere" not in st.session_state:
        st.session_state.v3_lumiere = True
        st.session_state.v3_disgrace = False
    for d in range(3):
        for c in range(3):
            st.session_state.setdefault(f"map_{d}_{c}", False)


def _handle_mapping(d_sel: int, c_sel: int) -> None:
    """Quand on coche (d,c), on décoche les conflits (même ligne ou même colonne)."""
    if st.session_state.get(f"map_{d_sel}_{c_sel}"):
        for d in range(3):
            for c in range(3):
                if (d == d_sel or c == c_sel) and (d, c) != (d_sel, c_sel):
                    st.session_state[f"map_{d}_{c}"] = False


def _handle_status(clicked: str) -> None:
    if clicked == "lumiere":
        st.session_state.v3_lumiere = True
        st.session_state.v3_disgrace = False
    else:
        st.session_state.v3_lumiere = False
        st.session_state.v3_disgrace = True


def get_mapping_result() -> dict[int, int] | None:
    """Retourne {destination → idx_carte} si toutes les destinations sont assignées."""
    mapping: dict[int, int] = {}
    used: set[int] = set()
    for d in range(3):
        found = False
        for c in range(3):
            if st.session_state.get(f"map_{d}_{c}"):
                mapping[d] = c
                used.add(c)
                found = True
                break
        if not found:
            return None
    if len(used) != 3:
        return None
    return mapping


def reset_selection() -> None:
    for d in range(3):
        for c in range(3):
            st.session_state[f"map_{d}_{c}"] = False


def queen_position() -> str:
    return "Estime" if st.session_state.v3_lumiere else "Disgrace"


def render(hand_cards: list[Carte]) -> None:
    """Rend la grille de sélection ; les états sont stockés dans `session_state`."""
    _ensure_state()

    st.markdown(
        """
        <style>
        div[data-testid="stHorizontalBlock"] > div:nth-child(5) input[type="checkbox"],
        div[data-testid="stHorizontalBlock"] > div:nth-child(6) input[type="checkbox"] {
            border-radius: 50% !important;
            transform: scale(1.3);
        }
        div[data-testid="stHorizontalBlock"] { align-items: center; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.write("#### Cartes à jouer")

    cols_config = [1.5, 1, 1, 1, 1, 1]

    # En-tête : images des 3 cartes + libellés statut
    h3 = st.columns(cols_config)
    h3[0].write("**Destinations**")
    for idx, c in enumerate(hand_cards):
        with h3[idx + 1]:
            st.image(load_image(c.famille, c.role), width="stretch")
            st.caption(f"Carte {idx + 1}")

    # Spacer pour aligner les labels statut sur les "Carte X"
    spacer_size = (200, 300)
    if hand_cards:
        ref_img = load_image(hand_cards[0].famille, hand_cards[0].role)
        spacer_size = ref_img.size
    spacer = Image.new("RGBA", spacer_size, (0, 0, 0, 0))
    with h3[4]:
        st.image(spacer, width="stretch")
        st.caption("**Lumière**")
    with h3[5]:
        st.image(spacer, width="stretch")
        st.caption("**Disgrâce**")

    # Lignes : Reine / Moi / Adv × 3 colonnes carte + 2 colonnes statut
    for d_idx, item in enumerate(A_ITEMS):
        r3 = st.columns(cols_config)
        r3[0].markdown(f"### {item['icon']} {item['label']}")
        for c_idx in range(3):
            key = f"map_{d_idx}_{c_idx}"
            r3[c_idx + 1].checkbox(
                "", key=key, on_change=_handle_mapping, args=(d_idx, c_idx)
            )
        if d_idx == 0:
            r3[4].checkbox("", key="v3_lumiere", on_change=_handle_status, args=("lumiere",))
            r3[5].checkbox("", key="v3_disgrace", on_change=_handle_status, args=("disgrace",))
        else:
            r3[4].write("")
            r3[5].write("")
