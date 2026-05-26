"""Chemins et chargement des images du jeu."""

from __future__ import annotations

import os

import streamlit as st
from PIL import Image

from app.jeu import Role

IMAGE_DIR = "images"
FAMILLES_DIR = os.path.join(IMAGE_DIR, "familles_cartes")
BOARD_IMG = os.path.join(IMAGE_DIR, "courtisans_reine_board.png")
BACK_CARD_IMG = os.path.join(IMAGE_DIR, "back_card.png")

ROLE_TO_FILE = {
    Role.ASSASSIN: "A",
    Role.GARDE: "S",
    Role.NOBLE: "N",
    Role.ESPION: "E",
    Role.NEUTRE: "I",
}


@st.cache_data
def load_image(famille_idx: int, role_idx: int, visible: bool = True) -> Image.Image:
    """Charge et cache l'image d'une carte (face visible ou dos)."""
    if not visible:
        if os.path.exists(BACK_CARD_IMG):
            return Image.open(BACK_CARD_IMG)
        return Image.new("RGB", (200, 300), color="gray")

    fam_str = str(famille_idx + 1)
    role = Role(role_idx)
    letter = ROLE_TO_FILE[role]
    path_base = os.path.join(FAMILLES_DIR, fam_str, letter)
    for ext in (".jpg", ".png"):
        if os.path.exists(path_base + ext):
            return Image.open(path_base + ext)
    return Image.new("RGB", (200, 300), color="red")
