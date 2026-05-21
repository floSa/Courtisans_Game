# Spécification Technique - Application Streamlit Courtisans

Ce document définit l'interface utilisateur et l'architecture de l'application Streamlit pour le jeu Courtisans.

## 1. Objectifs
- Permettre à un utilisateur de jouer contre l'IA (entrainée ou non).
- Visualiser graphiquement l'état du jeu (Plateau, Mains, Scores).
- Lancer des sessions d'entraînement depuis l'interface.

## 2. Structure de l'Interface (Layout)

### A. Sidebar (Contrôles & Entraînement)
Une barre latérale gauche pour les paramètres globaux.
- **Mode de Jeu** : "Jouer vs IA" ou "Entraînement".
- **Paramètres d'Entraînement** (si mode Entraînement activé) :
    - Nombre d'itérations (Parties).
    - Simulations MCTS (Profondeur de réflexion).
    - Taux d'apprentissage (Learning Rate).
    - Bouton "Lancer l'entraînement" (avec barre de progression).
- **Paramètres Partie** :
    - Choix du Modèle (Liste des fichiers `.pth` dans `models/`).
    - Bouton "Nouvelle Partie".

### B. Zone Principale (Le Plateau)

L'affichage est vertical, centré, pour imiter la "Table de Jeu".

#### 1. Zone Adverse (IA) - "Haut"
- Affichage des cartes collectées par l'IA (Domaine IA).
- **Style** : Cartes regroupées par Famille, superposées en éventail (offset vertical ou horizontal) pour voir le haut de chaque carte.

#### 2. Zone Reine (Banquet) - "Centre"
- **Fond** : Image `images/courtisans_reine_board.png`.
- **Superposition** :
    - Zone Haute (Lumière) : Cartes jouées en "Estime".
    - Zone Basse (Obscurité) : Cartes jouées en "Disgrâce".
- Les cartes sont affichées par Famille, alignées avec les emplacements du plateau.

#### 3. Zone Joueur (Moi) - "Bas"
- Affichage des cartes collectées par le Joueur (Domaine Perso).
- Même style que la zone IA (Miroir).

### C. Zone de Main (Interactions)
C'est ici que se fait le "Tour de Jeu".
- **Disposition** : 3 Colonnes (une par Carte en main).
- **Pour chaque Carte** :
    1.  **Image de la Carte** (Grande taille).
    2.  **Sélecteur de Destination** (Radio buttons ou Boutons avec icônes) :
        - 👑 Reine (Choix : Estime ou Disgrâce à préciser ?) -> *Note: Le choix Estime/Disgrâce se fait souvent en positionnant la carte. On peut ajouter un "Toggle" ou deux boutons Reine.*
        - 🤖 IA (Cadeau à l'adversaire).
        - 👤 Moi (Mon domaine).
- **Validation** :
    - Un gros bouton "JOUER LES CARTES".
    - **Logique** : Ce bouton est désactivé (ou affiche une erreur) tant que les contraintes ne sont pas respectées :
        - 1 Carte pour la Reine.
        - 1 Carte pour Soi.
        - 1 Carte pour l'Adversaire.
        - (Si Reine choisie, préciser Estime/Disgrâce).

## 3. Gestion des Assets (Images)
Le script chargera les images dynamiquement :
- Chemin : `images/{Famille}/{Type}.jpg`.
    - Familles : 0 à 5 (Nom des dossiers à vérifier).
    - Types : A, E, I, N, S.
- Redimensionnement à la volée avec PIL pour l'affichage (Optimisation).

## 4. Logique Technique

### État de session (`st.session_state`)
- `game_env` : Instance persistante de `GameEnv`.
- `ai_net` : Instance chargée du réseau `CourtisansNet`.
- `user_selections` : Dictionnaire stockant les choix temporaires pour les 3 cartes ({0: None, 1: None, 2: None}).

### Boucle de Jeu
1.  **Rendu** : On dessine le plateau complet à partir de `game_env`.
2.  **Input** : L'utilisateur configure ses 3 cartes.
3.  **Action** :
    - Au clic "Jouer", on traduit les sélections en un `action_idx` compatible avec `ActionMapper`.
    - On appelle `game_env.step(action_idx)`.
    - Si la partie n'est pas finie, l'IA joue immédiatement après (`game_env.step(ai_action)`).
    - `st.rerun()` pour rafraîchir l'affichage.

## 5. Entraînement (Back-office)
L'entraînement est une opération bloquante.
- Utilisation de `st.spinner()` ou barre de progression.
- Appel direct à la fonction `train()` de `mcts_network.py` (à adapter pour accepter un callback de progression si possible, sinon affichage console).
- Sauvegarde automatique du modèle et rechargement dans l'app.
