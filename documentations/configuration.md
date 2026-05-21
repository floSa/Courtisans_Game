# Guide de Configuration et d'Installation - Courtisans AI

Ce document explique comment configurer l'environnement de développement pour le projet **Courtisans AI**, installer les dépendances nécessaires (notamment PyTorch avec support CUDA), et lancer l'application Streamlit.

## 1. Prérequis

Assurez-vous d'avoir installé :
- **Python 3.10 ou supérieur** (vérifiez avec `python --version` dans un terminal).
- **Une carte graphique NVIDIA** (recommandé pour l'IA) avec des pilotes à jour pour profiter de CUDA.

## 2. Création de l'Environnement Virtuel

Il est recommandé d'utiliser un environnement virtuel pour isoler les dépendances du projet.

1. Ouvrez un terminal (PowerShell ou Invite de commandes) à la racine du projet `Courtisans_game`.
2. Créez l'environnement virtuel (nous l'appellerons `courtisans_env`) :
   ```cmd
   python -m venv courtisans_env
   ```

## 3. Activation de l'Environnement

Avant d'installer quoi que ce soit ou de lancer le jeu, vous devez activer l'environnement.

**Si vous utilisez l'Invite de commandes (CMD) :**
```cmd
courtisans_env\Scripts\activate
```

**Si vous utilisez PowerShell :**
```powershell
.\courtisans_env\Scripts\activate
```

*Note : Une fois activé, vous devriez voir `(courtisans_env)` s'afficher au début de votre ligne de commande.*

## 4. Installation des Dépendances

### A. PyTorch avec Support CUDA (Important)
Pour que l'IA (le réseau de neurones) fonctionne rapidement et utilise votre carte NVIDIA RTX 4060Ti, vous devez installer la version spécifique de PyTorch compatible CUDA.

Exécutez cette commande (avec l'environnement activé) :
```cmd
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```
*Cette étape peut prendre quelques minutes car les fichiers sont volumineux.*

### B. Autres Dépendances
Installez ensuite les autres bibliothèques requises (Streamlit, Numpy, Pillow...) :
```cmd
pip install -r requirements.txt
```

## 5. Lancement de l'Application

L'application utilise **Streamlit**. Pour la lancer, utilisez la commande suivante depuis la racine du projet :

```cmd
streamlit run streamlit_app/courtisans_app.py
```

### Accès
Une fois lancée, l'application ouvrira automatiquement votre navigateur. Si nécessaire, vous pouvez y accéder manuellement à l'adresse suivante :
- **Local URL :** [http://localhost:8501](http://localhost:8501)

## 6. Note sur la Logique d'Exécution

Vous vous demandez peut-être : *« Quand l'application Streamlit exécute le code du Jeu ou du réseau de neurones, utilise-t-elle bien mon environnement virtuel ? »*

**La réponse est OUI.**

Voici pourquoi :
1. Lorsque vous tapez `streamlit run ...` dans votre terminal **où l'environnement `courtisans_env` est activé**, vous lancez le programme `streamlit` qui est installé **dans** cet environnement.
2. Tout le processus Python initié par Streamlit tourne donc avec l'interpréteur Python de votre environnement virtuel.
3. Lorsque le code fait des imports (ex: `from app.jeu import ...` ou utilise `mcts_network`), il cherche les modules et les bibliothèques (comme `torch` ou `numpy`) **uniquement** dans cet environnement actif.

Il n'y a donc aucun risque de conflit avec une installation globale de Python, tant que vous lancez bien la commande `streamlit` depuis votre terminal activé.
