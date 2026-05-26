# Courtisans Game

Implémentation Python du jeu de cartes **Courtisans** avec une IA inspirée
d'AlphaZero (MCTS + ResNet) et une interface **Streamlit** pour jouer contre
l'IA.

## Le jeu

Courtisans est un jeu de cartes d'influence où chaque joueur, à son tour,
joue trois cartes : une au banquet central (chez la Reine, en Lumière ou en
Obscurité), une dans sa propre collection, et une chez un adversaire. À la fin
de la partie, les familles majoritairement en Lumière rapportent des points à
ceux qui les collectionnent ; celles en Obscurité en font perdre.

Règles complètes : voir [`documentations/regles.md`](documentations/regles.md).

## Architecture

- `app/jeu.py` — moteur de jeu pur, garant des règles. Aucune logique d'IA.
- `app/mcts_network.py` — IA AlphaZero : MCTS + ResNet (`CourtisansNet`).
- `streamlit_app/` — interface (sous-modules `ui/`, `state.py`, `ai_runner.py`).
- `models/` — poids entraînés (`model_2.pth`).
- `tests/` — suite pytest (mapper, moteur, assassins).

Détails techniques : [`documentations/architecture_technique.md`](documentations/architecture_technique.md).
Audit & axes d'amélioration : [`documentations/ameliorations.md`](documentations/ameliorations.md).

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
```

> Note multi-comptes SSH : si tu as configuré GitHub avec un alias d'hôte
> (par ex. `github.com-perso`), remplace l'URL par
> `git@github.com-perso:floSa/Courtisans_Game.git`.

### Premier modèle (bootstrap)

Le fichier `models/model_2.pth` n'est plus commité (cf.
[`documentations/ameliorations.md`](documentations/ameliorations.md) point #23).
Pour disposer d'une IA fonctionnelle, soit on en initialise une rapidement,
soit on en entraîne une vraie :

```bash
# Option A — bootstrap rapide (poids aléatoires, joue au hasard)
python scripts/bootstrap_model.py

# Option B — petit entraînement (~5 min CPU)
python main.py train --iterations 50

# Option C — entraînement sérieux
python main.py train --iterations 500 --num-sims 50
```

Sans modèle, l'app fonctionne quand même : l'IA joue alors au hasard.

### Lancer l'interface

```bash
streamlit run streamlit_app/courtisans_app.py
```

L'app s'ouvre sur <http://localhost:8501>. Le modèle `models/model_2.pth` est
chargé automatiquement s'il est présent.

### CLI (sans interface)

```bash
# Entraîner
python main.py train --iterations 200 --num-sims 30 --seed 42

# Jouer en console
python main.py play --model models/model_2.pth
```

### Lancer les tests

```bash
uv pip install -e ".[dev]"
pytest
```

## Structure du projet

```
Courtisans_Game/
├── app/                      # moteur + IA
│   ├── jeu.py
│   └── mcts_network.py
├── streamlit_app/            # interface
│   ├── courtisans_app.py     # point d'entrée
│   ├── ai_runner.py
│   ├── state.py
│   └── ui/
│       ├── assets.py
│       ├── board.py
│       ├── hand_picker.py
│       └── logs.py
├── tests/                    # pytest
├── models/                   # poids entraînés
├── images/                   # visuels (cartes, plateau)
├── documentations/           # règles + doc technique + audit
├── main.py                   # CLI
├── pyproject.toml
└── requirements.txt
```
