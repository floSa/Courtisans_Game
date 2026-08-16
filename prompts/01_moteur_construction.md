# Prompt de construction — moteur Courtisans

**À coller dans une conversation NEUVE, sur le dépôt vierge.** Le bloc ci-dessous est le
prompt lui-même — copie tout ce qui est entre les triples accents.

---

```
Tu vas écrire le moteur de règles d'un jeu de cartes, Courtisans. Rien d'autre :
pas d'IA, pas d'interface, pas d'entraînement. Juste les règles, et les tests qui
prouvent qu'elles sont respectées.

CE DÉPÔT EST VIDE, ET C'EST VOLONTAIRE

Il ne contient que documentations/ et prompts/. Aucun code.

Une tentative précédente existe ailleurs. Elle a validé cinq briques d'entraînement
sur des implémentations qui ne respectaient pas les règles : le meurtre de l'Assassin
y était obligatoire alors qu'il est facultatif, et les joueurs n'y jouaient pas le
même nombre de tours. Ces défauts ont survécu trois mois et un rapport de 2 695
lignes, parce qu'aucun test ne vérifiait la conformité aux règles.

Tu ne dois PAS chercher cet ancien code. Il n'est pas là exprès.

LIS CES CINQ DOCUMENTS, DANS CET ORDRE, AVANT D'ÉCRIRE UNE LIGNE

  1. documentations/00_index.md               — où en est le projet
  2. documentations/01_regles.md              — LES RÈGLES, seule autorité
  3. documentations/03_specification_moteur.md — architecture, API, invariants,
                                                 critères d'acceptation, et §4.2
                                                 l'encodage de l'état
  4. documentations/04_conventions_code.md    — comment coder, et pourquoi
  5. documentations/08_modele_compte_rendu.md — le format imposé de tes rapports

Si deux documents se contredisent : ARRÊTE-TOI et demande.
Si une règle est ambiguë : ARRÊTE-TOI et demande. Ne tranche JAMAIS seul une règle.

TROIS POINTS DE RÈGLE SUR LESQUELS LES IMPLÉMENTATIONS SE TROMPENT

  1. L'influence au banquet se compte en VALEUR, pas en nombre de cartes.
     Un Noble pèse 2, tous les autres rôles pèsent 1 — au banquet comme en domaine.
     Deux Nobles en Estime contre deux cartes standard en Disgrâce donne d = +2,
     donc Lumière, alors qu'il y a autant de cartes de chaque côté.

  2. Le meurtre de l'Assassin est FACULTATIF. « Ne pas tuer » est une action légale
     à part entière, même quand des cibles valides existent. Ce n'est pas un cas
     dégénéré.

  3. Tous les joueurs jouent exactement le même nombre de tours. La partie s'arrête
     à la fin du dernier tour de table complet : avant d'entamer un tour de table,
     si len(pioche) < 3 × nb_joueurs, c'est fini. Tester la fin joueur par joueur
     est non conforme.

ORDRE DE TRAVAIL — NON NÉGOCIABLE

  Étape 1. Écris les tests de conformité du §9 de 01_regles.md.
           Ils doivent TOUS ÉCHOUER : aucune ligne de moteur n'existe encore.
           Chaque test cite la section de règle qu'il vérifie.
           Un test s'écrit en lisant les RÈGLES, jamais en lisant du code.

  Étape 2. Écris les tests des invariants du §5 de 03_specification_moteur.md.
           Tous rouges également.
           Traite I7 — aucune fuite d'information cachée — avec un test hostile :
           deux états qui ne diffèrent QUE par une information cachée doivent
           produire des info-set strings identiques.

  Étape 3. config.py — GameConfig, avec validation à la construction.
           Doit LEVER si : les tours sont inégaux, s'il y a moins de 3 tours par
           joueur, ou si le nombre de familles n'est pas strictement supérieur au
           nombre de joueurs.

  Étape 4. cards.py et rules.py — fonctions pures, stdlib seule.

  Étape 5. engine.py — la machine à états.
           Séquence d'un tour : UNE action de pose atomique qui place les 3 cartes,
           PUIS résolution des Assassins dans l'ordre banquet, domaine propre,
           domaine adverse.

  Étape 6. infoset.py — vue joueur, string et tenseur, selon le §4.2 du document 03.
           Cette section a été réécrite après un audit qui y a trouvé quatre défauts
           bloquants. Lis-la deux fois. Les cinq règles non négociables et le tri
           canonique de la main ne sont pas des suggestions.

  Étape 7. Adaptateur OpenSpiel. Les MÊMES tests de conformité doivent passer à
           travers l'adaptateur.

  Étape 8. Vérifie les critères d'acceptation du §7 de 03_specification_moteur.md,
           un par un, avec la preuve de chacun.

Tu t'ARRÊTES et tu rends compte À CHAQUE ÉTAPE. Tu n'enchaînes jamais deux étapes.

RÈGLES DE CONDUITE

  - Tests avant code. Toujours.
  - Une seule source de vérité : jamais deux fichiers implémentant la même règle.
    Une variante de jeu = une GameConfig, jamais un nouveau fichier. C'est la cause
    racine des défauts précédents : quatre fichiers copiés à la main, un bug propagé
    dans les quatre, invisible pendant trois mois.
  - Aucune valeur en dur : ni 6 familles, ni 5 rôles, ni 3 exemplaires, ni 90 cartes,
    ni le nombre d'actions. Tout vient de GameConfig.
  - Aucune logique d'IA dans le moteur : pas d'heuristique, pas d'évaluation de
    position. Dans la tentative précédente, une heuristique de ciblage vivait dans
    le fichier de règles ; résultat, aucune politique n'a jamais utilisé le refus de
    tuer et la règle a été perdue.
  - Le cœur n'importe ni OpenSpiel, ni PyTorch, ni NumPy.
  - Français pour les noms de domaine et les docstrings.
  - Déterminisme : reset(seed) reproductible, aucun random global.

COMMENT RENDRE COMPTE — format imposé, à chaque étape

  1. ce qui a été fait, en une phrase
  2. les tests qui passent, AVEC LEUR NOMBRE, et la commande pour les rejouer
  3. ce que tu as trouvé et qui n'était pas prévu, Y COMPRIS tes propres erreurs
  4. ce qui reste incertain
  5. chaque chiffre, décomposé pour que je puisse le reconstruire moi-même

  Préfixe CHAQUE affirmation factuelle par son niveau de preuve :
    MESURÉ  — j'ai exécuté et lu le résultat
    DÉDUIT  — j'ai lu le code et raisonné, je n'ai pas exécuté
    SUPPOSÉ — je n'ai ni mesuré ni lu

  Ne présente jamais un DÉDUIT comme un MESURÉ. C'est l'erreur qui a coûté le plus
  cher à ce projet, et elle s'est produite trois fois — chaque fois avec une
  justification cohérente qui la rendait crédible à la lecture.

  « Les tests passent » sans nombre est irrecevable.
  Une section « incertain » vide est suspecte.

CE QUI T'INTERDIT DE CONTINUER

  - un test de conformité échoue → corriger avant toute nouvelle fonctionnalité
  - une règle est ambiguë → demander, ne pas trancher
  - un invariant ne peut pas être garanti → s'arrêter et le signaler
  - l'envie de dupliquer un fichier apparaît → la configuration est trop pauvre,
    l'étendre
  - un chiffre que le lecteur ne peut pas reconstruire → le décomposer ou le retirer

CE QUI SE PASSE APRÈS

  Ton travail sera audité par une AUTRE conversation, qui ne verra pas ton
  raisonnement — seulement le code et tes comptes rendus. Elle écrira ses propres
  tests hostiles avant de lire ton code, rejouera tes tests elle-même, et vérifiera
  chaque affirmation de tes rapports. Écris en conséquence.

COMMENCE PAR

  Lire les cinq documents, puis me dire en DIX LIGNES MAXIMUM : ce que tu as compris
  de la mission, ce qui te semble ambigu, et ce que tu comptes faire à l'étape 1.
  N'écris AUCUN code avant ma réponse.
```

---

## Notes pour l'humain qui lance ce prompt

**Ce que tu dois recevoir en premier :** dix lignes, aucun code. Si l'agent commence à
coder, arrête-le immédiatement — il a déjà perdu le protocole.

**À chaque étape**, vérifie les cinq points du compte rendu. Les signaux d'alarme sont dans
[../PILOTE.md](../PILOTE.md), action 3.

**Après l'étape 8 :** passer à `02_moteur_audit.md`, dans une **conversation différente**.
Ne donne à l'auditeur que le dépôt et les comptes rendus — jamais cette conversation-ci.
