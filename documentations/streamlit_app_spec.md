# Spécification — Application Streamlit Courtisans

Ce document décrit l'organisation de l'interface et le flux d'interaction.

## 1. Objectifs

- Permettre à un humain de jouer contre l'IA (entraînée ou non).
- Visualiser graphiquement l'état du jeu (plateau, mains, scores).
- Lancer des sessions d'entraînement depuis l'interface.

## 2. Organisation des modules

```
streamlit_app/
├── courtisans_app.py   # point d'entrée (orchestration + layout principal)
├── state.py            # init / new game du st.session_state
├── ai_runner.py        # sélection de l'action IA + chaîne assassins
└── ui/
    ├── assets.py       # chemins images + load_image (cached)
    ├── board.py        # render_zone_7cols, render_stack, split Reine
    ├── hand_picker.py  # grille de sélection 3×3 + statut Lumière/Disgrâce
    └── logs.py         # rendu de l'historique des tours
```

- **`courtisans_app.py`** se contente d'orchestrer : init session, sidebar,
  rendu du plateau, branchement des callbacks. ~235 lignes.
- Toute la logique d'affichage est dans `ui/`, et toute la logique IA dans
  `ai_runner.py` — ce qui rend la couche UI testable en isolation.

## 3. Layout

### A. Sidebar

- **Mode de jeu** : "Jouer vs IA" ou "Entraînement".
- **Mode Entraînement** :
  - Nombre de parties (`iterations`).
  - Simulations MCTS par coup (`num_sims`).
  - Learning rate.
  - Bouton "Lancer l'entraînement" + barre de progression.
- **Mode Jouer vs IA** :
  - Slider "Simulations MCTS (IA)" : profondeur de réflexion à l'inférence.
  - Bouton "Nouvelle Partie".

### B. Zone principale

L'affichage est vertical, centré (max-width 950 px) pour imiter une table :

1. **Domaine adversaire (IA)** — 7 colonnes : Fam 1-3, Espions (face cachée),
   Fam 4-6.
2. **Banquet Reine** :
   - Zone haute "Estime" (Lumière).
   - Image de fond `images/courtisans_reine_board.png`.
   - Zone basse "Disgrâce" (Obscurité).
3. **Domaine joueur** — même mise en page que la zone IA.

### C. Zone de main

Pendant le tour du joueur humain et sans assassin en attente :

- 3 cartes affichées en image taille réelle.
- Grille `3 destinations × 3 cartes` (cases à cocher) : Reine / Mon Domaine /
  Adversaire. Les conflits ligne/colonne sont auto-décochés.
- 2 cases statut Reine (Lumière / Disgrâce) — mutuellement exclusives.
- Bouton **VALIDER L'ACTION** : passe en `primary` quand l'assignation est
  complète.

### D. Résolution d'un assassin (humain)

Si `env.pending_assassin_context` est non-nul et que c'est le tour du joueur :

- L'UI bascule en mode "résolution assassin".
- Radio listant les cibles valides + option `(passer)`.
- Bouton "Résoudre l'assassin" qui appelle `env.resolve_assassin_manual()`.
- La file restante (`_pending_assassins_queue`) est traitée automatiquement
  via plusieurs allers-retours UI tant qu'il reste des assassins en attente.

### E. Logs

Expander en bas de page, affiche les tours dans l'ordre antéchronologique
avec mini-images des 3 cartes jouées.

## 4. Flux côté code

### State (`session_state`)

Initialisé par `streamlit_app.state.init_session()` :

| Clé                 | Type      | Rôle |
|---------------------|-----------|------|
| `game_env`          | `GameEnv` | Instance persistante du moteur. |
| `game_over`         | `bool`    | Drapeau de fin de partie. |
| `logs`              | `list`    | Historique des tours (dicts). |
| `interaction_mode`  | `str`     | `"playing"` ou autre (réservé). |
| `error_msg`         | `str?`    | Message affiché sous le bouton Valider. |
| `v3_lumiere/...`    | `bool`    | État des cases cochées (gérées par `hand_picker`). |
| `map_{d}_{c}`       | `bool`    | Cases de la grille destinations × cartes. |

### Adversaires

La sidebar propose trois adversaires (`ai_runner.GREEDY` / `NETWORK` /
`RANDOM`) :

- **Greedy PIMC** (défaut) : `greedy_action_main` / `greedy_action_target`
  avec `num_worlds` déterminisations (slider « Mondes PIMC »). Aucun modèle
  requis, agent le plus fort mesuré.
- **Réseau AlphaZero** : MCTS sur `models/model_2.pth` (chargé via
  `@st.cache_resource`, warning si absent → fallback aléatoire).
- **Aléatoire** : action légale uniforme.

### Action joueur

1. L'utilisateur configure la grille puis clique sur **VALIDER**.
2. `hand_picker.get_mapping_result()` retourne `{0: idx, 1: idx, 2: idx}` ou
   `None`.
3. `env.mapper.encode((perm), queen_pos, 0)` → `action_idx`.
4. `env.step(action_idx)` :
   - si `info["assassin_pending"]` → l'UI rerender en mode résolution ;
     chaque assassin du joueur se résout manuellement (le sélecteur
     réapparaît tant que la file n'est pas vide).
5. Le tour de l'IA n'est plus déclenché dans le callback : un bloc en tête de
   script joue l'IA dès que `env.current_player != HUMAN` (donc aussi après
   une résolution d'assassin humaine), puis
   `ai_runner.resolve_ai_assassins()` résout la chaîne d'assassins de l'IA
   (ciblage greedy PIMC, ou heuristique B1 pour réseau/aléatoire).

### Entraînement

Bouton "Lancer l'entraînement" → appel à `app.mcts_network.train(config=...)`
avec un `progress_callback` qui met à jour la barre de progression Streamlit.
Sauvegarde finale : `models/model_2.pth`.

## 5. Assets

- `images/familles_cartes/{1..6}/{A,E,I,N,S}.{jpg|png}` :
  - dossiers `1` à `6` pour les 6 familles ;
  - lettres `A=Assassin, S=Garde, N=Noble, E=Espion, I=Neutre`.
- `images/back_card.png` : dos générique (utilisé pour les espions et la
  colonne face cachée).
- `images/courtisans_reine_board.png` : fond du banquet central.

Les images sont chargées via `streamlit_app.ui.assets.load_image()` qui est
décoré `@st.cache_data` — le coût de chargement disque est payé une seule fois.
