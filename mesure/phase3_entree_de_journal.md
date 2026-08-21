# Phase 3 — proposition d'entrée de journal

*Au format du §4 de [08_modele_compte_rendu.md](../documentations/08_modele_compte_rendu.md) et
du §0.1 de [05_protocole_experimental.md](../documentations/05_protocole_experimental.md).
Proposée par le constructeur ; la décision n'est pas la sienne.*

---

## [2026-08-21] Phase 3 — Le premier agent entraîné

**Hypothèse.** *Écrite et commitée avant tout entraînement,
`mesure/phase3_hypothese_et_instrument.md`.* Un agent entraîné en self-play avec un pool
d'adversaires figés, sur `entrainement-3j`, obtient contre **deux greedys**, sièges permutés, un
**gain moyen strictement positif, borne basse de son IC 99 % bootstrap par donne comprise**.

**Instrument.** PPO à masque d'actions, réseau unique partagé par les trois sièges, tête de
valeur, `γ = 1`, `λ = 1`. Ni le greedy ni l'aléatoire n'entrent dans le pool d'entraînement.
Juge : gain moyen, niveau nul **exactement 0,0000**. Budget **dimensionné sur la composition**,
jamais emprunté : `σ = 0,6494` et `ρ = −0,1400` mesurés sur « un greedy contre deux greedys »,
2 000 donnes, seeds 20000–21999 — d'où **2 000 donnes × 3 sièges = 6 000 parties**, écart
détectable **+0,0243**. Bootstrap **par donne**, 10 000 rééchantillons. Entraînement : plafond
2 h, checkpoint tous les quarts d'heure, seeds `100000+`, disjointes de toutes les plages de
mesure. Rapport régénérable par `uv run python -m mesure.phase3_mesure`.

**Résultat. L'agent apprend nettement, et il est battu par le greedy. Les deux sont établis.**

- **Le juge — H est INFIRMÉE, et de façon établie, pas par manque de puissance.** Gain moyen
  **−0,1643**, IC 99 % **[−0,1824 ; −0,1462]** sur 6 000 parties : la borne **haute** est
  négative. Part de victoire fractionnée **22,38 %** contre **33,3333 %** au neutre. L'effet
  vaut **sept fois** l'écart détectable remesuré (+0,0237). Ce n'est pas « non conclu au
  budget » : c'est « battu », au sens de la table go/no-go.
- **L'instrument est calibré sur les seeds exactes du verdict**, et pas seulement sur celles de
  la pré-inscription : le greedy mis à la place de l'agent, seeds 60000–61999, rend
  **+0,0062**, IC 99 % **[−0,0124 ; +0,0255]**, qui contient 0.
- **L'agent apprend, sans ambiguïté.** Part fractionnée contre deux aléatoires, agrégée sur les
  trois sièges comme le 86,52 % l'est : **57,33 → 59,52 → 61,77 → 63,22 → 65,06 → 67,56 → 69,27
  → 70,13 %** sur les huit checkpoints, **croissance monotone sans exception**, et il progressait
  encore au dernier. 1 486 336 parties d'entraînement.
- **Le garde-fou n'est pas franchi — et la raison que le protocole lui prête est FAUSSE ici.**
  Le protocole écrit « on arrête : **l'agent n'apprend pas**, et rallonger ne dira rien de
  plus ». La prémisse est vérifiable et la mesure la contredit. Ce n'est pas un agent qui
  n'apprend pas, c'est un agent qui **n'a pas fini d'apprendre** en 2 h.
- **`σ` a bougé de −12,1 %** — 0,5710 mesuré contre 0,6494 sous l'hypothèse nulle, au-delà de la
  marge de 10 % que la pré-inscription s'était donnée. Elle l'annonçait comme SUPPOSÉ ; c'est
  désormais MESURÉ, et le rapport le dit.
- **`ρ` reste négatif** — −0,0565 contre −0,1400 sous l'hypothèse nulle. La permutation des
  sièges **réduit** la variance dans les deux cas, effet de plan 0,8817 par bootstrap et 0,8870
  par analyse de variance, deux routes indépendantes.
- **Comportements, comparés à une ligne de base RÉGÉNÉRÉE** — trois greedys à **un seul siège
  compté**, mêmes seeds, même composition, même décalage `6000000` ; seuls les sièges comptés
  changent. **`B1-motif` 42,48 % contre 45,83 %** : l'agent manifeste le motif de retournement
  **moins** que le greedy. **`B4-brut` 31,93 % contre 15,93 %** : il refuse de tuer deux fois
  plus souvent. **`B4-contre-nature` 35,87 % contre 0,00 %**.

**Audit.** Auto-audit **écrit et commité avant que l'agent ne soit mesuré** —
`mesure/phase3_audit.py`, dix contrôles portant sur des unités, des dénominateurs et des
populations, jamais sur des valeurs. **Les dix sont concluants.** Chacun est vérifié capable
d'échouer par `tests/mesure/test_phase3_audit.py`, qui les casse un par un.

**Il a trouvé un vrai défaut avant la mesure** : les compositions du pool tombaient **dans la
plage d'entraînement** — départ à 30 000 avec des décalages de +100 000 et +200 000, quand
l'entraînement occupe 100 000 à ~1 586 000. L'agent aurait été jugé sur des donnes qu'il avait
vues. Les six plages sont désormais toutes sous 100 000.

**Cinq autres défauts trouvés par mes propres tests, tous avant d'avoir un chiffre :** un repli
silencieux vers `actions_legales[0]` dans la boucle d'entraînement ; un aléa partagé en
lock-step qui rendait une partie irreproductible à l'unité ; une garde de dénominateur qui
**doublait** celle de `phase2.observations_par_partie` ; une comparaison de demi-largeur d'IC
entre deux budgets différents ; et une règle de garde-fou qui tuait un agent qui apprend.

**Décision. PROPOSÉE : pivot, pas abandon** — la décision n'appartient pas au constructeur.

L'hypothèse est infirmée : l'agent ne bat pas le greedy. Mais **ce que le résultat écarte est
le budget, pas la méthode** : la courbe est monotone sur huit points et n'a pas plateauté.
Trois lectures coexistent et la phase ne les sépare pas — budget insuffisant, entropie effondrée
trop tôt (0,47 dès le premier checkpoint, 0,34 à la fin), ou convention de self-play. **Rien ici
ne tranche entre elles**, et prétendre le contraire serait la faute du projet.

**Impact plan.**

1. **Le garde-fou de la phase 3 doit être relu au protocole.** Il conflate « n'atteint pas le
   niveau du greedy » et « n'apprend pas », et cette phase fournit le contre-exemple. C'est le
   **troisième** défaut de ce même garde-fou : le protocole le déclenchait quand le run était
   fini, ma correction le déclenchait trop tôt, et sa prémisse est fausse.
2. **La phase 4 hérite d'une question ordonnée, pas d'un catalogue.** Le levier 1 — budget — est
   celui que la courbe désigne, et c'est le seul que le résultat appuie.
3. **`B4-contre-nature` et `B4-meurtre-couteux` cessent d'être tautologiques**, comme la phase 2
   l'annonçait, mais **leur lecture reste ambiguë** : contredire l'évaluation myope du greedy
   n'établit ni planification ni erreur.
4. **La ligne de base « trois greedys à un siège compté » existe désormais** et est régénérable.
   Toute phase mesurant **un** agent contre deux adversaires doit la citer plutôt que la colonne
   à trois sièges de la phase 2.
