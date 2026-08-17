# PILOTE — ce que tu as à faire

**Le seul document qui te parle. Quelle action, quel prompt, quelle conversation, et à quoi reconnaître que c'est fait.**

Corpus de référence, pour toi et pour les agents :
[documentations/00_index.md](documentations/00_index.md).

Mis à jour le 16/08/2026, après audit croisé par deux auditeurs indépendants.

---

## Où on en est

| | |
|---|---|
| Étape en cours | **Action 3 terminée — les huit étapes.** 502 tests, tous verts ; les 8 critères d'acceptation atteints |
| Prochaine action | **Action 4 — l'audit croisé**, dans une conversation neuve |
| Bloquant | **Rien.** Deux reports assumés, écrits dans le README : canonicalisation et encodage par cible. |

Le dépôt est poussé sur la branche `moteur-conforme` de
[floSa/Courtisans_Game](https://github.com/floSa/Courtisans_Game), avec un historique
indépendant de `main` et de `cfr-pivot` : c'est un moteur neuf, pas une correction de
l'ancien.

**Mis à jour le 16/08 après l'étape 1.** Trois arbitrages ont été rendus en cours de route :
les instances historiques ne sont plus reproduites (elles violent les règles), le compteur
« Espions morts non révélés » est supprimé (une carte tuée est révélée), et les nœuds de
chance sont explicites dans l'adaptateur OpenSpiel, pas dans le cœur. Cinq erreurs de
documentation ont été corrigées au passage — détail en fin de ce document.

**Ce qui vient de se passer.** Deux auditeurs indépendants ont relu les règles et le vecteur
d'état, sans voir le raisonnement qui les avait produits. Ils ont trouvé **onze défauts dans
les règles** dont six bloquants, et **six défauts dans le vecteur d'état** dont deux qui
rendaient la phase de ciblage tout simplement injouable. Tout est corrigé, sauf quatre points
qui demandent ta décision.

Le protocole d'audit croisé vient donc de prouver son utilité avant même d'avoir servi sur du
code.

---

## Action 1 — Relire les règles (fait, mais relis)

**Les quatre questions bloquantes sont tranchées.** Pour mémoire :

| # | Réponse |
|---|---|
| L'influence au banquet | **en valeur** — Noble = 2, autres = 1, au banquet comme en domaine |
| Une carte tuée | **révélée**, va à la défausse **publique** — donc le résidu est exactement calculable |
| Le poseur d'une carte visible | **non tracé** — sans intérêt ; on ne trace que les cartes cachées |
| Familles > joueurs | **oui** — sinon chacun se replie sur sa famille et aucune alliance n'émerge |

Il reste sept questions de fond au §11 de
[documentations/01_regles.md](documentations/01_regles.md), **aucune ne bloque**. Elles
portent sur le rôle stratégique du Garde, du Neutre, et sur la validité des critères de
réussite B1 à B7.

**Une seule chose vraiment importante ici : relis `01_regles.md` en entier.** Constructeur et
auditeur liront tous deux ce document ; une règle mal rédigée là ne sera rattrapée par aucun
audit en aval. C'est le seul filet.

---

## Action 2 — Créer le dépôt neuf

**Pour toi. Cinq minutes.**

Tu as choisi de repartir sur un dossier et une branche vierges. Concrètement :

1. créer le nouveau dossier et y initialiser un dépôt git ;
2. y copier **uniquement** `PILOTE.md`, `documentations/` et `prompts/` ;
3. depuis l'ancien dépôt, récupérer `app/greedy_bot.py` et `cfr/solve_mini.py` — ce sont les
   deux seuls fichiers de code qui resservent, l'un comme référence de comportement, l'autre
   pour l'oracle ;
4. dans l'ancien dépôt, poser un tag `alphazero-final` pour que l'historique reste
   consultable.

**Fait quand :** le nouveau dépôt contient les documents, et rien d'autre que les deux
fichiers de code cités.

---

## Action 3 — Construire le moteur

**Conversation NEUVE.** Colle le bloc de
[prompts/01_moteur_construction.md](prompts/01_moteur_construction.md), donne l'accès au
nouveau dépôt.

L'agent doit d'abord te répondre en dix lignes : ce qu'il a compris, ce qui lui semble
ambigu, ce qu'il compte faire. **Aucun code avant ta réponse.**

Puis il avance en 8 étapes et **s'arrête à chaque étape**. Les étapes 1 et 2 produisent des
tests **tous rouges** — c'est le but : les tests sont écrits avant le moteur.

**Ce que tu dois recevoir à chaque étape**, format imposé par
[documentations/08_modele_compte_rendu.md](documentations/08_modele_compte_rendu.md) :

1. ce qui a été fait, en une phrase
2. les tests, **avec leur nombre** et la commande pour les rejouer
3. ce qui a été trouvé et n'était pas prévu, y compris ses propres erreurs
4. ce qui reste incertain
5. chaque chiffre, décomposé

**Renvoie-le au travail si tu vois :**

| Symptôme | Ce que ça cache |
|---|---|
| « les tests passent » sans nombre | invérifiable |
| section « incertain » vide | toujours suspect |
| une affirmation sans MESURÉ / DÉDUIT / SUPPOSÉ | un raisonnement présenté comme une mesure |
| un chiffre que tu ne peux pas reconstruire | une valeur sortie du chapeau |
| deux étapes enchaînées sans s'arrêter | il a perdu le protocole |

---

## Action 4 — Auditer le moteur

**Conversation NEUVE, différente de l'action 3.** Colle
[prompts/02_moteur_audit.md](prompts/02_moteur_audit.md), donne l'accès au dépôt **et le
compte rendu du constructeur**. Rien d'autre — surtout pas la conversation de construction.

L'auditeur doit te dire ce qu'il va chercher et quels tests hostiles il va écrire **avant**
d'avoir lu le code. C'est l'ordre qui fait toute la valeur de l'audit.

Verdict d'un mot : **ACCEPTÉ**, **ACCEPTÉ SOUS RÉSERVE**, **REJETÉ**.

**Irrecevable si :** aucun test hostile écrit, verdict rendu sans avoir exécuté les tests
lui-même, ou l'auditeur a corrigé au lieu de constater.

**Si REJETÉ :** retour à la conversation de l'action 3 avec la liste numérotée des défauts,
puis retour à la conversation d'audit pour re-vérifier **uniquement** ces défauts.

---

## Action 5 — Reporter au journal

**Pour toi. Cinq minutes.** Une entrée dans
[documentations/06_journal_decisions.md](documentations/06_journal_decisions.md) : hypothèse,
instrument, résultat, audit, décision, impact sur le plan.

Note surtout **ce que l'auditeur a trouvé et que le constructeur avait manqué**. Si l'audit
ne trouve jamais rien sur plusieurs phases, c'est le protocole d'audit qu'il faut durcir —
pas s'en réjouir.

---

## Ensuite

Les actions 3 à 5 se répètent, une paire de conversations par phase. Détail des phases,
hypothèses, seuils chiffrés et critères go/no-go dans
[documentations/05_protocole_experimental.md](documentations/05_protocole_experimental.md).

| Phase | Objet | Exécution machine |
|---|---|---|
| 0 | Moteur conforme, tests en premier | tests < 1 min |
| 1 | Générateur d'instances paramétré | < 1 min |
| 2 | Encodage de l'état + vérification des invariants | quelques minutes |
| 3 | Premier agent entraîné, mesuré contre le greedy | ~1 h |
| 4 | Itérations sur l'algorithme | ~2 h par run |

Les durées sont des **temps d'exécution machine** seulement. Aucune estimation de temps de
développement : elles ne seraient pas fondées.

Les prompts des phases 1 et suivantes seront écrits au fur et à mesure, sur le modèle des
deux premiers — **un prompt de construction, un prompt d'audit**.

---

## Corrections de documentation du 16/08

Relevées pendant l'étape 1, corrigées dans les documents concernés.

| # | Erreur | Où | Correction |
|---|---|---|---|
| 1 | « 17 tests de conformité », situés au « §10 » | [00_index](documentations/00_index.md) §4, [03](documentations/03_specification_moteur.md) §2 et §7, [04](documentations/04_conventions_code.md) §1 | Ils sont **18**, C1 à C18, au **§9** de [01](documentations/01_regles.md). Le §10 est le tableau des arbitrages. |
| 2 | Le meurtre facultatif attribué à « R1 » et au test « C4 » | [03](documentations/03_specification_moteur.md) §4.1 | C'est **R2** et **C5**. R1 est la structure du tour, C4 le reste en pioche. |
| 3 | Reproductibilité exigée des instances historiques, alors qu'elles sont non constructibles sous les planchers du §8 | [03](documentations/03_specification_moteur.md) §3 | Exigence **supprimée** ; trois configurations de référence conformes la remplacent. |
| 4 | Compteur « Espions morts non révélés », fondé sur une Q2 dite non tranchée | [03](documentations/03_specification_moteur.md) §4.2 | **Supprimé** : le §11 de [01](documentations/01_regles.md) tranche que la carte tuée est révélée et la défausse publique. |
| 5 | « Deux cartes chez le même adversaire » présenté comme non tranché | [00_index](documentations/00_index.md) §7, [03](documentations/03_specification_moteur.md) §8 | **Fermé : non**, par le §3.2 et R1. |
| 6 | Plancher noté « familles ≥ 3 » | [01](documentations/01_regles.md) §10bis | C'est **familles > joueurs**, comme au §8. |
| 7 | Tableau de l'invariant I2 cassé par un `|` non échappé | [03](documentations/03_specification_moteur.md) §5 | Écrit `nb_roles`. |

**Tranché le 16/08 après l'étape 1 :** `tours` n'est **pas** un paramètre de `GameConfig`.
Il est dérivé — `nb_cartes // (3 × joueurs)` — et la construction lève si le résultat est
inférieur à 3. Le §8 de [01](documentations/01_regles.md) interdit de toucher à la durée ;
la seule façon de garantir qu'on n'y touche pas est de ne pas exposer le levier.
