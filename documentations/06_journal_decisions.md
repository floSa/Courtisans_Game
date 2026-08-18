# Journal des décisions

**Une entrée par tour de boucle d'investigation. Antichronologique — le plus récent en haut.**

Format et règles : [05_protocole_experimental.md](05_protocole_experimental.md) §0.

```
[date] Phase X.Y — <titre>
Hypothèse   : énoncé falsifiable, écrit AVANT l'expérience
Instrument  : métrique, seuil chiffré, durée à laquelle elle devient décisive
Résultat    : ce qu'on a mesuré
Audit       : le chiffre mesure-t-il ce qu'on croit ? sur quel support ? comparable ?
Décision    : go / pivot / abandon — avec justification
Impact plan : phases invalidées ou modifiées
```

---

## [2026-08-18] Phase 1 — L'instance d'entraînement, et audit croisé de sa mesure

**Hypothèse.** *Écrite et commitée avant toute mesure, `mesure/hypothese_et_instrument.md`.*
L'instance `entrainement-3j` — 4 familles, 5 rôles, 2 exemplaires, 3 joueurs, 40 cartes,
4 tours — conserve la substance du jeu : sous jeu uniformément aléatoire, sur 1 000 parties,
les trois joueurs jouent le même nombre de tours (H1), la distribution des scores n'est pas
dégénérée (H2), et au moins un retournement survient dans au moins 33,3 % des parties (H3).

**Instrument.** 1 000 parties, donne `Engine.reset(seed)` seeds 0–999, politique uniforme sur
`legal_actions()` avec `Random(1_000_000 + seed)`. Seuil H3 : `p ≥ 1/3`, intervalle exact de
Clopper-Pearson à 99 %, bande d'indécision [0,295 ; 0,372] fixée d'avance. La mesure tranche
dès N = 30 si `p̂ ≥ 0,80`. Le protocole ne définissant pas « retournement », quatre définitions
ont été pré-inscrites ; le go/no-go porte sur **R2, perte d'acquis** — `∃t : s_{t−1} ≠
Indifférente et s_t ≠ s_{t−1}` — parce que l'encadré du §2.2 des règles tranche déjà que le
seuil qui compte est l'Indifférence et non l'Obscurité.

**Résultat.** Hypothèse **vérifiée sur les trois énoncés.** H1 : 1 000/1 000, vecteur de poses
`(4, 4, 4)`. H2 : 10/10 critères, écart-type 4,4 par siège, 25 à 26 valeurs de score
distinctes, mode à 9 %, trois ex æquo dans 1,5 % des parties. H3 : **96,00 % (960/1 000),
IC99 [94,12 % ; 97,42 %]**, soit 2,88 fois le seuil — borne basse à 94,12 %. 2,075 familles
retournées par partie sur 4. Une partie se joue en 1,6 ms, 19,2 décisions. 82,53 % des
7 206 nœuds de ciblage offrent au moins une cible, donc un refus qui est un choix et non un
constat.

**Audit.** Deux tours, par une conversation distincte qui a réimplémenté le calcul de statut,
le compteur de retournements, l'intervalle de confiance et la campagne depuis le texte des
règles, sans réutiliser une ligne du constructeur, et écrit seize contrôles hostiles.
Code de l'audit : `audit/` et `tests/audit/`, verdict détaillé dans
`audit/verdict_phase_1.md`.

*Tour 1 — livrable `3f5b75d`, verdict **REJETÉ**.*

Ce que l'audit a **confirmé** : les trois critères de go/no-go, remesurés indépendamment —
`(4, 4, 4)` dans 5 000 parties sur 5 000, retournements à 94,0–95,5 % selon le bloc de seeds,
étendue de 1,5 point ; l'accord des deux calculs de statut sur **11 000 comparaisons,
0 désaccord** ; l'exactitude de l'intervalle sur **820 couples (k, n, α), écart maximum
2,5 × 10⁻¹²**, par quatre calculs indépendants ; l'estimation « ~8 cartes par domaine » qui
fondait le seuil D2, mesurée à **6,99** ; et la **convergence de trois lectures indépendantes
du §2.2** sur la définition R2, l'auditeur ayant écrit la sienne avant de lire celle du
constructeur. Le constructeur ne surinterprète pas non plus son chiffre : sa pré-inscription
écrit, avant la mesure, que l'aléatoire n'établit pas qu'un agent saura planifier un
retournement.

Ce que l'audit a **trouvé, et que le constructeur avait manqué** : l'affirmation « **0 sur
1 000 retournements R2 invisibles des trois joueurs** » était **fausse**. Le calcul agrégeait
les quatre familles en un booléen de partie avant de comparer les vues, puis les trois sièges
par un `any` ; il comptait « une partie où la vérité a un R2 et où aucun siège n'en a sur
aucune famille », conjonction quasi impossible entre deux grandeurs valant 96 % et ~93 %. Le
même invisible, mêmes seeds, sous le décalage de politique du constructeur, **grain tour** :

| Niveau d'agrégation | seeds 0–999 | seeds 1000–1999 |
|---|---|---|
| partie, familles confondues — *le chiffre publié* | 0 | 0 |
| famille — invisibles / familles en R2 | 5 / 2 075 = **0,241 %** | 11 / 2 026 = **0,543 %** |
| famille — invisibles / emplacements famille × partie | 5 / 4 000 = 0,125 % | 11 / 4 000 = 0,275 % |
| événement — invisibles / pertes d'acquis | 79 / 2 665 = **2,96 %** | 56 / 2 531 = 2,21 % |
| événement — parties touchées | 74 / 1 000 = **7,40 %** | 56 / 1 000 = 5,60 % |

**Le dénominateur retenu au niveau famille est 2 075, les familles qui ont effectivement perdu
un acquis** : la question posée est « parmi les retournements qui ont eu lieu, lesquels
n'étaient visibles de personne ». Rapporter les mêmes 5 aux 4 000 emplacements famille × partie
répond à une autre question — quelle part du plateau porte un retournement invisible — et
divise le taux par deux. Les deux lectures sont justes ; les deux sont écrites ci-dessus
précisément parce qu'un taux sans son dénominateur n'est pas auditable.

Cinq témoins nommés au premier bloc : seeds 308, 453, 496, 539, 933. Le cas se construit à la
main en quatre poses — deux Espions de même famille posés par deux joueurs différents — et
touche **une partie sur treize à dix-huit** (74/1 000 = 1 sur 13,5 ; 56/1 000 = 1 sur 17,9 ;
au grain fin, 75 et 57 pour 1 000, soit 1 sur 13,3 et 1 sur 17,5). **Son propre test le
démontrait déjà** : `tests/mesure/test_parties_construites.py` assertait exactement ce cas, sa
docstring écrivant « un retournement que personne ne pouvait planifier ». Le test et le rapport
se contredisaient dans le même livrable.

Cinq défauts mineurs par ailleurs : une assertion tautologique, l'instance définie trois fois,
quatre littéraux en dur dans les décompositions du rapport, un seuil D2 franchi dès 12 parties
donc sans pouvoir discriminant, et un intervalle qui ne validait pas `n > 0`.

*Tour 2 — correction `d7398bd`, verdict **ACCEPTÉ SOUS RÉSERVE**.*

Les six défauts sont corrigés. Le comptage de l'invisible ne compare plus que des grandeurs
non agrégées et publie les deux niveaux avec leurs dénominateurs ; **l'implémentation
indépendante de l'auditeur rend exactement le même nombre au même grain** — 81 événements
invisibles sur 2 735 dans 75 parties au grain fin, contre 79 sur 2 665 dans 74 parties au
grain tour, celui que le rapport publie. Deux défauts sont corrigés mieux que demandé : le
pouvoir discriminant est mesuré pour les **quatre** critères, et non le seul D2 relevé par
l'audit — D1 et D3 sont satisfaits dès 3 parties, D4 dès 1 —, et le §5.3 de la pré-inscription
porte un erratum qui **conserve** la phrase fausse plutôt que de l'effacer. L'auditeur a
re-vérifié la correction en y ré-introduisant la faute exacte : un test rouge, sur une partie
construite à la main. Les trois chiffres du go/no-go sont inchangés. 648 tests verts chez le
constructeur, les 16 contrôles hostiles de l'auditeur verts contre le code corrigé.

Deux réserves : rien ne relie la définition unique de l'instance dans `mesure/instance.py` à
la description indépendante de `tests/outils.py` — l'indépendance de l'oracle est justifiée,
l'absence de garde-fou contre la dérive ne l'est pas ; et la section 6 du rapport ne répète pas
le grain sur ses deux blocs de comptage, si bien qu'un lecteur reconstruisant 2 078 familles au
grain fin au lieu de 2 075 au grain tour ne peut pas savoir laquelle des deux lectures est la
sienne.

**Décision.** **Go.** La phase 1 est close. `entrainement-3j` est l'instance des phases 2 et 3.

**Impact plan.** La phase 2 s'ouvre sans modification. Une mesure s'ajoute à sa liste : la
fréquence des retournements qu'**aucun** siège ne voit est un **plafond de ce que B1 peut
mesurer**. Une ligne de base d'agent qui ne planifie jamais un retournement doit être lue en
retranchant les ~7 % de parties portant une perte d'acquis qu'aucune politique, aussi bonne
soit-elle, ne pouvait voir venir.

**Défauts du protocole, à corriger dans [05_protocole_experimental.md](05_protocole_experimental.md).**
Trois termes du go/no-go de la phase 1 ne sont définis nulle part, et les trois sont chiffrés :
« retournement », « distribution non dégénérée », et « situations où refuser de tuer est
possible » — dont la lecture littérale est **vide**, refuser étant toujours légal (§4.1,
arbitrage R2), si bien que la fréquence vaudrait 100 % par construction. Les définitions
proposées par le constructeur ont tenu deux tours d'audit et doivent remonter dans le document.
Le §3 présente en outre « 20 cartes ou 40 cartes » comme un arbitrage à trancher en phase 1 :
il n'en est pas un, la variante à 20 cartes étant refusée à la construction par le plancher
`tours ≥ 3` du §8 des règles.

**Trois enseignements de méthode.**

- **Un taux dont le sujet grammatical n'est pas l'unité comptée doit publier son
  dénominateur.** L'erreur de ce tour n'est ni un calcul faux ni un DÉDUIT présenté comme un
  MESURÉ : c'est un chiffre juste, reproductible au bit près, dont la phrase parlait de
  retournements quand le calcul parlait de parties. Aucun contrôle existant ne cherchait cette
  faute-là.
- **Un zéro absolu doit être confronté à un cas construit à la main avant d'être écrit.**
  Celui-ci était contredit par un test du même livrable.
- **Un chiffre doit porter son échantillon — grain et dénominateur compris.** L'auditeur a
  commis deux fois la faute qu'il reprochait : d'abord en juxtaposant deux comptes justes,
  70 et 81 événements sur les mêmes seeds, sans dire que le décalage de politique différait —
  cause racine, une valeur en dur invisible dans les chiffres qu'elle produisait, devenue un
  paramètre nommé ; ensuite en écrivant « 5 familles sur 4 000 » sans dire que « 5 sur 2 075 »
  existait et disait autre chose. Les deux corrections sont dans cette entrée.

---

## [2026-08-17] Phase 0 — Audit croisé du moteur conforme

**Hypothèse.** Le moteur construit par la conversation de l'action 3 implémente les règles de
`01_regles.md`, et ses 502 tests verts l'établissent.

**Instrument.** Protocole d'audit croisé, `07_protocole_audit_croise.md`. Contrôles A1 à A7
par une conversation distincte, qui rejoue tous les chiffres elle-même et écrit ses propres
tests hostiles contre le **texte des règles**, sans appeler une seule fonction du moteur pour
calculer un attendu. Seuil de rejet fixé d'avance : un critère non satisfait, un test hostile
rouge, ou une affirmation fausse dans le compte rendu.

**Résultat.** Hypothèse **partiellement rejetée**. Aucun défaut de conformité aux règles —
61 cas hostiles, dont une construction de fuite d'information à pioches jumelles et une
traduction complète de l'espace d'actions sous permutation des familles, n'en ont produit
aucun. Mais **neuf défauts** dans l'adaptateur, la stratégie de test et la documentation, en
trois tours :

| Tour | Défauts | Les deux qui comptent |
|---|---|---|
| Audit initial | 6 (2 majeurs, 4 mineurs) | `make_py_observer` absent → le harnais de validité d'OpenSpiel ne pouvait pas tourner ; l'observation d'un identifiant réservé rendait une vue **n'appartenant à aucun joueur**, sans lever |
| Correction 1 | +1 trouvé par le correctif | libellés d'action dupliqués — trouvé par `random_sim_test` en une exécution, que 502 tests maison n'avaient pas vu |
| Re-vérification | +2 | régression sur le motif d'appel d'OpenSpiel (34 sites, dont `deep_cfr` et `best_response`) ; le jeu ne survivait pas à un aller-retour par sa propre chaîne de paramètres |

État final, **remesuré par l'auditeur** sur `b90f714` : 576 tests verts, 127/127/127 sur les
trois moteurs, 143 invariants, 8/8 critères, **618 instructions et 0 manquante**, **18
mutations sur 18 détectées**, `ruff` propre.

**La réserve unique de cet audit est levée le 17/08.** Elle portait sur
`_action_to_string`, qui nommait la famille et le rôle de la carte ciblée par un Assassin —
`tuer la cible 1 : f0-ESPION` — y compris lorsque cette carte était un Espion posé face
cachée par un adversaire, dont le joueur qui choisit ignore l'identité. Rien n'en fuitait :
ces libellés n'étaient lus que par du débogage. Mais **rien ne l'aurait signalé non plus**,
l'invariant I7 ne surveillant qu'`information_state_string`. Un dos est désormais dit dos,
situé dans sa zone et numéroté par son rang parmi les cartes de même apparence encore en jeu
— le rang étant ce qui empêche de rouvrir le défaut 7 en anonymisant. Mesures sur `7eabe3b` :
**596 tests verts, 127/127/127, 143 invariants, 8/8 critères, 643 instructions et 0
manquante, 19 mutations sur 19 détectées**, `ruff` propre. **Le nouveau verdict appartient à
l'auditeur** : ce paragraphe constate la correction, il ne la valide pas.

**Audit du résultat.** Deux mesures méritent d'être distinguées de tout le reste :

1. **Deux des neuf défauts vivaient à 100 % de couverture d'instructions.** Le défaut 2 était
   une branche exécutée à chaque appel mais jamais avec l'argument omis ; la régression du
   tour 2 était un refus exécuté mais jamais dans le cas où il devait rendre une valeur. La
   couverture d'instructions **ne peut pas** les voir. La couverture de **branches** est le
   seul changement d'instrument qui les aurait signalés.
2. **La preuve que les phases 2 et 3 sont débloquées a été faite, pas déduite.** L'auditeur a
   fait tourner de vrais consommateurs OpenSpiel de bout en bout sur `rapide-2j` :
   `mcts.MCTSBot` — partie entière, 38 coups, gains [1.0, −1.0] — et
   `rl_environment.Environment` — 14 pas, rewards [1.0, −1.0].

**Décision.** **Go.** Verdict **ACCEPTÉ SOUS RÉSERVE**. La phase 0 est close.

~~Une réserve reste ouverte et demande un arbitrage : `action_to_string` nomme la famille et
le rôle d'un **Espion caché**.~~ **Arbitrée et corrigée le 17/08, avant la phase 1** plutôt
qu'avant la phase 3 : l'invariant I7 ne couvrant qu'`information_state_string`, aucun test
n'aurait signalé le jour où une interface ou une trace d'entraînement se serait mise à lire
ces libellés. Détail au paragraphe « la réserve unique est levée » ci-dessus. **I7 n'a pas été
étendu à `action_to_string`** — ce serait modifier la spécification, et c'est un arbitrage
distinct, resté ouvert.

**Impact plan.** Aucun. La phase 1 s'ouvre sans modification. Trois enseignements de méthode
sont à reporter dans les phases suivantes :

- **La section « Incertain » d'un compte rendu désigne le défaut suivant.** Le constructeur
  avait écrit « SUPPOSÉ que la sérialisation passerait » ; c'était faux, et c'est devenu le
  défaut 9. Un `SUPPOSÉ` dans un compte rendu est un test qui manque.
- **Un arbitrage mal formulé produit une régression.** La consigne disait « la substitution
  disparaît » là où elle aurait dû dire « la substitution est validée » — d'où le défaut R1.
  Un arbitrage doit énoncer ce qui doit **continuer de marcher**, pas seulement ce qui doit
  échouer.
- **Le harnais standard de l'écosystème trouve ce que la suite maison ne cherche pas.**
  Débloquer `random_sim_test` a produit un défaut réel à la première exécution.

---

## [2026-08-15] Pré-phase 0 — Conformité des instances aux règles

**Hypothèse.** Les instances CFR implémentent les règles de Courtisans.

**Instrument.** Lecture croisée instances / `regles.md` / `app/jeu.py`, puis 20 000 playouts
pour quantifier l'impact des écarts trouvés.

**Résultat.**

- **N1** — le meurtre de l'Assassin est obligatoire alors qu'il est facultatif :
  **20.0 %** des résolutions où refuser serait strictement meilleur, perte moyenne
  **1.34 point**, **38.1 %** d'auto-mutilations forcées.
- **N3** — tours inégaux : P0 joue 2 tours (6 cartes), P1 un seul (3 cartes). Idem en 2.1d.
- **N2** — `app/jeu.py::is_done` teste la fin de partie joueur par joueur : à 4 joueurs, les
  deux premiers de l'ordre jouent un tour de plus.

**Audit.** L'ordre de pose intra-tour, suspecté, a été vérifié **sans effet** (0 cas sur 24) :
ce n'était pas un écart. Les mesures d'impact sont myopes (score si la partie s'arrêtait là),
donc indicatives et non exactes — mais l'ordre de grandeur suffit à conclure.

**Décision.** Hypothèse **rejetée**. L'oracle à 0.001783 est l'équilibre exact d'un jeu qui
n'est pas Courtisans.

**Impact plan.** La phase 0 devient bloquante pour tout le reste. Les verdicts des briques
2.1c et 2.1e sont suspendus jusqu'à mesure de la fréquence du passe à l'équilibre (P2.5).

---

## [2026-08-15] Pré-phase 0 — Que mesure le plafond à 0.190 ?

**Hypothèse.** Le chiffre 0.190 mesure la qualité de Deep CFR sur l'instance 2.1e.

**Instrument.** Lecture de `deep_cfr_mini.py`, puis simulation de la collecte de
strategy-memories (sémantique OpenSpiel `_traverse_game_tree`) au budget exact du run
(20 itérations × 2000 traversées).

**Résultat.** `DCFR_MEASURE_NET` vaut 0 par défaut : la métrique est
`buffer_exploitability`, qui **retourne la politique uniforme** pour tout info-set absent du
buffer. Couverture au budget du run : **295 176 / 455 092 = 64.9 %**. Au moins **35 %** des
info-sets jouent au hasard dans la stratégie notée 0.190.

**Audit.** La simulation utilise une politique uniforme, qui **maximise** l'exploration : le
chiffre réel est plus bas, pas plus haut. C'est donc une borne supérieure, à confirmer par
lecture du log réel (P3.0, dix secondes). Aux briques 1 à 2.1d la couverture était totale
(236/236, 12 484/12 484) — la métrique y était honnête, et c'est ce qui rend le 0.190 non
comparable.

**Décision.** Hypothèse **rejetée**. Le 0.190 n'est pas comparable aux chiffres des briques
précédentes.

**Impact plan.** La conclusion « mur de variance à 455k info-sets → ESCHER/DREAM » du
`rapport_expert.md` §34 est **suspendue**. Le diagnostic est rouvert en phase 3, avant toute
phase 4.

---

## [2026-08-15] Pré-phase 0 — L'encodage perd-il de l'information ?

**Hypothèse.** La représentation d'un info-set n'est pas injective : deux info-sets
distincts au sens des règles produisent le même tenseur, ce qui plafonnerait
l'exploitabilité quel que soit l'algorithme.

**Instrument.** Traversée exhaustive des **8 250 001** états de l'instance combo. Trois
contrôles : collisions tenseur → string, non-déterminisme string → tenseur, et cohérence des
actions légales au sein d'un info-set.

**Résultat.**

```
info-sets (strings distinctes) : 475 000   (P0 455 092 + P1 19 908)
tenseurs distincts             : 475 000
2 info-sets → 1 tenseur                       : 0
1 info-set → 2 tenseurs                       : 0
actions légales incohérentes dans un info-set : 0
```

**Audit.** Le harnais a d'abord été validé sur l'instance 2.1c (123 921 états), dont le
résultat correspond à la documentation existante, avant d'être appliqué à 2.1e. Le troisième
contrôle est nouveau — `check_combo.py` ne le faisait pas — et c'était le risque réel, la
string ne codant que la zone-clé de l'assassin en phase de ciblage.

**Décision.** Hypothèse **rejetée**. L'encodage n'est pas la cause du plafond.

**Impact plan.** Réoriente l'investigation vers la métrique et la conformité aux règles.
Les tests d'injectivité deviennent C13 et C14 de la suite de conformité, à exécuter
automatiquement.
