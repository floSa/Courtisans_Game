# Reprise — à lire en premier sur une machine ou un compte neuf

Ce document existe pour une raison précise : le 19/08/2026, le travail a changé de machine et
de compte. Tout le reste du projet est dans le dépôt et se relit. **Ce fichier contient
uniquement ce qui n'existait nulle part ailleurs** — dans la mémoire d'un assistant, dans des
conversations, dans la tête de quelqu'un.

Si tu reprends le pilotage : lis ce document, puis
[00_index.md](00_index.md), puis [06_journal_decisions.md](06_journal_decisions.md).

---

## 1. Comment travailler avec l'humain

**C'est le point le plus important de ce document, et il n'est écrit dans aucun autre fichier.**

Il s'est fâché deux fois pour la même raison : le manque de clarté.

- **Une idée par phrase, des mots parlants, pas de jargon.** « Rien n'attend de toi côté
  code » ne veut rien dire. « Le code est poussé sur ton GitHub » veut dire quelque chose.
- **Quand il demande une réponse courte, la donner.** Deux lignes, pas un bilan.
- **Numéroter toujours la conversation destinataire** d'un bloc à coller. Il travaille avec
  plusieurs conversations en parallèle et s'y perd sinon.
- **Ne jamais lui demander d'assembler des instructions.** Quand il faut coller quelque
  chose, lui envoyer **un seul** fichier, prêt à Ctrl+A / Ctrl+C.
- **S'il faut ajouter une phrase à un document, la modifier soi-même.** Ne jamais lui dire
  « ajoute cette phrase » — c'est le travail du pilote, pas le sien.
- **Ne pas lui donner un prompt qu'il n'a pas demandé**, et ne pas anticiper l'étape
  suivante avant que la réponse de l'agent soit arrivée.
- **Aucun trailer d'attribution dans les commits ni les PR.** Pas de `Co-Authored-By`, pas de
  mention de l'assistant. Quatre commits de juin en portent un ; ils sont sur
  `origin/cfr-pivot` uniquement, hors lignée.
- **Une preuve différée revient nommée, pas agrégée en un compte.** Si on annonce « tel test
  tombera », il faut dire *lequel*, pas « trois tests sont tombés ».

## 2. Le rôle du pilote

Le pilote **n'écrit pas le code des phases**. Il :

1. recalcule les chiffres des agents avec sa propre implémentation avant de les accepter, et
   dit quand ça tombe juste aussi clairement que quand ça ne tombe pas ;
2. tranche les arbitrages que les agents lui remontent ;
3. écrit les prompts de phase ;
4. garde le dépôt fusionné et poussé ;
5. rend à l'humain des blocs prêts à coller, numérotés par conversation destinataire.

**Deux règles de vérification apprises à leurs frais.**

- Après tout changement dans `courtisans/`, revérifier que les **19 motifs** de
  `outillage/mutation.py` s'appliquent encore. Une mutation qui cesse de s'appliquer ne
  mesure plus rien, et rien ne le signale.
- **Vérifier qu'une branche d'agent est poussée avant de la croire sauvée.** C'est arrivé
  deux fois : en phase 1 le travail de l'audit était non commité, et en phase 2 la branche
  d'audit `claude/courtisans-phase2-baseline-c5159e` n'avait **aucun upstream** alors qu'elle
  portait le verdict entier et 36 contrôles hostiles. Les agents créent leur worktree sur une
  branche locale et ne poussent pas spontanément.

**Un agent peut avoir raison contre le pilote, et c'est arrivé plusieurs fois.** Voir §7.

## 3. La numérotation des conversations

| N° | Rôle | État |
|---|---|---|
| **1** | Pilote | active — c'est celle qu'on reprend |
| **2** | Mesure de la phase 1 | close (elle a produit les 96 % de retournement) |
| **3** | Audit de la phase 1 | clos (il a écrit REJETÉ) |
| **4** | Mesure de la phase 2, constructeur | **terminée** |
| **5** | Audit de la phase 2 | **clos — ACCEPTÉ au tour 3** |

## 4. État du dépôt, vérifié le 19/08/2026

`github.com/floSa/Courtisans_Game`. **Tout est poussé.**

| Branche | Contenu |
|---|---|
| **`main`** | **la branche de travail** — tout le projet Courtisans, phases 0 à 2 closes |
| `old_version` | l'ancien projet RL, 38 commits, gardé pour mémoire |
| `cfr-pivot` | l'ancien travail CFR, 53 commits que `old_version` n'a pas — c'est la source du plafond à 0,190 et de l'oracle combo que le journal cite |

**Le 19/08/2026, `moteur-conforme` a pris la place de `main`.** L'ancien `main` est devenu
`old_version`, et les cinq branches d'agents des phases 1 et 2 ont été supprimées après
fusion — leurs commits sont tous dans `main`, rien n'est perdu.

Les prompts déjà utilisés (`prompts/03`, `prompts/08`, `prompts/09`) parlent encore de
`moteur-conforme`. **C'est volontaire** : ce sont des documents historiques, et les réécrire
falsifierait le compte rendu de ce qui a été fait. C'est la même branche, sous son ancien nom.

`old_version` et `cfr-pivot` sont l'ancien projet RL, hors sujet du jeu Courtisans.

**`uv` exige `UV_LINK_MODE=copy` sur ce dépôt** — OneDrive refuse les liens durs (os error 396).

**Le piège de la base.** Les cinq agents lancés jusqu'ici ont **tous** créé leur worktree sur
l'ancien `main`, où le paquet `courtisans/` n'existait pas. Le contrôle est dans les prompts depuis la
phase 2 : `git merge-base --is-ancestor 68a5c16 HEAD` doit réussir.

## 5. La phase 2 est close, et ce qui reste ouvert

**VERDICT FINAL : ACCEPTÉ**, au troisième tour d'audit. L'entrée est au journal, à la date du
19/08/2026 — **lis-la, tout y est**. Les deux branches sont fusionnées dans `main`.

Trois tours, 75 contrôles hostiles, cinq défauts trouvés dont un bloquant, 977 tests verts.

**La même faute est sortie cinq fois dans cette seule phase** : un chiffre exact sur une
population que sa phrase ne nomme pas. Chez le constructeur, chez l'auditeur, chez le pilote, et
la cinquième fois dans l'entrée de journal qui nommait la faute quatre fois. D'où la règle :
**relire ce qui a été écrit en dernier, pas ce qui a été mesuré en premier.**

**Quatre mineurs du tour 1 restent ouverts**, hors du périmètre re-vérifié, et ils sont à
traiter au début de la phase 3 :

1. le rapport généré est en cp1252 quand les quatre autres documents sont en UTF-8 ;
2. **`vue_du_joueur`, rendue publique par cette phase, ne valide pas son argument** et rend une
   vue n'appartenant à aucun siège — c'est la réouverture du défaut 2 de la phase 0 sur une
   entrée neuve, et c'est le plus sérieux des quatre puisque tout agent en dépend ;
3. deux des douze directions annoncées sont comptées comme tenues alors que la pré-inscription
   les déclare nulles **par construction** ;
4. une cellule « voir `B4-departage` » dans une table dont le texte dit qu'elle ne se lit qu'en
   juxtaposant deux nombres.

**Cinq trous du protocole expérimental** sont nommés dans l'entrée de journal et **ne sont pas
corrigés** dans [05_protocole_experimental.md](05_protocole_experimental.md). C'est un travail de
pilote, pas d'agent.

### Phase 3 — pas de prompt

C'est le prochain travail de fond du pilote. Trois choses doivent y figurer, décidées en
phase 2 :

- **Aucune durée citée sur un seul chronométrage.** Sur cette machine, cinq passes du même
  code donnent un rapport max/min de **2,93 à 3,00** par campagne, de façon **non monotone**.
  Le temps mural mesure l'état de la machine, pas le coût du code. Toute durée se cite sur au
  moins trois passes, avec son étendue.
- **`agents/greedy.py` devient la ligne de base de toutes les phases suivantes et ne porte
  aucune mutation.** `outillage/mutation.py` ne cible que `courtisans/` — vérifié. À inscrire
  au programme de la phase 3.
- **`B4-tout-dos` et `B5-renfort` ne sont pas comparables entre compositions.** Leurs taux
  publiés (3,89 % et 20,41 %) bougeront sous trois agents entraînés pour une raison qui n'est
  pas l'habileté de l'agent. La phase 3 les mesure sur une population de même composition que
  la sienne, ou ne les compare pas.

### Machine

La phase 2 n'utilise aucun GPU. La phase 3 doit tourner sur le PC fixe — Ryzen 9600X,
RTX 4060, 64 Go de RAM.

## 6. Les sept points que l'audit de la phase 2 re-vérifie

Le verdict était **REJETÉ** : 1 bloquant, 2 majeurs, 4 mineurs. Le constructeur a corrigé.
La liste, telle qu'elle a été transmise à la conversation 5 :

1. **Défaut 1, bloquant.** Les cinq lignes `-par-partie` du §6 publiaient un écart entre deux
   grains — greedy sur 1 siège moins hasard sur 3 sièges agrégés. Sur `B1-motif` le signe
   s'inversait : −23,97 pt au lieu de +11,82 pt. Le grain porte désormais le **nombre de
   sièges** — indispensable, les deux colonnes portaient auparavant un libellé identique, donc
   une parade comparant les libellés n'aurait rien levé. `ecart_de_taux` et `cumuler` **lèvent**
   quand les grains diffèrent. Les cellules portent « non comparable : grains différents ».
2. **Défaut 2, majeur.** La clause « Indifférente ou en Obscurité » de B1 — le seuil du §2.2 —
   n'était tenue par aucun test : la faute réinjectée donnait 913 verts, zéro rouge. La
   régression aurait valu 9,27 points quand le détectable de la phase 3 est de 7,64.
3. **Défaut 3, majeur.** Le greedy ne fait pas ce que dit sa spécification : la pose est
   évaluée Assassins résolus conjointement, le ciblage se décide un nœud à la fois sans les
   Assassins en attente. Corrigé **par la description, pas par le code** — une ligne de base
   n'a pas besoin d'être forte, elle a besoin d'être exactement décrite. Le biais est
   déterminé pour M3 (plancher) et **ne l'est pas pour M4**, parce que les compteurs B4 sont
   jugés par l'évaluation myope elle-même : le zéro de `B4-contre-nature` est tautologique.
4. **Défaut 4, mineur.** « Aveugle par le bas » est devenu un critère **calculé** : un compteur
   dont l'écart détectable dépasse son propre taux. Deux lignes le portent, `B7-gaspillage`
   (0,30 % contre 0,15 %) et `B7-gaspillage-vraie` (0,35 % contre 0,2050 %).
5. **La garde de campagne, scindée.** Elle refusait trois greedys en disant « la mesure n'a
   plus d'objet » : vrai de M3, faux de M4. Elle confondait une mesure avec une phase.
6. **La troisième population, trois greedys.** Autorisée par le pilote, auditée par personne,
   à traiter comme une première livraison. Raison : la phase 3 fera jouer les trois sièges par
   des agents entraînés, donc une ligne de base collective mesurée sur un agent contre deux
   hasards n'est pas la bonne. **Le critère de périmètre se décide sur le texte : la définition
   nomme-t-elle un autre joueur ?** `B1-collectif` oui, `B4-tout-dos` et `B5-renfort` non.
7. **Défaut 5, trouvé par le pilote après le verdict.** Le générateur divisait par un facteur
   trois indu : un compteur `-par-partie` rend **un** booléen par partie quel que soit le
   nombre de sièges, parce que l'agrégation est dans son numérateur. **Six budgets étaient
   faux** ; les justes sont 745, 1 295, 299, 239, 10 400, 280. Il y avait **trois** sites de
   calcul du budget, il n'y en a plus qu'un.

**`B1-strict-par-partie` reste**, malgré ses 10 400 parties. Retirer une ligne parce que sa
valeur s'est révélée décevante, c'est décider un périmètre **après** avoir vu les valeurs —
la liberté que la pré-inscription existe pour supprimer. Son inutilité est l'avertissement.

## 7. Les erreurs du pilote, pour qu'elles ne se refassent pas

Elles sont ici parce qu'un pilote qui ne les connaît pas les répétera.

1. **Une formule de taille d'échantillon anti-conservatrice**, aussi fausse que celle de
   l'agent. L'arbitrage binomial exact a donné 1531 et 11629.
2. **Une estimation de 100 000 parties pour B7** contre les 320 163 de l'agent. L'agent avait
   raison.
3. **Un prompt d'audit qui demandait un 0 % sur un dénominateur vide** : « une instance sans
   Assassin, la fréquence de B4 doit valoir exactement 0 ». Faux — sans Assassin il n'y a
   aucun nœud de ciblage, donc **0/0 n'est pas 0 %**. Le contrôle utile est l'inverse :
   vérifier que le dénominateur vaut 0 et que le code **refuse** de publier un taux.
4. **Un « ralentissement uniforme » endossé** comme signature d'une cause machine. La cause
   machine tenait ; le mot « ralentissement » non. Cinq passes montrent une **étendue** non
   monotone, pas une dérive.
5. **Le `2 234` de `B1-collectif` validé alors qu'il était trois fois trop grand.** La formule
   du pilote le reproduisait — parce qu'elle avait reçu le dénominateur par partie du
   générateur, 1,0, au lieu de le dériver du grain, 3,0. C'est le constructeur qui l'a trouvé.

**L'enseignement (g), qui vient de la cinquième.** *Reproduire un nombre ne le valide pas : il
faut reproduire son unité d'abord, et le nombre ensuite.* Deux implémentations qui partagent la
même hypothèse fausse concordent parfaitement. **Le contrôle A7 — « les chiffres se
reconstruisent » — ne remplace pas le contrôle 1 — « le calcul est celui que la phrase
décrit ».** Vrai entre constructeur et auditeur, et vrai de la phase 3 qui citera ces chiffres
sans les recalculer.

## 8. Les trous de protocole trouvés en phase 2

Trois ont été mis dans le prompt par le pilote plutôt que laissés à découvrir : le greedy
n'existait pas dans le dépôt, B1–B7 n'étaient pas mesurables en l'état, le seuil de 38 % de M1
était à 9,9 erreurs-type de l'attendu donc ne discriminait rien.

L'agent en a trouvé deux de plus : « parties appariées » est vide à politiques identiques, et
« l'appariement divise par cinq à dix » implique un rho entre 0,8 et 0,9 sans mesure d'appui.

**C'est la bonne façon de faire** : nommer le trou dans le prompt coûte une phrase, le laisser
découvrir coûte un tour d'audit.
