# Courtisans Game

Implémentation Python du jeu de cartes **Courtisans** avec une IA inspirée d'AlphaZero (MCTS + réseau de neurones résiduel) et une interface **Streamlit** pour jouer contre l'IA.

## Le jeu

Courtisans est un jeu de cartes d'influence où chaque joueur, à son tour, joue trois cartes : une au banquet central (chez la Reine, en Lumière ou en Obscurité), une dans sa propre collection, et une chez un adversaire. À la fin de la partie, les familles majoritairement en Lumière rapportent des points à ceux qui les collectionnent ; celles en Obscurité en font perdre.

Règles complètes : voir [`documentations/regles.md`](documentations/regles.md).

## Architecture

- **`app/jeu.py`** — moteur de jeu pur, garant des règles. Aucune logique d'IA.
- **`app/mcts_network.py`** — IA AlphaZero : MCTS + ResNet (`CourtisansNet`).
- **`streamlit_app/courtisans_app.py`** — interface de jeu.
- **`models/`** — poids entraînés (`model_2.pth`).

Détails techniques : [`documentations/architecture_technique.md`](documentations/architecture_technique.md).

## Quick start

Prérequis : **Python 3.12** et [`uv`](https://docs.astral.sh/uv/) installés.

```bash
# 1. Cloner
git clone git@github.com:floSa/Courtisans_Game.git
cd Courtisans_Game

# 2. Créer le venv et installer les dépendances
uv venv courtisans_env --python 3.12
# Windows :
courtisans_env\Scripts\activate
# Linux/macOS :
source courtisans_env/bin/activate

uv pip install -r requirements.txt

# 3. Lancer l'app Streamlit
streamlit run streamlit_app/courtisans_app.py
```

L'app s'ouvre sur `http://localhost:8501` — un modèle pré-entraîné (`models/model_2.pth`) est chargé automatiquement.

## Structure du projet

```
Courtisans_game/
├── app/                    # moteur + IA
│   ├── jeu.py
│   └── mcts_network.py
├── streamlit_app/          # interface
│   └── courtisans_app.py
├── models/                 # poids entraînés
├── images/                 # visuels des cartes et du plateau
├── documentations/         # règles + doc technique
├── pyproject.toml
└── requirements.txt
```
