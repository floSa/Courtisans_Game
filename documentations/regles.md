# Règles du jeu Courtisans

## Matériel et mise en place

- Un paquet de cartes représentant 6 familles, chaque famille ayant 5 rôles
  (Assassin, Garde, Noble, Espion, Neutre). 3 exemplaires de chaque carte →
  90 cartes au total.
- Selon le nombre de joueurs, on peut retirer un certain nombre de cartes du
  paquet (par convention dans cette implémentation : on utilise les 90 pour
  toute partie).
- Les cartes sont mélangées pour former la pioche.

## Déroulement de la partie

### Tour de jeu

À chaque tour, vous recevez 3 cartes et devez les jouer **toutes les trois**,
en les plaçant dans trois zones différentes :

1. Une carte au **banquet** (l'arène centrale, chez la Reine), soit en
   **Lumière** (Estime), soit en **Obscurité** (Disgrâce).
2. Une carte **chez vous** (votre domaine).
3. Une carte **chez un adversaire** (son domaine).

### Faces visibles / cachées

- Les rôles **Assassin, Garde, Noble, Neutre** sont posés **face visible**,
  peu importe la zone.
- Le rôle **Espion** est posé **face cachée**, peu importe la zone
  (y compris chez la Reine).
- Le joueur qui pose un espion **garde la connaissance de son identité**
  (famille / rôle). Les autres joueurs ne voient qu'un dos.
- En fin de partie, tous les espions sont retournés face visible pour le
  décompte.

## Effets des rôles

### Assassin

Quand un Assassin est posé, il **tue immédiatement une autre carte** :

- **Cible valide** : toute carte de la même zone (même position Estime/Disgrâce
  si chez la Reine, ou même domaine si posé dans un domaine) qui n'est **pas
  un Garde** et qui n'est **pas l'Assassin lui-même**.
- Un Assassin **peut** donc tuer un autre Assassin et un Espion (visible ou
  caché).
- Si plusieurs Assassins sont joués dans le même tour, ils tuent
  séquentiellement (queue de résolution).

L'IA peut choisir intelligemment quelle cible tuer parmi les valides, en
utilisant la connaissance de **qui a posé chaque carte** (`proprietaire_idx`)
pour décider stratégiquement (cf. ciblage MCTS B2 et heuristique B1).

### Garde

- **Immunisé** contre les Assassins : un Garde dans la zone d'un Assassin ne
  peut pas être tué.
- Valeur de scoring : 1 point.

### Noble

- Valeur de scoring : **2 points** (deux fois plus que les autres rôles).
- Aucun effet spécial.

### Espion

- Posé face cachée dans toutes les zones (cf. ci-dessus).
- Valeur de scoring : 1 point.
- Peut être tué par un Assassin (pas immunisé).

### Neutre

- Valeur de scoring : 1 point.
- Aucun effet spécial.

## Placement chez la Reine

- Dans le banquet central, les cartes peuvent être placées soit dans la zone
  supérieure (**Estime / Lumière**), soit dans la zone inférieure
  (**Disgrâce / Obscurité**).
- Ce placement détermine si les familles **rapportent ou font perdre** des
  points en fin de partie.

## Stratégie

- Si vous collectionnez une famille particulière, vous voudrez probablement la
  placer en **Lumière** pour qu'elle rapporte des points à vos cartes posées
  dans les domaines (les vôtres comme ceux des autres).
- À l'inverse, vous pouvez placer en **Disgrâce** les familles collectionnées
  par vos adversaires pour leur faire perdre des points.
- Les Espions et les Gardes ajoutent une couche d'incertitude et de protection
  qui rend l'interaction tactique riche.

## Fin de partie et décompte

Lorsque la pioche est épuisée **et** que plus aucun joueur n'a 3 cartes en
main pour jouer un tour complet, la partie se termine.

### Décompte

1. Pour chaque famille (1 à 6), on détermine son **statut** :
   - **Lumière** si elle a plus de cartes en Estime qu'en Disgrâce.
   - **Obscurité** si elle a plus de cartes en Disgrâce qu'en Estime.
   - **Neutre** si égalité (la famille ne rapporte rien).
2. Pour chaque carte posée dans un domaine :
   - Si sa famille est en **Lumière** → le propriétaire du domaine gagne
     `valeur` points (1 ou 2 selon le rôle).
   - Si sa famille est en **Obscurité** → le propriétaire du domaine **perd**
     `valeur` points.
   - Si sa famille est Neutre → 0 point.
3. Les espions sont retournés face visible avant ce décompte et comptent
   normalement.
4. Le **propriétaire du domaine** (`domaine_id` dans le code), pas celui qui
   a posé la carte (`proprietaire_idx`), est crédité ou débité des points.

Le joueur avec le plus de points remporte la partie.

---

## Mapping vers le code

| Concept            | Champ `Carte` ou méthode                       |
|--------------------|-----------------------------------------------|
| Identité (fam/rôle)| `famille`, `role`                              |
| Valeur de scoring  | `valeur` (2 pour Noble, 1 sinon)               |
| Zone Reine         | `position` ∈ {`"Estime"`, `"Disgrace"`, `None`}|
| Zone domaine       | `domaine_id` (index du joueur propriétaire)    |
| Face visible       | `visible` (`False` pour les Espions)           |
| Qui a posé         | `proprietaire_idx`                             |
| Décompte           | `GameEnv._calcul_scores()`                     |
| Effets assassins   | `GameEnv.step` + `resolve_assassin_manual`     |
