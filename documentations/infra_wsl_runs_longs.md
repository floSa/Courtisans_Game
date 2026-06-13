# Infra — faire tenir les runs longs sous WSL2

> Écrit le 13/06/2026 après une série de gels WSL qui ont fait échouer l'oracle
> de la brique 2.1e. À lire avant tout calcul long (oracle CFR+ tabulaire surtout).

## Le problème

Les runs longs (heures) dans la VM WSL2 gèlent par intermittence avec
`Wsl/Service/0x8007274c` (« le parti connecté n'a pas répondu »). La VM devient
injoignable ; seul `wsl --shutdown` côté Windows la ranime.

## La cause (vérifiée — issues GitHub microsoft/WSL)

Bug Microsoft connu, non corrigé : **échec d'allocation mémoire dans le noyau**
(« page allocation failure, order:7 », driver `hv_balloon`). Ce n'est PAS un
manque de RAM totale, c'est de la **fragmentation** : le « ballooning » de
Hyper-V rend en continu la RAM libérée à Windows, ce qui fragmente la mémoire
noyau jusqu'à ne plus trouver de bloc contigu. S'aggrave avec l'uptime de la VM
et le nombre de processus. Réfs : issues #11612, #12764, #9852.

## Pourquoi ça touche le CFR+ tabulaire et pas l'entraînement neuronal

L'oracle CFR+ garde en RAM des **millions de petits objets Python** (dicts de
regrets par info-set) pendant des heures → profil d'allocation qui fragmente
fort. PyTorch (Deep CFR, jeu réel) alloue de **gros blocs contigus** une fois →
fragmente peu. Donc le gel est surtout un artefact du **solveur tabulaire**, pas
une fatalité du jeu complet. L'oracle est de toute façon exponentiel : il ne
tournera JAMAIS sur le jeu réel, par nature.

## Mitigations appliquées (≠ cure garantie)

1. **`~/.wslconfig`** :
   ```
   [wsl2]
   memory=34359738368      # 32 Go fixes (hôte = 63 Go)
   swap=4294967296
   vmIdleTimeout=3600000
   [experimental]
   autoMemoryReclaim=disabled   # coupe le ballooning = la cause nommée
   ```
   S'applique au prochain `wsl --shutdown`.
2. **Couper les services concurrents** avant le run : `docker.service` est activé
   au boot (il relance dockerd + conteneurs uvicorn/streamlit). `sudo systemctl
   stop docker docker.socket containerd` (sudo interactif requis — à faire par
   Florian). Vérifier qu'ils ne redémarrent pas.
3. **Checkpoint/reprise** dans `solve_mini.py` (`COURTISANS_CKPT=...`) : sauvegarde
   des regrets/politiques cumulés **à chaque itération** → un gel coûte ≤1 itér.
4. **Réduire l'instance / les itérations** quand c'est scientifiquement neutre :
   l'oracle d'une brique se valide sur la plus petite instance qui montre le
   mécanisme. (Limite : un combo assassin+pioche a besoin de ≥9 cartes pour avoir
   une pioche — 3 familles × 3 rôles minimum.)
5. **tcmalloc/jemalloc** (`LD_PRELOAD`) : allocateurs anti-fragmentation, à
   installer (`apt`) — non fait (réseau WSL capricieux). Piste pour durcir encore.

## Le seul vrai test

Aucune de ces mitigations n'est garantie (bug MS). La preuve = un run qui tient
plusieurs heures sans geler. Ne jamais annoncer « réglé » avant de l'avoir
observé. Voir [[lecons-fiabilite-wsl]] dans la mémoire.
