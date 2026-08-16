# Conventions de code et méthode de travail

**Comment construire. Chaque règle est justifiée par une erreur réelle du projet, pas par un goût.**

Le **quoi** est dans [03_specification_moteur.md](03_specification_moteur.md).

---

## 1. La règle numéro un : les tests avant le code

**On écrit les 18 tests de conformité de [01](01_regles.md) §9 AVANT toute
ligne de moteur.** Ils échouent tous. Puis on écrit le moteur jusqu'à ce qu'ils passent.

> *Corrigé le 16/08.* Ce document annonçait « 17 tests » et les situait au §10. Le §9 de
> [01](01_regles.md) en contient **18**, C1 à C18 ; le §10 est le tableau des arbitrages.
> La même erreur figurait dans [00_index](00_index.md) et
> [03_specification_moteur](03_specification_moteur.md), corrigée aux deux endroits.

**Pourquoi.** Le projet a fait l'inverse pendant trois mois : moteur d'abord, validation par
scripts ponctuels lancés à la main. Résultat — le meurtre obligatoire et les tours inégaux
ont survécu à cinq briques successives et à un rapport de 2 695 lignes. **Aucun test ne
vérifiait qu'une implémentation respectait les règles.** C'est le manque le plus coûteux de
l'historique.

Corollaire : un test de conformité ne s'écrit pas en regardant le code. Il s'écrit en lisant
[01_regles.md](01_regles.md), et il cite la section de la règle
qu'il vérifie.

---

## 2. Une seule source de vérité

**Interdit absolu : dupliquer une logique de règle.** Pas de fichier par instance, pas de
copier-coller entre variantes, pas de « je duplique et j'adapte ».

**Pourquoi.** `courtisans_assassin.py` et `courtisans_combo.py` avaient un `_legal_actions`
identique au caractère près. Le défaut introduit dans le premier s'est propagé au second
sans que rien ne le signale. Quatre fichiers, 1 254 lignes, un seul bug, invisible.

**En pratique.** Une nouvelle variante de jeu = une nouvelle `GameConfig`, jamais un nouveau
fichier. Si une variante ne peut pas s'exprimer en configuration, c'est la configuration
qu'il faut étendre.

---

## 3. Pas de valeur en dur

Ni 6 familles, ni 5 rôles, ni 3 exemplaires, ni 2 joueurs, ni 12 actions, ni 90 cartes.
Tout vient de `GameConfig`.

**Pourquoi.** Une constante en dur oblige à copier le fichier pour changer la valeur — et on
retombe sur la section 2. Le `MAX_SLOTS = 9` de l'ancienne instance combo est exactement ça :
une valeur calculée à la main pour une configuration, avec un commentaire expliquant
pourquoi 9 et pas 6. Le prochain qui change la configuration ne lira pas le commentaire.

Test associé : A5 des critères d'acceptation — instancier 5 configurations distinctes et
vérifier que les tailles suivent.

---

## 4. Séparation stricte règles / IA / interface

Le module de règles ne contient **aucune** heuristique, évaluation, ou score de position.

**Pourquoi.** L'ancien `app/jeu.py` contenait `_pick_target_heuristic`, une heuristique d'IA
au milieu des règles. Conséquence : elle ne renvoyait `None` que si la liste de cibles était
vide, donc **aucune politique du projet n'a jamais refusé de tuer**, alors que le moteur le
permettait. Une règle du jeu a été perdue parce qu'une IA vivait dans le fichier des règles.

---

## 5. Déterminisme

- `reset(seed)` produit la même partie à chaque exécution, sur toute plateforme.
- Aucun appel à `random` global : une instance `Random(seed)` passée explicitement.
- Aucune dépendance à l'ordre d'itération d'un `set` ou d'un `dict` non ordonné dans une
  décision de règle.

**Pourquoi.** Sans déterminisme, un test qui échoue une fois sur cent est ignoré. Et un
résultat d'expérience n'est pas reproductible, ce qui rend le protocole expérimental
inutilisable.

---

## 6. Typage et outillage

| Point | Règle |
|---|---|
| Python | 3.12 (`.python-version` du dépôt) |
| Gestionnaire | `uv` |
| Lint | `ruff`, configuration existante du `pyproject.toml` — `line-length = 100`, règles `E, F, W, I, UP, B` |
| Typage | Annotations sur **toute** signature publique. `from __future__ import annotations`. |
| Tests | `pytest`, `testpaths = ["tests"]` |

Le cœur n'importe **ni OpenSpiel, ni PyTorch, ni NumPy**. Vérifié par un test d'import (A4).

**Pourquoi.** Un cœur en stdlib pure se teste en millisecondes, tourne partout, et ne casse
pas quand OpenSpiel change d'API. L'ancien code mélangeait `pyspiel` et les règles dans le
même fichier, ce qui rendait impossible de tester les règles sans instancier un jeu OpenSpiel.

---

## 7. Français, et honnêteté dans les noms

- Docstrings, commentaires et noms de domaine en **français** : `famille`, `role`, `estime`,
  `disgrace`, `domaine`, `poseur`, `proprietaire`.
- Termes techniques consacrés en anglais : `seed`, `checkpoint`, `tensor`, `infoset`.
- **Un nom ne ment pas.** Une fonction `resoudre_assassin` qui ne peut pas refuser de tuer
  s'appelle `tuer_obligatoirement`. Si le nom devient gênant, c'est le code qui est faux.

---

## 8. Ce qu'on écrit quand on ne sait pas

**Interdit** : un placeholder qui a l'air d'une valeur réelle, une valeur recopiée d'ailleurs
« parce que ça se ressemble », une section « Limites » vide par défaut.

**Obligatoire** : `TODO`, `à confirmer`, `non implémenté`, ou une exception explicite.

**Pourquoi.** Une valeur inventée qui a l'air juste est plus dangereuse qu'une erreur
visible. Ce document est écrit après un cas exact : une règle de retrait de cartes a été
inventée de toutes pièces, présentée avec une justification cohérente, et il a fallu une
relecture humaine pour la détecter.

---

## 9. Comment rendre compte

À chaque étape terminée, produire :

1. **Ce qui a été fait**, en une phrase.
2. **Les tests qui passent**, avec leur nombre — pas « les tests passent ».
3. **Ce qui a été trouvé et qui n'était pas prévu**, y compris les erreurs propres.
4. **Ce qui reste incertain**, explicitement.

**Distinguer systématiquement trois niveaux :**

| Niveau | Signification | Formulation |
|---|---|---|
| **Mesuré** | j'ai exécuté et lu le résultat | « mesuré : 475 000 info-sets » |
| **Déduit** | j'ai lu le code et raisonné | « déduit de `is_done` ligne 236 — non exécuté » |
| **Supposé** | je n'ai ni mesuré ni lu | « supposé, à vérifier » |

**Pourquoi.** Un audit antérieur a présenté comme mesuré le comportement de `is_done` à
4 joueurs, alors qu'il était déduit d'une docstring. La vérification par exécution, tentée
ensuite, a produit un harnais faux dont les chiffres ne voulaient rien dire. Sans les trois
niveaux, on ne sait plus ce qui tient.

---

## 10. Ce qui interdit de continuer

Conditions d'arrêt. En cas d'occurrence, on s'arrête et on remonte l'information — on ne
contourne pas.

| Condition | Action |
|---|---|
| Un test de conformité échoue | Corriger avant toute nouvelle fonctionnalité |
| Une règle de [01](01_regles.md) est ambiguë | Demander l'arbitrage, ne pas trancher seul |
| Un invariant de [03](03_specification_moteur.md) §5 ne peut pas être garanti | S'arrêter et le signaler |
| Le besoin de dupliquer un fichier apparaît | C'est le signe que la configuration est trop pauvre — l'étendre |
| Un chiffre ne peut pas être reconstruit par le lecteur | Le décomposer ou le retirer |
