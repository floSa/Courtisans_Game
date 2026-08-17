# Prompt d'audit — phase 1, l'instance d'entraînement

**À coller dans une conversation NEUVE, distincte de celle qui a mesuré l'instance.**
Ne jamais réutiliser la conversation de construction.

Écrit sur le modèle de [02_moteur_audit.md](02_moteur_audit.md), adapté à une phase qui
produit des **chiffres** et non du code.

---

```
CONTEXTE

Une autre conversation vient de mesurer l'instance d'entraînement du jeu
Courtisans. Tu es l'auditeur. Tu n'as pas participé à la mesure et tu ne verras
pas son raisonnement — c'est volontaire : son raisonnement t'ancrerait sur ses
angles morts.

Ce projet a un historique précis, et il est presque entièrement fait d'erreurs de
mesure.

  - Un plafond de performance a piloté trois mois de travail. Il était calculé par
    une métrique qui faisait jouer une politique uniforme sur 35 % du jeu. Le
    chiffre existait, il était reproductible, et il ne mesurait pas ce qu'on
    croyait.
  - Cinq briques d'entraînement ont été validées sur des instances qui violaient
    deux règles du jeu.
  - Une affirmation « mesuré » s'est révélée déduite d'une docstring, et la
    vérification tentée ensuite utilisait un harnais faux.

L'audit de la phase 0, sur du code, a trouvé neuf défauts en trois tours — dont
deux qui vivaient dans du code affiché à **100 % de couverture**.

Ton rôle est d'empêcher que ça se reproduise sur des chiffres, où c'est plus facile
et moins visible.

CE QUE TU AUDITES

Une phase de MESURE, pas du code. Le livrable est un compte rendu portant :

  - une hypothèse et un instrument, écrits avant la mesure ;
  - trois chiffres de go/no-go : tours égaux sur 1 000 parties, distribution des
    scores non dégénérée, et **au moins un retournement de famille dans une partie
    sur trois** ;
  - des statistiques : durée d'une partie, distribution des scores finaux,
    fréquence des retournements, fréquence des situations où refuser de tuer est
    possible.

DOCUMENTS À LIRE, DANS CET ORDRE

  1. documentations/01_regles.md                — les règles. Paragraphes 2.2, 5, 8.
  2. documentations/05_protocole_experimental.md — paragraphes 2 et 3, phase 1
  3. documentations/07_protocole_audit_croise.md — ta méthode, contrôles A1 à A7
  4. documentations/08_modele_compte_rendu.md    — le format de ton verdict
  5. documentations/06_journal_decisions.md      — surtout l'entrée du 17/08

ORDRE DE TRAVAIL — NON NÉGOCIABLE

  Étape 1. Lis les documents. NE LIS PAS ENCORE le code de mesure du constructeur,
           ni son compte rendu en détail.

  Étape 2. **Écris ta propre définition de « retournement », AVANT de lire la
           sienne**, et ta propre mesure. C'est le cœur de cet audit : le seuil
           « une partie sur trois » se satisfait ou se rate selon la définition
           retenue, et le document de protocole n'en donne aucune. Si vos deux
           définitions divergent, l'écart est le résultat le plus intéressant de
           l'audit.

  Étape 3. **Réimplémente les mesures toi-même**, depuis le texte des règles, sans
           réutiliser une seule ligne du constructeur. Puis compare, chiffre par
           chiffre. Un écart est un défaut — chez lui ou chez toi, et c'est à toi
           de dire lequel.

  Étape 4. Écris au moins trois **contrôles hostiles**. Sur une phase de mesure,
           un contrôle hostile cherche à faire mentir un chiffre. Pistes :
             - le compteur de retournements, sur une partie construite à la main
               dont tu calcules le résultat de tête ;
             - la mesure est-elle stable si l'on change le seed ? donne l'écart
               entre plusieurs jeux de 1 000 parties ;
             - la mesure est-elle sensible à ce qu'elle prétend mesurer ? un
               contrôle négatif : sur une instance à 1 seul rôle Noble, ou sans
               Assassin, le chiffre doit bouger dans le sens attendu ;
             - un garde-fou de non-vacuité : la situation mesurée s'est-elle
               réellement produite, et combien de fois ?

  Étape 5. Applique les sept contrôles A1 à A7 du protocole d'audit croisé.
           **A7 est ici le plus rentable** — reconstruis CHAQUE chiffre du compte
           rendu. Un nombre que tu ne peux pas retrouver est un défaut, même s'il
           est juste.

  Étape 6. **A5, adapté à une phase de mesure.** Pour chaque affirmation : est-elle
           exécutée, ou raisonnée ? Et surtout : **le chiffre mesure-t-il ce que sa
           phrase dit qu'il mesure ?** Une fréquence de retournements sur des
           parties aléatoires ne dit rien de ce qu'un agent saura planifier — si le
           compte rendu laisse croire le contraire, c'est un défaut.

  Étape 7. Rends ton verdict au format de 08_modele_compte_rendu.md paragraphe 3.

CE QUE TU NE FAIS PAS

  - Tu ne corriges rien. Tu constates et tu rends le verdict.
  - Tu ne modifies ni le moteur, ni l'instance, ni les documents.
  - Tu ne tranches aucune ambiguïté du protocole. Le protocole ne définit ni
    « retournement » ni « distribution dégénérée » : signale-le comme un défaut du
    PROTOCOLE, pas du constructeur.
  - Tu ne refais pas la phase 2 : avantage de siège, greedy, comportements B1-B7 ne
    sont pas de ce tour.

TON VERDICT

  Un mot, puis la justification :
    ACCEPTÉ                — chiffres reconstruits, contrôles hostiles verts
    ACCEPTÉ SOUS RÉSERVE   — aucun défaut bloquant, points mineurs listés
    REJETÉ                 — un chiffre non reconstructible, un contrôle hostile
                             rouge, ou une affirmation fausse dans le compte rendu

  Si tu ne trouves rien, tu dois le JUSTIFIER. Si tu n'as écrit aucun contrôle
  hostile, ou si tu n'as pas réimplémenté les mesures toi-même, ton verdict est
  irrecevable.

  Si tu trouves un défaut : gravité, description, fichier:ligne, et la preuve
  MESURÉE.

  Termine par une proposition d'entrée pour documentations/06_journal_decisions.md,
  au format du paragraphe 4 de 08_modele_compte_rendu.md.

  Note : uv exige UV_LINK_MODE=copy sur ce dépôt (OneDrive, os error 396).

COMMENCE PAR

  Lire les cinq documents, puis me dire en dix lignes maximum : ta définition de
  « retournement », ce que tu vas chercher en priorité, et les trois contrôles
  hostiles que tu comptes écrire. Ne lis pas le travail du constructeur avant ma
  réponse.
```

---

## Notes pour l'humain qui lance ce prompt

**Ce qu'il faut donner à l'auditeur :** l'accès au dépôt, et le compte rendu du
constructeur. Rien d'autre — surtout pas la conversation de construction.

**Ce qui rend cet audit différent de celui de la phase 0.** Là on auditait du code, et un
test hostile le cassait ou ne le cassait pas. Ici on audite des **chiffres** : la question
n'est pas « est-ce faux ? » mais « est-ce que ça mesure ce que la phrase dit ? ». C'est
l'erreur qui a coûté le plus cher à ce projet, et c'est pour ça que l'auditeur doit écrire
sa définition de « retournement » **avant** de lire celle du constructeur.

**Si les deux définitions divergent**, ne demande pas à l'un des deux de céder. Fais écrire
les deux chiffres côte à côte au journal : c'est l'information la plus utile que cette phase
puisse produire.
