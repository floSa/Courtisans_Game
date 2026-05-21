# Documentation Technique - Courtisans AI

Ce document détaille l'architecture technique du projet et la logique d'implémentation pour l'IA du jeu Courtisans.

## Architecture Globale

Le projet suit une architecture stricte de **séparation des responsabilités** :

1.  **Le Moteur de Jeu (`app/jeu.py`)** : Il est l'unique garant des règles. Il ne contient **aucune** logique d'IA.
2.  **Le Cerveau (`app/mcts_network.py`)** : Il contient l'algorithme MCTS et le Réseau de Neurones. Il pilote le jeu pour l'entraînement.

---

## 1. Moteur de Jeu (`app/jeu.py`)

Ce module gère l'état du monde et les règles. Il a été refondu pour correspondre exactement aux règles officielles (tour complet de 3 cartes).

### Concepts Clés

*   **État (State)** : Représente le plateau (cartes chez la Reine, cartes chez les joueurs) et la main du joueur courant (3 cartes).
*   **Action Atomique** : Contrairement à l'ancienne version qui jouait carte par carte, une "Action" ici représente **le tour complet d'un joueur**.
    *   Le joueur a 3 cartes en main : A, B, C.
    *   Il doit en placer une chez la Reine, une chez lui, une chez l'adversaire.
    *   Il y a $3! = 6$ permutations possibles des cartes.
    *   Pour la carte Reine, 2 choix : "Lumière" (Estime) ou "Obscurité" (Disgrâce).
    *   Pour la carte Adversaire, choix de la cible (si > 2 joueurs).
    *   **Taille de l'Espace d'Action** : $6 \times 2 \times (NbJoueurs - 1)$.
        *   Pour 2 joueurs : $6 \times 2 \times 1 = 12$ actions possibles.

### Classe `GameEnv`

*   `__init__(num_players)` : Initialise une partie.
*   `get_state_vector()` : Convertit l'état du jeu en un vecteur numérique (Tensor) pour le réseau de neurones.
    *   Format One-Hot Encoding : Chaque emplacement et type de carte est représenté par des 0 et 1.
    *   *Note importante* : La main est toujours triée avant encodage pour garantir que le réseau ne dépende pas de l'ordre de la pioche.
*   `step(action_idx)` :
    1.  Décode l'index (0-11) en instructions de jeu (Quelle carte où ?).
    2.  Applique les effets (Pose des cartes, Révélation).
    3.  Gère les pouvoirs spéciaux (Assassins) automatiquement (ou via heuristique aléatoire pour l'instant).
    4.  Passe au joueur suivant.
    5.  Retourne : `(new_state, reward, done)`.

---

## 2. Intelligence Artificielle (`app/mcts_network.py`)

Ce module contient l'intelligence basée sur AlphaZero.

### Réseau de Neurones (`CourtisansNet`)
C'est un réseau de neurones résiduel (ResNet) profond.
*   **Entrée** : Le vecteur d'état fourni par `GameEnv`.
*   **Sortie 1 (Policy)** : Un vecteur de probabilités de taille 12 (pour 2 joueurs). Il prédit le "meilleur coup" parmi les combinaisons possibles.
*   **Sortie 2 (Value)** : Un scalaire entre -1 (Défaite) et +1 (Victoire). Il estime les chances de gagner depuis l'état actuel.

### Algorithme MCTS (Monte Carlo Tree Search)
L'algorithme de recherche qui permet à l'IA de "réfléchir" en simulant le futur.
1.  **Sélection** : Il parcourt l'arbre des possibles en utilisant les probabilités du réseau (Prior) et les résultats des simulations précédentes (Value).
2.  **Expansion** : Quand il atteint une nouvelle situation, il demande au Réseau de Neurones de l'évaluer.
3.  **Simulation** : Dans notre cas, on utilise le réseau pour estimer la valeur directement (pas de "Rollout" aléatoire complet jusqu'à la fin, méthode AlphaZero pure).
4.  **Backpropagation** : Il remonte l'information "C'est une bonne/mauvaise branche" jusqu'à la racine.

### Boucle d'Entraînement (`train`)
C'est le chef d'orchestre qui lie les fichiers :
1.  Il importe `GameEnv` depuis `jeu.py`.
2.  Il lance des parties **AI vs AI** (Self-Play).
3.  Il stocke les situations rencontrées.
4.  Il entraîne le `CourtisansNet` à mieux prédire ces situations.
5.  Il sauvegarde le modèle sous `models/model_{N}.pth`.

---

## Résumé des Modifications (Plan)

Je vais nettoyer le code actuel pour respecter cette structure :
1.  **`jeu.py`** : Suppression de tout le code MCTS/NN. Ajout de la logique "3 cartes par tour".
2.  **`mcts_network.py`** : Suppression de la classe `CourtisansGame` (placeholder). Importation réelle de `GameEnv` depuis `jeu.py`.

Cette séparation garantit un code propre, maintenable et conforme à votre demande.
