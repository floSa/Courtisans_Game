"""Smoke test headless de l'app Streamlit via streamlit.testing (AppTest)."""

from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "4")

from streamlit.testing.v1 import AppTest  # noqa: E402

at = AppTest.from_file("streamlit_app/courtisans_app.py", default_timeout=120)
at.run()
assert not at.exception, at.exception
print(f"Run initial OK — {len(at.sidebar.selectbox)} selectbox, {len(at.button)} bouton(s)")

# Changer d'adversaire → Aléatoire puis Réseau (modèle absent → warning, pas crash)
at.sidebar.selectbox[0].set_value("Aléatoire").run()
assert not at.exception, at.exception
at.sidebar.selectbox[0].set_value("Réseau AlphaZero (MCTS)").run()
assert not at.exception, at.exception
print("Changement d'adversaire OK")

# Mode entraînement (rendu seulement, sans lancer)
at.sidebar.radio[0].set_value("Entraînement").run()
assert not at.exception, at.exception
print("Mode entraînement OK")

print("AppTest : OK, aucune exception")
