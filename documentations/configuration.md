# Configuration et installation

Ce document détaille la mise en place de l'environnement de développement.

## 1. Prérequis

- **Python 3.12** (voir `pyproject.toml`).
- [`uv`](https://docs.astral.sh/uv/) recommandé pour la gestion d'environnement.
- (Optionnel) **GPU NVIDIA + CUDA** pour accélérer l'entraînement du réseau.

Vérifier l'installation :

```bash
python --version   # >= 3.12
uv --version
```

## 2. Environnement virtuel

```bash
uv venv courtisans_env --python 3.12

# Activation
# - Windows (CMD/PowerShell) :
courtisans_env\Scripts\activate
# - Linux/macOS :
source courtisans_env/bin/activate
```

## 3. Installation des dépendances

### A. PyTorch

La version `requirements.txt` installe la build par défaut (CPU). Pour le
support **CUDA**, installer PyTorch via l'index dédié :

```bash
# Exemple CUDA 12.1
uv pip install torch --index-url https://download.pytorch.org/whl/cu121
```

### B. Reste des dépendances

```bash
uv pip install -r requirements.txt
```

### C. Outils de dev (tests, lint)

```bash
uv pip install -e ".[dev]"
```

## 4. Lancement

### Interface Streamlit

```bash
streamlit run streamlit_app/courtisans_app.py
```

Accès : <http://localhost:8501>.

### CLI

```bash
python main.py train --iterations 100
python main.py play --model models/model_2.pth
```

### Tests

```bash
pytest
```

## 5. Notes

- L'app Streamlit utilise l'interpréteur Python du venv actif : le `streamlit`
  installé dans le venv lance un process Python qui hérite des dépendances du
  venv. Aucun risque de conflit avec une install globale tant que le venv est
  activé avant la commande.
- Si tu n'as pas de GPU NVIDIA, l'IA tournera sur CPU (plus lent à entraîner,
  mais fonctionnel pour l'inférence sur un modèle déjà entraîné).
