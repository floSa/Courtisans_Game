# Prompt de correction — tour 2, après re-vérification

**À coller dans la conversation de correction du tour 1** (elle a le contexte des six
défauts). Si elle est perdue, une conversation neuve fait l'affaire : le bloc est
autosuffisant.

---

```
RE-VÉRIFICATION DU TOUR 1 — RÉSULTAT

L'auditeur a re-vérifié tes correctifs. MESURÉ par lui, sur ton commit a54146b :

  567 passed                    couverture 614 instructions, 0 manquante, 100 %
  127 / 127 / 127               les trois moteurs
  143 invariants                28 cas de refus (A8)
  15 mutations, 15 détectées    ruff : All checks passed
  61 / 61                       ses propres tests hostiles, dont celui qui était rouge

**Les six défauts sont corrigés, et le septième aussi.** Rien à reprendre dessus.

Deux défauts NOUVEAUX, tous deux majeurs. Le premier est une régression que ton
correctif a introduite ; le second préexistait et c'est TOI qui l'avais signalé
comme incertain — tu avais raison, et c'est faux.

--- Défaut 8 — MAJEUR — RÉGRESSION — le motif d'appel d'OpenSpiel est cassé

En supprimant l'argument par défaut de `information_state_string` et
`information_state_tensor`, tu as fermé un chemin qui MARCHAIT : l'appel sans
argument sur un nœud de **décision**, où `current_player()` est un joueur réel.

MESURÉ, sur un nœud de décision, `current_player() == 0` :

    information_state_string()                 -> TypeError: missing 1 required
                                                  positional argument: 'player'
    information_state_string(current_player())  -> OK (631 caractères)

C'est le motif qu'emploie OpenSpiel lui-même. `open_spiel/python/policy.py:309`
écrit littéralement `return state.information_state_string()`.

MESURÉ : **34 appels sans argument** dans la bibliothèque, dont
`python/algorithms/best_response.py:80` (l'exploitabilité, phase 2),
`python/jax/deep_cfr.py:572` et `:640` (phase 3), `python/policy.py:244` et
`:309`, `python/algorithms/cfr_br.py:99`, `python/algorithms/policy_utils.py:53`.

L'arbitrage (b) disait « lever pour un identifiant réservé ». Il ne disait pas
de supprimer le défaut. La forme correcte garde `player=None` valant
`current_player()`, PUIS valide : ça lève sur un nœud de chance et au terminal —
le défaut 2 reste corrigé — et ça marche sur un nœud de décision.

Écris d'abord le test rouge : sur un nœud de décision, l'appel sans argument doit
rendre exactement la vue de `current_player()`. Et garde tes tests du défaut 2 :
ils doivent rester verts.

--- Défaut 9 — MAJEUR — le jeu ne survit pas à un aller-retour par sa chaîne

Tu avais écrit au paragraphe 5 de ton compte rendu : « la sérialisation n'est pas
établie […] SUPPOSÉ qu'elle passerait ». MESURÉ : elle ne passe pas, pour deux
causes distinctes.

**9a. La configuration est perdue.** Un jeu construit avec `config=` passe
`params or {}` à `super().__init__`, donc :

    jeu = CourtisansGame(config=GameConfig(familles=4, exemplaires=2, joueurs=3))
    str(jeu)  ->  'courtisans()'

La chaîne annonce le jeu par défaut — 6 familles, 3 exemplaires. `load_game(str(jeu))`
rend donc **un autre jeu**, sans rien lever. C'est exactement la famille du défaut 2 :
une valeur fausse, bien formée, silencieuse.

**9b. `roles` est incompatible avec la grammaire d'OpenSpiel**, qui coupe les
paramètres aux virgules :

    pyspiel.load_game("courtisans(familles=4,exemplaires=2,joueurs=3,"
                      "roles=ASSASSIN,GARDE,NOBLE,ESPION,NEUTRE)")
    -> SpielError: Unknown parameter 'ESPION,NEUTRE)'

Conséquences MESURÉES :

    random_sim_test(serialize=True)  ->  SpielError: game.ToString() ==
        game_and_state.first->ToString()
        'courtisans()' vs 'courtisans(exemplaires=3,familles=6,joueurs=3,roles=...)'
    policy.TabularPolicy(jeu)         ->  SpielError: Unknown parameter 'ESPION,NEUTRE)'

Pourquoi aucun test ne le voyait : `test_le_jeu_est_enregistre_et_chargeable_par_son_nom`
charge `"courtisans(familles=4,exemplaires=2,joueurs=3)"` — sans `roles`. Le test
passe littéralement à côté, comme `__str__` passait à côté du défaut 2.

Le choix de l'encodage de `roles` est un ARBITRAGE : sépararateur non virgule,
masque de bits, un booléen par rôle… Ne tranche pas, propose et attends.

ORDRE DE TRAVAIL

  Étape 0. Dis-moi en cinq lignes ce que tu comptes faire pour 8, et les options
           pour 9b. AUCUN CODE AVANT MA RÉPONSE pour 9b ; tu peux enchaîner
           directement sur 8, qui n'a pas d'ambiguïté.
  Étape 1. Test rouge d'abord, pour 8 et pour 9.
  Étape 2. Corrige. Une mutation par défaut corrigé, comme au tour 1.
  Étape 3. Rejoue tout, et cite les sept chiffres — ils sont en tête de ce message.
           `random_sim_test` doit désormais tourner avec `serialize=True`.
  Étape 4. Compte rendu au format du paragraphe 2 de 08_modele_compte_rendu.md.

CE QUE TU NE FAIS PAS

  - Tu ne casses aucun des correctifs du tour 1. Les tests du défaut 2 restent verts.
  - Tu n'affaiblis aucun test existant pour faire passer un correctif.
  - Tu ne tranches pas l'encodage de `roles`.
  - Hors périmètre, toujours : canonicalisation, encodage par cible.

NOTE

  `uv` échoue sur ce dépôt sans `UV_LINK_MODE=copy` — OneDrive interdit les liens
  durs (os error 396).
```

---

## Notes pour l'humain

**Ce qui a changé dans le dossier.** L'auditeur a rejoué les sept chiffres, ses 61 cas
hostiles et la batterie de mutation sur le commit `a54146b`. Tout est vert. Les deux
nouveaux défauts viennent de sondes qu'il n'avait pas faites au premier tour :
`serialize=True`, et le motif d'appel sans argument sur un nœud de décision.

**Le défaut 8 est imputable à l'arbitrage (b), pas au constructeur.** La consigne disait
« la substitution disparaît » ; elle aurait dû dire « la substitution est validée ».

**Le défaut 9 était annoncé.** Le paragraphe 5 du compte rendu du tour 1 le portait
comme SUPPOSÉ. C'est le format de compte rendu qui a fonctionné : la section
« Incertain » a désigné le défaut suivant avant qu'on le cherche.
