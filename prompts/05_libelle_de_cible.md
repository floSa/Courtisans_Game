# Prompt — la réserve de l'audit : le libellé d'une carte cachée

**Conversation neuve.** Court : un défaut, un arbitrage déjà rendu, une vingtaine de lignes.
À faire avant la phase 3, et autant le faire maintenant que le moteur est frais.

---

```
CONTEXTE

Le moteur de règles du jeu Courtisans vient de clore sa phase 0 : 576 tests verts,
18 mutations sur 18 détectées, couverture 618/618, audité par une conversation
distincte qui a rendu le verdict ACCEPTÉ SOUS RÉSERVE.

Il reste UNE réserve, et c'est ton travail.

LE DÉFAUT

`EtatCourtisans._action_to_string` (courtisans/openspiel_adapter.py) nomme la
famille et le rôle de la carte ciblée par un Assassin :

    tuer f3-ESPION

Quand la cible est un **Espion posé face cachée par un adversaire**, le joueur qui
choisit la cible ne connaît pas son identité — il voit un dos. Le libellé, lui,
l'écrit en clair.

Rien ne fuite aujourd'hui : ces libellés ne sont lus que par des traces de
débogage. Le risque est en aval — l'interface Streamlit, une trace consommée par
un agent, un log d'entraînement. Et rien ne le signalera : l'invariant I7 ne
surveille que `information_state_string`, pas `action_to_string`.

L'ARBITRAGE EST RENDU — ne le rediscute pas

Un libellé de cible dit **ce que la carte est** et **laquelle c'est**, sans jamais
révéler ce que le joueur ignore :

  - carte VISIBLE  : on peut tout nommer, famille et rôle compris.
  - carte CACHÉE   : on ne nomme ni la famille ni le rôle. On dit que c'est un dos,
                     et on le situe.

La position se compte sur les cartes **encore en jeu** dans la zone, pas sur
l'ordre historique des poses : c'est ce qu'un joueur humain voit sur la table.

Forme attendue, à ajuster si la contrainte technique l'impose :

    tuer le 2e dos en Estime
    tuer le Noble f3 dans le domaine de J+1
    ne pas tuer

CONTRAINTE TECHNIQUE, NON NÉGOCIABLE

**Deux actions légales distinctes doivent porter deux libellés distincts.**
OpenSpiel l'exige et son harnais `random_sim_test` le vérifie ; c'est le défaut 7
de l'audit, corrigé au tour précédent, et le rouvrir ferait échouer le harnais.
Deux dos dans la même zone doivent donc rester distinguables — c'est précisément
ce que l'ordinal apporte.

DOCUMENTS À LIRE

  1. documentations/01_regles.md, paragraphes 2.6, 4.1 et 4.2 — ce qu'un joueur sait
  2. documentations/03_specification_moteur.md, paragraphe 5 — l'invariant I7
  3. documentations/04_conventions_code.md
  4. documentations/08_modele_compte_rendu.md — le format de ton compte rendu

CE QUI EST DÉJÀ VRAI — À NE PAS CASSER

  576 passed                 uv run pytest -q
  127 / 127 / 127            les trois moteurs
  143 invariants             8 / 8 critères d'acceptation
  618 instructions, 0 manquante
  18 mutations, 18 détectées
  ruff check .               All checks passed

  Note : uv exige UV_LINK_MODE=copy sur ce dépôt (OneDrive, os error 396).

ORDRE DE TRAVAIL

  Étape 1. Écris d'abord les tests ROUGES. Au minimum :
             - le libellé d'une cible cachée ne contient ni sa famille ni son rôle ;
             - le libellé d'une cible visible les contient ;
             - deux dos de la même zone portent deux libellés différents ;
             - un test hostile qui construit une zone avec plusieurs dos et vérifie
               qu'aucun libellé ne permet de reconstituer une identité cachée.
           Montre-les rouges, avec leur sortie.

  Étape 2. Corrige.

  Étape 3. Ajoute une mutation à outillage/mutation.py qui remet le défaut —
           le libellé qui nomme une carte cachée — et vérifie qu'elle est détectée.
           La batterie exige un arbre propre : commite avant de la lancer.

  Étape 4. Rejoue les six chiffres ci-dessus et cite-les avec leur valeur mesurée.

  Étape 5. Compte rendu au format du paragraphe 2 de 08_modele_compte_rendu.md.

CE QUE TU NE FAIS PAS

  - Tu ne touches pas à `information_state_string` ni à `information_state_tensor` :
    ils sont audités et corrects.
  - Tu n'affaiblis aucun test existant. Si l'un devient rouge, arrête-toi et
    remonte-le.
  - Tu n'étends pas l'invariant I7 à `action_to_string` sans me le demander :
    ce serait modifier la spécification.

COMMENCE PAR

  Les documents, puis cinq lignes : ce que tu as compris, la forme exacte de libellé
  que tu proposes, et les tests rouges que tu vas écrire. Pas de code avant ma
  réponse.
```
