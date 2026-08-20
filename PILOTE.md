# PILOTE — ce que tu as à faire

**Le seul document qui te parle. Quelle action, quel prompt, quelle conversation, et à quoi reconnaître que c'est fait.**

Corpus de référence, pour toi et pour les agents :
[documentations/00_index.md](documentations/00_index.md).

Mis à jour le 20/08/2026, après la clôture de la phase 2 et le bouchage des trous du protocole.

---

## Où on en est

| | |
|---|---|
| Étape en cours | **Phase 2 CLOSE le 19/08, verdict ACCEPTÉ au troisième tour d'audit.** Trois tours, **75 contrôles hostiles**, cinq défauts trouvés dont un **bloquant**, **977 tests verts, 0 rouge** — recomptés par le pilote le 20/08, c'est bien 977. Les quatre lignes de base du jeu sont établies et citables : avantage de siège **33,50 %** en part fractionnée pour le siège le plus favorisé, σ(gain) = **0,6652**, greedy contre deux aléatoires à **86,52 %** et **+0,7978** de gain moyen, et dix-sept compteurs de comportement |
| Prochaine action | **Écrire les prompts de la phase 3**, construction et audit, puis les lancer dans deux conversations neuves et distinctes. Le premier agent entraîné, mesuré contre le greedy |
| Ce que la phase 3 doit corriger en entrant | **Quatre mineurs de la phase 2** restés hors du périmètre re-vérifié, plus une réserve de la phase 1. Le plus sérieux : **`vue_du_joueur` ne valide pas son argument** et rend une vue n'appartenant à aucun siège — réouverture du défaut 2 de la phase 0 sur une entrée neuve, et **tout agent en dépend**. Les autres : le rapport généré est en **cp1252** quand les quatre autres documents sont en UTF-8 ; deux des douze directions annoncées sont comptées comme tenues alors que la pré-inscription les déclare **nulles par construction** ; une cellule « voir `B4-departage` » figure dans une table dont le texte dit qu'elle ne se lit qu'en juxtaposant deux nombres |
| Réserve de la phase 1, mesurée le 20/08 | Elle disait que **rien ne relie** `mesure/instance.py` à la description indépendante de `tests/outils.py`, si bien qu'une dérive resterait muette. **Vérifié en injectant la dérive** — `familles=4` passé à `5` : **21 tests tombent**, donc elle n'est pas muette. Mais **aucun des 21 ne dit que l'instance a dérivé** : ils échouent tous sur des nombres calculés à la main dans `tests/mesure/test_parties_construites.py`, `tests/mesure/test_comportements.py` et `tests/audit/test_echelle_de_l_invisible.py`, dont le message est « son chiffre doit se reproduire ». Le garde-fou existe **par accident, pas par intention**, et `tests/outils.py::ENTRAINEMENT_3J` — la description censée servir d'oracle — n'est pas ce qui l'attrape. À fermer par **un** test qui le dit |
| Le protocole | **Bouché le 20/08.** [05_protocole_experimental.md](documentations/05_protocole_experimental.md) porte un **§0 normatif** — le journal y renvoyait depuis le début, il n'existait pas —, un **erratum sur la phase 1** qui définit « retournement », « distribution non dégénérée » et « refuser de tuer est possible », un **erratum sur la phase 2** qui nomme les cinq défauts de son propre texte, et les **seuils des phases 3, 4 et 5 réécrits** |
| Bloquant | **Rien.** Deux reports assumés, écrits dans le README : canonicalisation et encodage par cible. |

### Les trois décisions de la phase 2 que la phase 3 doit porter

- **Aucune durée ne se cite sur un seul chronométrage.** Sur cette machine, cinq passes du même
  code donnent un rapport max/min de **2,93 à 3,00** par campagne, **de façon non monotone**. Le
  temps mural mesure l'état de la machine, pas le coût du code. Trois passes minimum, avec
  l'étendue.
- **`agents/greedy.py` est la ligne de base de toutes les phases suivantes et ne porte aucune
  mutation.** `outillage/mutation.py` ne cible que `courtisans/` — vérifié.
- **`B4-tout-dos` et `B5-renfort` ne sont pas comparables entre compositions.** Leurs taux publiés,
  **3,89 %** et **20,41 %**, bougeront sous trois agents entraînés pour une raison qui n'est pas
  l'habileté de l'agent.

### Le seuil de la phase 3 a été réécrit, et il ne faut pas coller l'ancien

L'ancien seuil était **« > 55 % contre le greedy sur 1 000 parties appariées »**, avec une bande
45–55 % et un plancher à 45 %. **Ces trois nombres sont des intuitions de jeu à deux joueurs.** À
trois joueurs la part de victoire fractionnée vaut **33,33 %** au neutre : un agent à 45 % est très
au-dessus du hasard, pas en dessous. Le nouveau seuil juge le **gain moyen**, dont la valeur nulle
est exactement 0,0000, et demande que la **borne basse de son IC 99 % soit strictement positive**,
sur une composition nommée — **un agent contre deux greedys**, sièges permutés.

**Et son budget ne s'emprunte pas.** Le seul écart de gain détectable mesuré, **+0,1013 à
1 000 parties appariées**, l'a été **sous jeu uniformément aléatoire**. La phase 3 mesure σ(gain) et
ρ sur sa propre composition avant de lancer.

### Ce que l'audit croisé a rapporté, trois phases de suite

**En phase 0**, il a rejeté une première fois — six défauts — puis, après correction, en a trouvé
deux de plus, dont un qui bloquait `deep_cfr` et le calcul d'exploitabilité. Neuf défauts au total,
tous corrigés, chacun tenu par un test **et** par une mutation.

**En phase 1**, il a trouvé une faute d'un genre nouveau, sur des **chiffres** et non sur du code :
un nombre juste, reproductible au bit près, dont la phrase ne décrivait pas le calcul. Le rapport
annonçait « 0 sur 1 000 retournements invisibles des trois joueurs » ; le calcul agrégeait les
quatre familles avant de comparer les vues, et le cas survient en réalité dans **une partie sur
treize à dix-huit**. Le propre test du constructeur le démontrait déjà, dans le même livrable.

**En phase 2**, la même faute est sortie **cinq fois dans une seule phase** — un chiffre exact sur
une population que sa phrase ne nomme pas — chez le constructeur, chez l'auditeur, chez le pilote,
et jusque dans l'entrée de journal qui nommait la faute quatre fois. Le défaut le plus instructif,
un facteur trois indu dans six budgets, avait **survécu à deux vérifications réussies** : la formule
de contrôle recevait le même dénominateur erroné que le générateur.

> **Les leçons transférables sont désormais normatives**, au §0.2 de
> [05_protocole_experimental.md](documentations/05_protocole_experimental.md), et non plus seulement
> racontées au journal. Les trois qui comptent le plus pour la phase 3 : **l'unité se reconstruit
> avant la valeur, et séparément** ; **un compte n'est pas une liste de noms** ; et **on relit ce qui
> a été écrit en dernier, pas ce qui a été mesuré en premier** — la correction est le lieu du défaut
> suivant.

Le dépôt est poussé sur la branche `main` (nommée `moteur-conforme` jusqu'au 19/08/2026) de
[floSa/Courtisans_Game](https://github.com/floSa/Courtisans_Game), avec un historique
indépendant de `old_version` et de `cfr-pivot` : c'est un moteur neuf, pas une correction de
l'ancien.

**Les actions 1 à 5 ci-dessous sont celles de la phase 0.** Elles sont conservées parce que leur
forme se répète à chaque phase — un prompt de construction, un prompt d'audit, une entrée de
journal écrite par l'auditeur — et parce que les tableaux « renvoie-le au travail si » de
l'action 3 et « irrecevable si » de l'action 4 servent encore tels quels.
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

**C'est l'agent qui l'écrit, pas toi.** Tu le relis et tu valides. L'auditeur rédige
l'entrée à la fin de son audit, puisque c'est lui qui détient les chiffres remesurés et
la liste de ce que le constructeur avait manqué.

Une entrée dans
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

*Cette table nommait la phase 1 « générateur d'instances paramétré » et la phase 2 « encodage de
l'état », ce qui ne correspondait à aucune des deux. Corrigée le 20/08 sur le §3 du protocole,
seule source.*

| Phase | Objet | Budget machine | État |
|---|---|---|---|
| 0 | Moteur conforme, tests en premier | < 1 min | **close** |
| 1 | L'instance d'entraînement, `entrainement-3j` | quelques min | **close** |
| 2 | Mesurer le jeu avant d'y jouer | ~1 h | **close** |
| 3 | Premier agent entraîné, mesuré contre le greedy | plafond 2 h par run | **ouverte** |
| 4 | Itérations sur l'algorithme, une variable à la fois | plafond 2 h par run | — |
| 5 | Le jeu complet, 90 cartes | à établir | — |
| 6 | 2 et 4 joueurs | à établir | — |

Ces durées sont des **plafonds de budget machine**, pas des mesures : **aucune durée mesurée ne se
publie sur un seul chronométrage**. Aucune estimation de temps de développement n'est donnée :
elle ne serait pas fondée.

Les prompts sont écrits phase par phase, sur le modèle des deux premiers — **un prompt de
construction, un prompt d'audit**. Ceux des phases 0, 1 et 2 sont dans `prompts/` et **ne sont pas
réécrits** : ce sont des documents historiques, et les corriger falsifierait le compte rendu de ce
qui a été fait. Ils parlent encore de la branche `moteur-conforme`, qui est l'actuelle `main` sous
son ancien nom.

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
| 7 | Tableau de l'invariant I2 cassé par un `\|` non échappé | [03](documentations/03_specification_moteur.md) §5 | Écrit `nb_roles`. |

**Tranché le 16/08 après l'étape 1 :** `tours` n'est **pas** un paramètre de `GameConfig`.
Il est dérivé — `nb_cartes // (3 × joueurs)` — et la construction lève si le résultat est
inférieur à 3. Le §8 de [01](documentations/01_regles.md) interdit de toucher à la durée ;
la seule façon de garantir qu'on n'y touche pas est de ne pas exposer le levier.
