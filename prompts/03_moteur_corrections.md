# Prompt de correction — moteur Courtisans, phase 0, après audit REJETÉ

**À coller dans une conversation NEUVE.** Ne pas réutiliser la conversation d'audit : le
constructeur et l'auditeur ne doivent jamais être la même conversation, y compris au tour
de correction.

Écrit sur le modèle de [01_moteur_construction.md](01_moteur_construction.md) et
[02_moteur_audit.md](02_moteur_audit.md).

---

```
CONTEXTE

Tu reprends le moteur de règles du jeu de cartes Courtisans. La phase 0 a été
construite, puis auditée par une conversation distincte. Le verdict est REJETÉ.

Tu n'es pas l'auditeur. Tu ne verras pas son raisonnement, ni ses tests : tu
reçois sa liste de défauts, numérotée, et rien d'autre. C'est volontaire, dans
les deux sens — son raisonnement t'ancrerait, et ses tests te feraient corriger
pour les faire passer au lieu de corriger le défaut.

Ce projet a un historique précis. Cinq briques d'entraînement ont été validées
sur des instances qui violaient deux règles du jeu — le meurtre de l'Assassin y
était obligatoire alors qu'il est facultatif, et les joueurs n'y jouaient pas le
même nombre de tours. Ces défauts ont survécu trois mois et un rapport de 2 695
lignes, parce qu'aucun test ne vérifiait la conformité aux règles.

Les deux défauts majeurs que tu vas corriger sont de la même famille : une
valeur fausse, bien formée, plausible, qui ne lève aucune erreur.

CE QUI EST DÉJÀ VRAI — À NE PAS CASSER

L'auditeur a remesuré lui-même, sur la branche `moteur-conforme` :

  502 tests verts             uv run pytest -q
  127 / 127 / 127             les trois moteurs (cœur, openspiel, openspiel-hasard)
  143 cas d'invariants        tests/invariants/, 7 configurations
  8 / 8 critères              paragraphe 7 de 03_specification_moteur.md
  592 instructions, 0 manquante   couverture du cœur, 100 %
  10 mutations / 10 détectées     uv run python outillage/mutation.py
  ruff check                  All checks passed

**Toute régression sur l'un de ces chiffres est un échec, quelle que soit la
qualité du correctif.** Tu les rejoues tous à la fin, et tu les cites avec leur
valeur mesurée.

DOCUMENTS À LIRE, DANS CET ORDRE

  1. documentations/01_regles.md              — LES RÈGLES. Fait seule autorité.
  2. documentations/03_specification_moteur.md — architecture, API, invariants,
                                                 critères d'acceptation
  3. documentations/04_conventions_code.md     — les conventions à respecter
  4. documentations/08_modele_compte_rendu.md  — le format imposé de ton compte rendu

LES SIX DÉFAUTS

--- Défaut 1 — MAJEUR — le harnais de validité d'OpenSpiel ne peut pas tourner

`make_py_observer` n'est pas implémenté sur `CourtisansGame`, donc
`pyspiel.random_sim_test` — le contrôle de conformité d'OpenSpiel lui-même —
lève avant de commencer, avec `mask_test=True` comme avec `False`.

Aucun test du dépôt ne l'appelle. Or le docstring de
`tests/adaptateur/test_openspiel.py` annonce vérifier « que le jeu est valide au
sens d'OpenSpiel » : cette validité n'est aujourd'hui établie que par des
contrôles écrits à la main.

MESURÉ par l'auditeur : 12 des 12 jeux Python livrés avec OpenSpiel définissent
cette méthode.

Reproduction :

    import pyspiel
    from courtisans.cards import Role
    from courtisans.config import GameConfig
    from courtisans.openspiel_adapter import CourtisansGame
    jeu = CourtisansGame(config=GameConfig(
        familles=6, roles=tuple(Role), exemplaires=3, joueurs=3))
    pyspiel.random_sim_test(jeu, num_sims=3, serialize=False,
                            verbose=False, mask_test=True)
    # AttributeError: 'CourtisansGame' object has no attribute 'make_py_observer'

--- Défaut 2 — MAJEUR — une observation qui n'appartient à aucun joueur

Sur un **nœud de chance**, `information_state_string()` et
`information_state_tensor()` appelés **sans argument** rendent une observation
bien formée qui n'égale la vue d'**aucun** joueur. Rien ne lève.

Cause : `EtatCourtisans.information_state_string` substitue `current_player()`
quand `player` est omis (openspiel_adapter.py:188-196). Sur un nœud de chance
cela vaut -1, et `vue.mains[-1]` (infoset.py:134) désigne le dernier joueur par
indexation négative, tandis que `_relatif` calcule des positions relatives
depuis -1.

Le chemin est le plus normal qui soit : `new_initial_state()` rend un nœud de
chance.

Sur un **terminal**, le comportement est incohérent selon le nombre de joueurs :

    2 joueurs  ->  IndexError
    3 joueurs  ->  IndexError
    4 joueurs  ->  une chaîne de 891 caractères et un tenseur de 334 valeurs
                   sont rendus, car `vue.mains[-4] == vue.mains[0]`

MESURÉ par l'auditeur, sur un nœud de chance en milieu de partie : les n vues
réelles sont bien distinctes (2/2, 3/3, 4/4 chaînes), et la chaîne rendue sans
argument n'égale aucune d'entre elles.

Reproduction : avancer d'une soixantaine de coups depuis `new_initial_state()`,
s'arrêter sur un nœud de chance, puis comparer `information_state_string()` aux
`information_state_string(j)` pour j dans range(joueurs).

Aucun test ne voit ce défaut, et il y a une raison à trouver et à écrire dans
ton compte rendu : une ligne du dépôt approche ce chemin et le contourne.

--- Défaut 3 — MINEUR — un chiffre non reconstructible

Le critère A8 est documenté « 26 cas de refus », dans
`tests/acceptation/test_criteres.py:14` et `03_specification_moteur.md:450`.

L'auditeur compte 27 cas assertant un refus : 11 configurations non conformes
+ 5 entiers invalides + 1 rôle invalide + 1 `tours` non paramétrable
+ 1 `canonicalisation` non paramétrable + 5 drapeaux de contournement
+ 3 instances historiques. Ou 28 en comptant l'immuabilité.

« 26 » ne correspond à aucun regroupement naturel. Décide ce que compte ce
chiffre, écris sa décomposition, et corrige les deux endroits.

--- Défaut 4 — MINEUR — une assertion tautologique

`tests/adaptateur/test_openspiel.py:120` :

    assert jeu.max_chance_outcomes() == module("rules").nb_types_de_carte(config)

La borne déclarée est comparée à la fonction du code, pas à la formule de la
spécification — `familles × rôles`, écrite en 03_specification_moteur.md:203. Si
`nb_types_de_carte` était faux, les deux membres bougeraient ensemble et le test
passerait.

--- Défaut 5 — MINEUR — une duplication de la source de vérité

`courtisans/openspiel_adapter.py:72-73` écrit `max_num_players=4` et
`min_num_players=2` en dur, alors que `courtisans/config.py:37` porte
`JOUEURS_AUTORISES = (2, 3, 4)`.

Étendre l'un sans l'autre est possible sans qu'aucun test ne le signale. C'est
la classe de faute que 02_audit_conformite.md désigne comme cause racine de N1
et N3.

--- Défaut 6 — MINEUR — une règle vérifiée contre sa propre transcription

`tests/outils.py:132-144` dérive `Instance.tours`, `cartes_jouees` et
`reste_en_pioche` par les mêmes formules que `GameConfig`. Les assertions du
type `config.tours == instance.tours` comparent donc deux transcriptions de la
même formule : elles attrapent une faute de codage, pas une mauvaise lecture de
la règle.

Seule `complet-3j` échappe au reproche : `tests/acceptation/test_criteres.py`
écrit 90 et 10 en dur.

Le tableau du paragraphe 3.4 de 01_regles.md donne les nombres littéraux pour
2, 3 et 4 joueurs — tours, cartes jouées, restant en pioche — ainsi que la
monotonie décroissante des tours. L'auditeur a comblé ce trou de son côté et
n'a trouvé aucune erreur : le moteur est juste. Le défaut est dans la stratégie
de test, pas dans le moteur.

ORDRE DE TRAVAIL — NON NÉGOCIABLE

  Étape 0. Lis les quatre documents et le code concerné. Puis réponds-moi en
           DIX LIGNES MAXIMUM : ce que tu as compris de chaque défaut, lesquels
           te semblent demander un arbitrage, et ce que tu comptes faire.
           AUCUN CODE AVANT MA RÉPONSE.

  Étape 1. Pour les défauts 1 et 2 : écris d'abord un test qui ÉCHOUE et qui
           reproduit le défaut. Montre-moi qu'il est rouge, avec sa sortie.
           Tests d'abord, comme pour toute la phase 0.

  Étape 2. Corrige. Un défaut à la fois. Montre le test devenu vert.

  Étape 3. Défauts 3 à 6 : corrige, en écrivant pour le 4 et le 6 des
           assertions qui portent sur la RÈGLE et non sur le code.

  Étape 4. Rejoue TOUT et cite les sept chiffres de la section « ce qui est
           déjà vrai », avec leur valeur mesurée après correction. La batterie
           de mutation exige un arbre propre : commite avant de la lancer.

  Étape 5. Rends compte au format de 08_modele_compte_rendu.md paragraphe 2.
           La section « Trouvé, non prévu » ne peut pas être vide : la question
           « pourquoi aucun test ne voyait le défaut 2 » a une réponse, et elle
           t'apprendra quelque chose sur la suite.

CE QUE TU NE FAIS PAS

  - Tu ne corriges aucun défaut sans avoir d'abord un test rouge, pour les
    défauts 1 et 2.
  - Tu n'affaiblis, ne supprimes ni ne réécris aucun test existant pour faire
    passer un correctif. Si un test existant devient faux à cause d'un
    correctif, ARRÊTE-TOI et remonte-le : c'est un signe que le correctif est
    mauvais, ou que le test l'était.
  - Tu ne touches pas à la canonicalisation par permutation des familles, ni à
    l'encodage par cible de la phase de ciblage. Ce sont deux reports assumés,
    points ouverts 8 et 9 de 00_index.md, hors du périmètre de ce tour.
  - Tu ne modifies pas les règles du jeu, ni la spécification.
  - Tu ne tranches aucune ambiguïté de spécification. Deux de ces défauts en
    contiennent une — voir ci-dessous.

DEUX ARBITRAGES À ME REMONTER, PAS À TRANCHER

  a) Défaut 1. Le jeu déclare `provides_observation_string=False` et
     `provides_observation_tensor=False`. La spécification ne dit pas ce qu'un
     observateur devrait exposer. Dis-moi les options et ce qu'elles coûtent,
     et attends ma réponse avant d'écrire l'observateur.

  b) Défaut 2. La spécification, paragraphe 4, écrit la signature
     `information_state_string(self, player: int)` sans dire ce qui doit se
     produire pour un identifiant réservé (-1 hasard, -4 terminal). Lever ?
     Refuser de substituer `current_player()` ? Autre ? Dis-moi les options et
     attends.

  Ces deux points sont des défauts de la SPÉCIFICATION, pas du code. Signale-les
  comme tels.

APRÈS TOI

  L'auditeur reprendra sa conversation et re-vérifiera UNIQUEMENT ces six
  défauts. Il ne relira pas le reste. Un correctif qui casse autre chose sera
  donc découvert par les sept chiffres, pas par sa relecture — c'est pourquoi tu
  les rejoues et les cites.

COMMENCE PAR

  Les quatre documents, puis tes dix lignes. Pas de code avant ma réponse.
```

---

## Notes pour l'humain qui lance ce prompt

**Ce qu'il faut donner au constructeur :** l'accès au dépôt, et ce bloc. Rien d'autre.

**Ce qu'il ne faut PAS lui donner :** la conversation d'audit, le fichier `VERDICT.md` en
entier, ni les tests hostiles de l'auditeur. La liste des six défauts ci-dessus est
volontairement autosuffisante : elle contient les reproductions, pas les tests. Donner les
tests de l'auditeur produirait un correctif taillé pour eux.

**Après le compte rendu du constructeur :** revenir à la conversation d'audit avec ce compte
rendu, et lui demander de re-vérifier **uniquement** les six défauts.

**Un constat d'audit hors périmètre, à porter au journal et non à ce prompt.** L'auditeur a
mesuré que la traduction de l'espace d'actions sous permutation des familles est **totale** :
sur 3 permutations × 12 pioches, toute action de la partie d'origine admet une action
équivalente dans la partie permutée, et les gains finaux sont identiques. Le point ouvert 8
est donc moins coûteux qu'annoncé. À traiter comme une étape à part entière, plus tard,
spécification d'abord — pas dans ce tour de correction.
