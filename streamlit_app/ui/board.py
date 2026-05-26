"""Rendu du plateau (zones Reine, domaines des joueurs)."""

from __future__ import annotations

from collections.abc import Iterable

import streamlit as st
from PIL import Image

from app.jeu import NUM_FAMILLES, Carte, Role
from streamlit_app.ui.assets import load_image


def _visible_to(c: Carte, perspective: int | None) -> bool:
    """Une carte est visible à `perspective` si elle est face visible OU
    si elle a été posée par ce joueur (mémoire des espions, via
    `proprietaire_idx`)."""
    if c.visible:
        return True
    if perspective is not None and c.proprietaire_idx == perspective:
        return True
    return False


def render_stack(cards: list[Carte], perspective: int | None = None) -> Image.Image | None:
    """Construit une image composite de cartes empilées verticalement (overlap 1/6).

    `perspective` : si fourni, les espions posés par ce joueur sont affichés
    face visible même si `c.visible == False` côté moteur.
    """
    if not cards:
        return None
    imgs = [load_image(c.famille, c.role, visible=_visible_to(c, perspective)) for c in cards]
    if not imgs:
        return None
    base_w, base_h = imgs[0].size
    overlap_y = base_h // 6
    total_h = base_h + (len(imgs) - 1) * overlap_y
    composite = Image.new("RGBA", (base_w, total_h), (0, 0, 0, 0))
    for i, img in enumerate(imgs):
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        composite.paste(img, (0, i * overlap_y), img)
    return composite


def render_zone_7cols(
    cards: Iterable[Carte],
    label: str | None = None,
    perspective: int | None = None,
) -> None:
    """Affiche une zone en 7 colonnes : Fam 1-3, Espions, Fam 4-6.

    `perspective` : index du joueur dont on adopte la perspective. Les
    espions posés par ce joueur sont affichés face visible **dans leur
    colonne de famille**, peu importe le `c.visible` côté moteur. Les
    espions adverses cachés restent dans la colonne centrale "Espions",
    face cachée.
    """
    if label:
        st.markdown(f"#### {label}")
    cols = st.columns(7)
    buckets: dict[int, list[Carte]] = {i: [] for i in range(7)}

    for c in cards:
        # Un espion *visible à la perspective* (parce que je l'ai posé)
        # est rangé dans sa colonne de famille, comme une carte normale.
        if c.role == Role.ESPION.value and not _visible_to(c, perspective):
            buckets[3].append(c)
        else:
            f_idx = c.famille
            buckets[f_idx if f_idx < 3 else f_idx + 1].append(c)

    for i in range(7):
        with cols[i]:
            current = buckets[i]
            if i == 3 and current:
                # Colonne espions adverses : face cachée forcée.
                imgs = [load_image(c.famille, c.role, visible=False) for c in current]
                base_w, base_h = imgs[0].size
                overlap_y = base_h // 6
                total_h = base_h + (len(imgs) - 1) * overlap_y
                composite = Image.new("RGBA", (base_w, total_h), (0, 0, 0, 0))
                for k, img in enumerate(imgs):
                    if img.mode != "RGBA":
                        img = img.convert("RGBA")
                    composite.paste(img, (0, k * overlap_y), img)
                st.image(composite, use_container_width=True)
            elif current:
                stack = render_stack(current, perspective=perspective)
                if stack:
                    st.image(stack, use_container_width=True)
            else:
                st.text("-")


def split_reine(plateau_cards: list[Carte]) -> tuple[list[Carte], list[Carte]]:
    """Retourne (cartes_estime, cartes_disgrace) du banquet central."""
    estime = [c for c in plateau_cards if c.position == "Estime"]
    disgrace = [c for c in plateau_cards if c.position == "Disgrace"]
    return estime, disgrace


def group_by_family(cards: list[Carte]) -> dict[int, list[Carte]]:
    g: dict[int, list[Carte]] = {f: [] for f in range(NUM_FAMILLES)}
    for c in cards:
        g[c.famille].append(c)
    return g
