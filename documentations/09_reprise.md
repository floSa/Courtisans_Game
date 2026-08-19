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
| **4** | Mesure de la phase 2, constructeur | terminée — elle attend le verdict (voir §5) |
| **5** | Audit de la phase 2 | **clos — ACCEPTÉ SOUS RÉSERVE au tour 2** |

## 4. État du dépôt, vérifié le 19/08/2026

`github.com/floSa/Courtisans_Game`. **Tout est poussé.**

| Branche | Tête | Contenu |
|---|---|---|
| `moteur-conforme` | `ade169e` | branche de travail : moteur, phases 0 et 1 closes, tous les prompts |
| `claude/courtisans-action-labels-leak-582d90` | `ade169e` | branche du pilote, au même commit |
| `claude/courtisans-phase-1-measure-3900b7` | `d7398bd` | mesure de la phase 1 |
| `claude/courtisans-measurement-audit-9bf2f1` | `c64cd9e` | audit de la phase 1 |
| `claude/courtisans-phase-2-baseline-559e17` | `db0816b` | **phase 2, constructeur** |
| `claude/courtisans-phase2-baseline-c5159e` | `8c8c838` | **phase 2, auditeur** — les deux verdicts + 36 contrôles hostiles |

`origin/main` et `origin/cfr-pivot` sont l'ancien projet RL, hors sujet.

**`uv` exige `UV_LINK_MODE=copy` sur ce dépôt** — OneDrive refuse les liens durs (os error 396).

**Le piège de la base.** Les cinq agents lancés jusqu'ici ont **tous** créé leur worktree sur
`main`, où le paquet `courtisans/` n'existe pas. Le contrôle est dans les prompts depuis la
phase 2 : `git merge-base --is-ancestor 68a5c16 HEAD` doit réussir.

## 5. Ce qui est en attente, précisément

### Conversation 4 — terminée, elle attend le verdict

Les deux corrections ont eu le feu vert et sont livrées dans `db0816b`. **Elles ne touchent
que deux documents** : le rapport `mesure/resultats/phase2.md`, `courtisans/` et
`documentations/` sont inchangés depuis `72630a1` — vérifié. L'état que l'auditeur
re-vérifie reste donc valide. C'était :

1. **La clause du −26 %.** Il avait écrit que les passes 3 à 5 s'étalent « de −26 % à +16 % »
   sur les cinq campagnes. Le −26 % venait d'une **sixième** campagne que sa propre phrase
   excluait, et le +16 % était +15,5 % arrondi vers le haut. La phrase juste, qu'il propose :
   *« Les passes 3, 4 et 5 portent un code identique sur la phase de jeu, et les changements
   d'une passe à la suivante s'étalent de −23,3 % à +15,5 % sur les cinq campagnes. »*
2. **L'enseignement (g)**, dont le texte est prêt : *reproduire un nombre ne le valide pas — il
   faut reproduire son unité d'abord, et le nombre ensuite.* Voir §7.

### Conversation 5 — verdict rendu au tour 2 : ACCEPTÉ SOUS RÉSERVE

Quatre défauts levés, les six budgets reconstruits à l'unité près en reconstruisant l'unité
avant la valeur. **965 verts sur 966**, le seul rouge portant la réserve 1.

**Le désaccord sur le 7,33 % est clos, et il lui appartenait.** Les deux nombres étaient justes ;
le sien était mal étiqueté. Il avait mesuré **trois greedys** (6,92 %, IC [5,95 ; 8,00], qui
contient 7,33 %) là où la campagne B du constructeur fait jouer **un greedy contre deux
uniformes** (4,92 %, IC [4,10 ; 5,85], qui contient son 4,23 %). Il avait publié un taux sans
nommer sa population — la faute qu'il reprochait ailleurs.

**Trois réserves ouvertes, toutes documentaires, aucune ne change un chiffre.**

1. Le §4 bis du rapport écrit « **trois** compteurs de B4 » là où `b4` en décide **quatre** sur
   `decision.valeurs`. L'omis est `B4-meurtre-couteux`, **l'un des deux zéros absolus** : un
   lecteur de la phase 3 lirait son zéro comme un résultat sur le greedy alors qu'il est
   tautologique comme les trois autres. Et aucun des quatre n'est nommé. **À corriger : c'est la
   correction du défaut 3 laissée à moitié.**
2. L'inclusion `B1-collectif >= B1-motif` est vérifiée sur les deux anciennes colonnes et pas
   sur la nouvelle — celle qui existe pour `B1-collectif`. L'auditeur l'a vérifiée à la main
   (3 916 >= 2 528, elle tient) mais personne ne la publie.
3. **Trouvée par le pilote dans son harnais.** Son tableau publie `287/4145` et `204/4145` — le
   **même** dénominateur pour deux populations différentes — alors que ses propres nœuds par
   siège-partie valent 0,406 et 0,407, ce qui implique deux dénominateurs distincts, de l'ordre
   de 4 141 et 4 151. Le couple publié n'est donc pas celui qui a servi. À échelle : ±10 sur le
   dénominateur déplace les bornes de 0,01 pt, donc **aucune conclusion ne bouge**. Et son
   `parties` compte des itérations, pas des parties : 3 400 pour trois greedys, 10 200 pour
   l'autre, donc « nœud par partie » est en réalité par **siège-partie mesuré**.

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
