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
