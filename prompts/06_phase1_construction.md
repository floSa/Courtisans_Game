# Prompt de construction — phase 1, l'instance d'entraînement

**À coller dans une conversation NEUVE.** Écrit sur le modèle de
[01_moteur_construction.md](01_moteur_construction.md).

L'audit de cette phase se fait dans une **autre** conversation, avec
[07_phase1_audit.md](07_phase1_audit.md).

---

```
CONTEXTE

Tu ouvres la phase 1 du projet Courtisans. La phase 0 est close : le moteur de
règles est écrit, audité par une conversation indépendante, et accepté —
576 tests verts, 8 critères d'acceptation, 18 mutations sur 18 détectées,
couverture 618 instructions et 0 manquante. Tu n'as pas à le corriger.

Ce projet a un historique précis. Cinq briques d'entraînement ont été validées sur
des instances qui violaient deux règles du jeu, et le plafond de performance qui a
piloté trois mois de travail était mesuré par une métrique qui jouait au hasard sur
un tiers du jeu. Personne ne l'a vu, parce que personne ne demandait à un chiffre
ce qu'il mesurait.

Ta phase produit des chiffres. C'est exactement là que ça se rejoue.

CE QU'EST LA PHASE 1

L'objectif est écrit au paragraphe 3 de documentations/05_protocole_experimental.md :
une configuration réduite qui garde la substance du jeu, et sur laquelle une partie
complète se joue vite.

**L'instance est déjà déterminée, et ce n'est pas ton travail de la choisir.** Le
protocole hésitait entre 20 cartes / 2 tours et 40 cartes / 4 tours ; la question
est fermée depuis que le plancher `tours >= 3` du paragraphe 8 des règles est
appliqué à la construction — `GameConfig` REFUSE la variante à 20 cartes. Reste :

    entrainement-3j : familles=4, les 5 rôles, exemplaires=2, joueurs=3
                      4 x 5 x 2 = 40 cartes ; 40 // 9 = 4 tours par joueur
                      36 cartes jouées ; 4 jamais piochées

**Ton travail est donc de MESURER cette instance et de dire si elle tient.** Pas de
la construire, pas de la modifier.

LE GO/NO-GO, TEL QU'IL EST ÉCRIT

Le protocole exige, sur 1 000 parties aléatoires :

  1. les trois joueurs jouent le même nombre de tours ;
  2. la distribution des scores finaux n'est pas dégénérée ;
  3. **au moins un retournement de famille survient dans une partie sur trois.**

Et le rapport attendu : durée, distribution des scores finaux, fréquence des
retournements, fréquence des situations où refuser de tuer est possible.

CE QUE CE GO/NO-GO NE DIT PAS, ET QUE TU DOIS TRANCHER OU REMONTER

  a) **« Retournement » n'est défini nulle part.** Le paragraphe 2.2 des règles
     décrit le mécanisme — une famille change de statut au banquet — mais aucun
     document n'en donne une définition mesurable. Une famille qui oscille
     Lumière → Indifférente → Lumière compte-t-elle ? Faut-il un changement de
     signe strict, Lumière ↔ Obscurité ? Le statut final doit-il différer du
     premier statut atteint, ou compte-t-on chaque transition ?
     **Propose une définition, écris-la, et dis ce que les autres définitions
     auraient donné comme chiffre.** Un seuil « 1 partie sur 3 » n'a aucun sens
     sans la définition qui va avec.

  b) **« Distribution non dégénérée » n'a pas de seuil.** Propose-en un, chiffré,
     et justifie-le.

  c) **La mesure porte sur des parties ALÉATOIRES.** Un retournement produit par
     un jeu aléatoire ne prouve pas qu'un agent pourra en planifier un ; il prouve
     seulement que l'instance le rend possible. Dis explicitement ce que ta mesure
     établit et ce qu'elle n'établit pas.

ORDRE DE TRAVAIL — NON NÉGOCIABLE

C'est la boucle en huit étapes du paragraphe 2 de 05_protocole_experimental.md.

  Étape 0. Lis les documents ci-dessous. Puis réponds-moi en DIX LIGNES MAXIMUM :
           ce que tu as compris, ta définition de « retournement », tes seuils, et
           ce qui te semble mal spécifié. AUCUN CODE AVANT MA RÉPONSE.

  Étape 1. Écris l'HYPOTHÈSE, falsifiable, AVANT toute mesure — avec ce que tu
           attends si elle est vraie et si elle est fausse. Écris l'INSTRUMENT :
           quelle mesure, quel seuil, sur combien de parties, et à quel nombre de
           parties elle devient décisive.

  Étape 2. Écris les tests de ce que tu vas mesurer, AVANT de mesurer. Un compteur
           de retournements se teste sur une partie construite à la main, dont tu
           calcules le résultat de tête. Sans ce test, ton chiffre n'est vérifiable
           par personne — c'est exactement la faute qui a coûté trois mois.

  Étape 3. Mesure. 1 000 parties minimum, seed fixé et cité.

  Étape 4. AUDITE TON PROPRE RÉSULTAT avant de me le donner, avec les trois
           questions du protocole : la mesure mesure-t-elle ce que je crois ? sur
           quel support est-elle définie ? est-elle comparable à quoi ?

  Étape 5. Compte rendu au format du paragraphe 2 de 08_modele_compte_rendu.md.
           Chaque affirmation préfixée MESURÉ, DÉDUIT ou SUPPOSÉ. Chaque chiffre
           décomposé.

DOCUMENTS À LIRE, DANS CET ORDRE

  1. documentations/01_regles.md                — les règles. Paragraphes 2.2, 5, 8.
  2. documentations/05_protocole_experimental.md — paragraphes 2 et 3, phase 1
  3. documentations/03_specification_moteur.md   — paragraphe 3, les configurations
                                                   de référence
  4. documentations/04_conventions_code.md
  5. documentations/08_modele_compte_rendu.md
  6. documentations/06_journal_decisions.md      — l'entrée du 17/08, pour savoir
                                                   ce qui vient d'être appris

  Le moteur s'utilise ainsi :

      from courtisans.cards import Role
      from courtisans.config import GameConfig
      from courtisans.engine import Engine
      config = GameConfig(familles=4, roles=tuple(Role), exemplaires=2, joueurs=3)
      etat = Engine(config).reset(seed)
      etat.legal_actions() / etat.apply(a) / etat.is_terminal()
      etat.scores() / etat.returns() / etat.vue_privilegiee()

  `vue_privilegiee()` est la vue de dieu : pioche, mains, cartes vivantes, défausse.
  Elle est réservée aux tests et à la mesure — jamais à une IA.

  Note : uv exige UV_LINK_MODE=copy sur ce dépôt (OneDrive, os error 396).

CE QUE TU NE FAIS PAS

  - Tu ne modifies pas le moteur. Il est audité. Si tu crois y voir un défaut,
    ARRÊTE-TOI et remonte-le : ne le corrige pas.
  - Tu ne changes pas l'instance pour faire passer un seuil. Si l'instance ne tient
    pas, c'est un résultat, et il se rapporte tel quel.
  - Tu n'écris aucune IA, aucune heuristique, aucune évaluation de position. La
    phase 1 mesure le jeu, elle n'y joue pas.
  - Tu ne fais pas la phase 2. Avantage de siège, winrate du greedy, ligne de base
    des comportements B1–B7 : c'est la phase suivante.
  - Tu ne modifies aucun document de `documentations/` sans mon accord.

CE QUE TU DOIS ME DONNER À LA FIN

  1. L'hypothèse et l'instrument, écrits avant la mesure.
  2. Les trois chiffres du go/no-go, avec leur définition et leur décomposition.
  3. Les statistiques demandées : durée d'une partie, distribution des scores
     finaux, fréquence des retournements, fréquence des situations où refuser de
     tuer est possible.
  4. Ce que ta mesure N'établit PAS.
  5. Une proposition d'entrée de journal, au format du paragraphe 4 de
     08_modele_compte_rendu.md.

COMMENCE PAR

  Les documents, puis tes dix lignes. Pas de code avant ma réponse.
```

---

## Notes pour l'humain qui lance ce prompt

**Ce qu'il faut donner :** l'accès au dépôt, et ce bloc. Rien d'autre.

**Ce qu'il te demandera d'arbitrer :** la définition de « retournement », et le seuil de
« distribution non dégénérée ». Les deux sont des trous du protocole expérimental, pas du
travail de l'agent.

**Le piège de cette phase.** Le seuil « un retournement dans une partie sur trois » se
satisfait ou se rate selon la définition retenue. Un agent qui choisit sa définition après
avoir vu le chiffre fabrique son propre go. Exige que la définition soit écrite à l'étape 1,
avant toute mesure — et que le compte rendu donne aussi le chiffre qu'auraient produit les
définitions concurrentes.

**Ensuite :** l'audit de la phase 1, dans une conversation distincte, avec
[07_phase1_audit.md](07_phase1_audit.md).
