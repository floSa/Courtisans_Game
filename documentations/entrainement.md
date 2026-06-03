# Guide opérationnel — Lancer un entraînement

Ce document rassemble **toutes les commandes pratiques** pour lancer un
entraînement de l'IA Courtisans, ce qu'il faut surveiller pendant, et comment
gérer les erreurs classiques. Lecture obligatoire avant le premier `train`.

## 1. Setup environnement (à faire une fois)

### Windows / WSL Ubuntu

```bash
# Si uv n'est pas encore installé dans WSL :
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Création du venv
cd ~/Projets/Prive/Courtisans-Games
uv venv courtisans_env --python 3.12
source courtisans_env/bin/activate
```

### Installation de PyTorch

Choisis **une seule** des deux options :

```bash
# Option CPU (validation, machine sans GPU)
uv pip install -r requirements.txt

# Option GPU (CUDA 12.1 — pour ta 4060Ti)
uv pip install torch --index-url https://download.pytorch.org/whl/cu121
uv pip install numpy pillow streamlit
```

### Vérification rapide

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available(), '| device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

Pour le GPU sous WSL, tu dois voir `CUDA: True | device: NVIDIA GeForce RTX 4060 Ti`.
Si tu vois `False`, vérifie que `nvidia-smi` fonctionne dans WSL (besoin du driver NVIDIA Windows + WSL CUDA support).

## 2. Commandes recommandées

### A. Smoke test (~30 secondes sur CPU)

À lancer dès qu'on touche au code pour vérifier que rien n'est cassé :

```bash
OMP_NUM_THREADS=2 python main.py train \
  --iterations 5 --num-sims 10 \
  --mcts-batch-size 4 --num-worlds 1 \
  --memory-size 200
```

Ce que tu dois voir :
- `No model at models/model_2.pth` (la première fois).
- `Aucun champion préexistant — poids initiaux comme baseline.`
- `Final candidate saved: …` puis `Initial best saved: …`
- Pas de traceback.

### B. Mini-run de validation GPU (~10-20 min sur 4060Ti)

À lancer chez toi avant le vrai run pour vérifier que le GPU est bien utilisé
et que la loss descend :

```bash
python -u main.py train --iterations 500 --num-sims 80 \
  --mcts-batch-size 32 --num-worlds 3 --memory-size 50000 \
  2>&1 | tee train_500.log
```

À surveiller :
- `Iter 10 | loss=X`, `Iter 20 | loss=Y` (doit globalement descendre).
- `Arena (iter 50): wins=… losses=… draws=… winrate=X.YZ`
- `Champion promu : …` quand winrate ≥ 0.55 sinon `Champion conservé`.

### C. Vrai entraînement (~3 h sur 4060Ti) — config validée

```bash
python -u main.py train --iterations 1500 --num-sims 80 \
  --mcts-batch-size 1 --num-worlds 1 --memory-size 100000 \
  2>&1 | tee train_1500.log
```

GPU ~40%, ~5-6s/iter, ~1800 itérations en 3h. C'est la config qui maximise le
**débit réel** (optimizer steps/heure) sur cette machine.

## 3. Tous les flags du CLI

| Flag | Défaut | Effet | Quand l'augmenter |
|---|---|---|---|
| `--iterations N` | 100 | Nb de parties self-play | Plus = meilleure IA. 500 = mini, 5000+ = sérieux |
| `--num-sims N` | 50 | Simulations MCTS par coup | Plus = meilleurs labels. CPU : 30-50. GPU : 80-200 |
| `--mcts-batch-size N` | 1 | Taille du batch d'évaluation MCTS (L3#3.1) | GPU : 32-64. CPU : 4-16 |
| `--num-worlds N` | 1 | Nb de déterminisations PIMC (L2#2.1) | 3-5 réduit la variance des labels |
| `--memory-size N` | 50000 | Taille du replay buffer (L1#1.1) | 50k pour < 2000 itérations, 100k+ au-delà |
| `--temperature-threshold N` | 10 | Nb de coups en T=1 (L1#1.3) | 10-15 pour 30 coups/partie |
| `--weight-decay X` | 1e-4 | Régularisation AdamW (L1#1.4) | Rarement à toucher |
| `--no-family-augmentation` | (off) | Désactive l'augmentation σ (L2#2.2) | Pour debug seulement |
| `--seed N` | None | Reproductibilité | Pour comparer des configs |
| `--model-dir PATH` | `models` | Où sauver les checkpoints | Différent pour chaque expérience |

## 4. Astuces opérationnelles

### Limiter le CPU pour ne pas saturer la machine

PyTorch utilise par défaut **tous les cœurs** disponibles pour ses matmul.
Sur une machine que tu veux pouvoir continuer à utiliser pendant le train :

```bash
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
```

Sur GPU c'est moins critique mais ça reste utile pour la partie CPU
(préparation des batchs, MCTS pur Python).

### Logs en temps réel

`tail -20` qui était dans ma première démo **bloque** jusqu'à la fin (le pipe
n'écoule rien tant que la source ne ferme pas). Utilise plutôt :

```bash
python -u main.py train ... 2>&1 | tee train.log
```

- `-u` désactive le bufferisation de Python (chaque `print`/`log` apparaît immédiatement).
- `tee` écrit dans le fichier ET affiche.

### Monitoring GPU en parallèle

Dans un autre terminal :

```bash
nvidia-smi -l 2
```

(Refresh toutes les 2 secondes.) Tu dois voir `GPU-Util` à 60-95 % pendant
les phases MCTS. Si c'est très bas (<20 %) c'est que le batched evaluator
ne sature pas la 4060Ti — peut-être augmenter `--mcts-batch-size`.

### Arrêter proprement

```
Ctrl-C
```

Les checkpoints intermédiaires (`model_2_ckpt_*.pth`) restent valides. Le
`model_2.pth` reflète le dernier *best* promu par l'arena.

## 5. Convention de fichiers

| Fichier | Quand mis à jour | Utilisé par |
|---|---|---|
| `models/model_2.pth` | À chaque promotion arena | Streamlit, `play_vs_ai`, arena baseline |
| `models/model_2_candidate.pth` | Fin de chaque run | Reprendre l'entraînement |
| `models/model_2_ckpt_{N}.pth` | Tous les `checkpoint_every=25` épisodes | Reprise / debug |

Tous les `.pth` sont gitignorés. Pour partager un modèle avec quelqu'un, soit
Git LFS, soit transfert manuel.

## 6. Reprise d'entraînement

Quand tu relances `python main.py train ...`, le script tente de charger
`models/model_{N}.pth` comme champion initial. Donc :
- Premier run : `No model at …` → poids initiaux.
- Runs suivants : `model_2.pth` est chargé → le candidate part au niveau du
  best précédent et l'arena évalue l'amélioration.

**Pour repartir de zéro** : `rm models/model_2*.pth` avant de lancer.

## 7. Erreurs classiques

### `RuntimeError: Error(s) in loading state_dict … Missing key(s)`

Le `state_dict` du fichier ne correspond pas à l'architecture actuelle.
Causes possibles :
- Tu as un vieux `.pth` entraîné avec BatchNorm (avant la bascule LayerNorm).
- Tu as un vieux `.pth` sans `policy_head_target` (avant B2).
- Le `state_vector_size` a changé (avant l'ajout des compteurs d'espions cachés).

`load_model()` détecte ces cas et logge un message clair. Solution :
`rm models/model_2*.pth` et ré-entraîner.

### Machine ralentie, ventilateur à fond

PyTorch sature tous les cœurs. Coupe avec `Ctrl-C` et relance avec
`OMP_NUM_THREADS=4` (ou moins).

### `Command 'python' not found`

WSL Ubuntu n'aliase pas `python` vers `python3`. Soit tu utilises `python3`,
soit tu actives ton venv (`source courtisans_env/bin/activate`) qui crée
l'alias `python` → le Python du venv.

### `CUDA out of memory`

Trop gros `--mcts-batch-size` ou trop de workers. Diminue `--mcts-batch-size`
(32 → 16) ou ferme les autres apps consommatrices de GPU.

## 8. Que faire des logs ?

Garde-les ! Les fichiers `train_*.log` permettent de :
- Voir la courbe de loss (`grep "Iter " train.log`).
- Voir l'historique des promotions arena (`grep "Champion promu" train.log`).
- Diagnostiquer une régression (`grep -i "warning\|error" train.log`).

## 9. Retour d'expérience — optimisation GPU (9600X + RTX 4060 Ti 16 Go, WSL2)

**Testé le 2026-05-26.** Toutes les configs ci-dessous ont été mesurées en conditions réelles.

### Ce qui ne marche PAS

#### `--num-worlds 3` sur GPU
La documentation d'origine recommandait `--num-worlds 3 --mcts-batch-size 32`.
En pratique sur la 4060 Ti :
- **13s/iter** (au lieu de 5-6s attendues)
- GPU à 55%, CPU à 14%
- En 3h : seulement ~750 iterations → **ne pas utiliser** pour un run limité en temps.

#### `--parallel-games 6` (self-play multi-threadé)
Le flag `--parallel-games N` a été ajouté pour lancer N parties simultanément via
`ThreadPoolExecutor`. Résultat décevant sur GPU :
- GPU à **85%** en apparence → mais c'est trompeur.
- En réalité, tous les threads partagent le **même stream CUDA** → les appels GPU
  se sérialisent quand même.
- **66.5s/iter** pour 6 parties = 11s/partie (pire que les 8.5s séquentielles).
- En 3h : seulement **~160 iterations** (contre ~1800 en séquentiel).

**Conclusion** : `--parallel-games > 1` augmente l'utilisation affichée du GPU sans
augmenter le débit réel. Ne l'utiliser que si on cherche à saturer la VRAM pour une
raison précise. Pour vraiment paralléliser il faudrait des streams CUDA séparés par
thread ou du `torch.multiprocessing` avec processus indépendants.

#### `--mcts-batch-size 64` seul (sans parallel-games)
GPU passe de 55% à **36%** — pire qu'avant. Le batch MCTS attend d'avoir 64 feuilles
avant chaque forward : ça allonge les pauses entre appels GPU.

### Ce qui marche

#### Config optimale validée pour un run ~3h sur 4060 Ti

```bash
python -u main.py train --iterations 1500 --num-sims 80 \
  --mcts-batch-size 1 --num-worlds 1 --memory-size 100000 \
  2>&1 | tee train_1500.log
```

| Métrique | Valeur |
|---|---|
| Temps/iter | ~5-6s |
| Iterations en 3h | ~1800 |
| GPU (Task Manager 3D) | ~40% |
| Température GPU | ~43°C |
| VRAM utilisée | ~1.5 Go / 16 Go |

Le GPU à 40% peut sembler faible, mais c'est la limite de l'architecture Python
MCTS mono-thread : le CPU parcourt l'arbre (GIL), le GPU attend. C'est structurel,
pas un problème de config.

### Piste d'amélioration future

Pour dépasser 40% GPU de façon honnête, il faudrait :
1. **`torch.multiprocessing.spawn`** — N processus indépendants, chacun avec son
   contexte CUDA, qui envoient leurs samples dans une queue partagée.
2. **Réécrire le MCTS en C++/Cython** — supprime le GIL du chemin critique.
