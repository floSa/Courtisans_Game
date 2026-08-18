# Prompt de construction — phase 2, mesurer le jeu avant d'y jouer

**À coller dans une conversation NEUVE.** Écrit sur le modèle de
[06_phase1_construction.md](06_phase1_construction.md).

L'audit de cette phase se fait dans une **autre** conversation, avec
[09_phase2_audit.md](09_phase2_audit.md).

---

```
CONTEXTE

Tu ouvres la phase 2 du projet Courtisans. Les phases 0 et 1 sont closes, auditées
chacune par une conversation indépendante — 664 tests verts, couverture 100 % sur
courtisans/, 19 mutations sur 19 détectées. Le moteur est audité et l'instance de
travail est validée. Tu ne touches ni à l'un ni à l'autre.

    entrainement-3j : familles=4, les 5 roles, exemplaires=2, joueurs=3
                      4 x 5 x 2 = 40 cartes ; 40 // 9 = 4 tours par joueur
                      36 cartes jouees ; 4 jamais piochees

Ce projet a un historique precis. Cinq briques d'entrainement ont ete validees sur des
instances qui violaient les regles du jeu, et le plafond de performance qui a pilote
trois mois de travail etait mesure par une metrique qui jouait au hasard sur un tiers
du jeu. Personne ne l'a vu, parce que personne ne demandait a un chiffre ce qu'il
mesurait.

La phase 1 a produit une faute d'un genre plus fin, et tu dois la connaitre parce que
tu vas travailler sur le meme terrain. Le rapport annoncait « 0 sur 1 000
retournements invisibles des trois joueurs ». Le nombre etait juste et reproductible
au bit pres. Il etait faux quand meme : le calcul agregeait quatre familles en un
booleen de partie avant de comparer, si bien que la phrase parlait de retournements
quand le calcul parlait de parties. Le vrai chiffre est une partie sur treize a
dix-huit, et le propre test du constructeur le demontrait deja, dans le meme
livrable. Lis l'entree du 18/08 au journal avant de commencer.

CE QU'EST LA PHASE 2

Le paragraphe 4 de documentations/05_protocole_experimental.md, phase 2 : savoir a
quoi ressemble le terrain AVANT d'entrainer quoi que ce soit. C'est la phase que la
campagne precedente n'a jamais faite, et c'est pour ca qu'elle a interprete de travers
tous ses resultats.

Quatre mesures, qui serviront de reference pour toutes les phases suivantes :

  M1. AVANTAGE DE SIEGE. 10 000 parties appariees entre trois agents aleatoires.
      Hypothese du protocole : la position de depart n'avantage aucun joueur de facon
      decisive. Seuil ecrit : si un siege gagne plus de 38 % des parties, l'avantage
      est structurel et doit etre neutralise partout ensuite par permutation
      systematique des sieges.

  M2. VARIANCE DU SCORE FINAL entre parties. Elle dimensionne le nombre de parties
      necessaire pour conclure quoi que ce soit, dans toutes les phases suivantes.

  M3. WINRATE DU GREEDY CONTRE L'ALEATOIRE. Il fixe l'echelle : si le greedy est a
      60 %, un agent a 65 % n'est pas impressionnant.

  M4. FREQUENCE DE CHAQUE COMPORTEMENT B1-B7 CHEZ LE GREEDY. C'est LA ligne de base
      des comportements. Sans elle, « l'IA planifie des retournements » n'est pas une
      affirmation interpretable. B1 a B7 sont au paragraphe 7.2 des regles.

Go/no-go du protocole : les quatre mesures sont etablies et consignees au journal.
« Cette phase ne peut pas echouer : elle produit des faits. » Ne prends pas cette
phrase pour une permission d'etre approximatif — elle veut dire que le risque n'est
pas de rater un seuil, il est de produire un fait qui ne dit pas ce qu'il annonce.

DEUX OBSTACLES QUE LE PROTOCOLE NE MENTIONNE PAS, ET QUI SONT L'ESSENTIEL DU TRAVAIL

  A) LE GREEDY N'EXISTE PAS DANS CE DEPOT. M3 et M4 en dependent tous les deux.
     Il existe une version sur l'ancienne lignee, `git show
     origin/cfr-pivot:app/greedy_bot.py` — 281 lignes. Elle n'est PAS reutilisable :
     elle importe `app.jeu.GameEnv`, c'est-a-dire le moteur non conforme que ce projet
     a reecrit, plus `torch` et le reseau AlphaZero abandonne. La lire pour comprendre
     la regle du greedy est utile ; la porter serait importer les defauts que la
     phase 0 a corriges. En particulier son `_pick_target_heuristic` ne rendait `None`
     que si la liste de cibles etait vide : AUCUNE politique de ce projet n'a jamais
     refuse de tuer, alors que les regles le permettent (paragraphe 4 des conventions).
     Un greedy qui ne sait pas refuser rend B4 inmesurable.

     Tu reecris donc le greedy contre `courtisans/`, depuis sa regle enoncee au
     paragraphe 7.1 des regles : maximiser l'ecart de score obtenu sur le tour en
     cours, comme si la partie s'arretait la. Il va dans son propre paquet — PAS dans
     `courtisans/`, que le paragraphe 4 des conventions interdit a toute heuristique.

  B) B1 A B7 NE SONT PAS DES DEFINITIONS MESURABLES. Ce sont sept comportements
     decrits en prose. C'est exactement le piege de la phase 1, ou « retournement »
     n'etait defini nulle part et ou le seuil « une partie sur trois » se satisfaisait
     ou se ratait selon la definition retenue. Tu proposes donc SEPT definitions
     operationnelles, ecrites et validees AVANT toute mesure, et pour chacune tu dis
     ce qu'une definition concurrente aurait donne.

     Un piege particulier sur B1, et tu dois l'ecrire dans ton rapport : B1 est
     « planifier un retournement ». Le greedy a un horizon d'UN tour par construction.
     Il ne planifie donc jamais rien. Ce que tu mesures chez lui n'est pas une
     planification, c'est la frequence a laquelle le MOTIF apparait par coincidence.
     C'est la bonne ligne de base — mais si tu ne l'ecris pas, quelqu'un lira plus tard
     « le greedy planifie des retournements dans 12 % des parties ». Le meme
     avertissement vaut pour B3.

TROIS CHOSES A REMONTER, PAS A TRANCHER SEUL

  a) LE SEUIL DE 38 % DE M1 NE DISCRIMINE RIEN. A 10 000 parties et trois sieges,
     l'attendu est 33,33 % et l'erreur-type 0,471 point. Le seuil de 38 % est donc a
     9,9 erreurs-type de l'attendu : un avantage de siege de 35 %, pourtant a
     3,5 erreurs-type et statistiquement certain, PASSE le seuil sans etre signale.
     C'est le meme defaut que l'audit de la phase 1 a trouve sur les quatre criteres
     de non-degenerescence — un critere qui constate au lieu de tester. Mesure
     l'avantage, donne son intervalle de confiance, dis a partir de quel ecart il
     devient statistiquement etabli, et propose un seuil qui ait un pouvoir
     discriminant. Ne remplace pas le seuil du protocole de ta seule autorite :
     rapporte les deux.

  b) « PARTIES APPARIEES » N'EST PAS DEFINI. A trois sieges il y a 3! = 6
     permutations par donne. Dis ce que tu apparies, combien de donnes cela fait, et
     pourquoi. 10 000 n'est pas divisible par 6.

  c) LES DEUX RESERVES DE LA PHASE 1 vivent dans `mesure/`, que tu vas rouvrir :
     rien ne relie la definition de l'instance dans `mesure/instance.py` a celle de
     `tests/outils.py`, et la section 6 du rapport ne repete pas le grain sur ses
     blocs de comptage. Tu peux les traiter, mais dis-le explicitement et
     separement — ce n'est pas ta phase.

ORDRE DE TRAVAIL — NON NEGOCIABLE

C'est la boucle du paragraphe 2 de 05_protocole_experimental.md.

  Etape 0. Lis les documents ci-dessous. Puis reponds-moi en DOUZE LIGNES MAXIMUM :
           ce que tu as compris, tes sept definitions de B1 a B7 en une ligne chacune,
           ta definition de « parties appariees », et ce qui te semble mal specifie.
           AUCUN CODE AVANT MA REPONSE.

  Etape 1. Ecris l'HYPOTHESE et l'INSTRUMENT de chacune des quatre mesures, AVANT
           toute mesure, et COMMITE-LES. Pour chacune : ce que tu attends, le seuil,
           le nombre de parties, et a quel nombre de parties la mesure devient
           decisive. Un seuil se rapporte desormais avec la taille d'echantillon a
           partir de laquelle il est franchi — c'est un enseignement de la phase 1.

  Etape 2. Ecris les tests AVANT de mesurer. Chacun des sept compteurs de comportement
           se teste sur une partie construite a la main dont tu calcules le resultat de
           tete. Le greedy se teste sur des positions ou son coup est determine par sa
           regle, y compris au moins une ou il DOIT refuser de tuer.

  Etape 3. Mesure. Seeds fixes et cites. Publie les denominateurs.

  Etape 4. AUDITE TON PROPRE RESULTAT avant de me le donner. Trois questions du
           protocole : la mesure mesure-t-elle ce que je crois ? sur quel support
           est-elle definie ? est-elle comparable a quoi ? Puis les trois de la
           phase 1 : chaque taux a-t-il le bon denominateur ? chaque chiffre porte-t-il
           son echantillon — seeds, politique, grain ? un zero ou un cent pour cent
           a-t-il ete confronte a un cas construit a la main ?

  Etape 5. Compte rendu au format du paragraphe 2 de 08_modele_compte_rendu.md.
           Chaque affirmation prefixee MESURE, DEDUIT ou SUPPOSE. Chaque chiffre
           decompose.

DOCUMENTS A LIRE, DANS CET ORDRE

  1. documentations/01_regles.md                 — paragraphes 2.2, 2.6, 5, 7.1 et 7.2
  2. documentations/05_protocole_experimental.md — paragraphes 1, 2 et 3, phase 2
  3. documentations/06_journal_decisions.md      — les entrees du 17/08 et du 18/08
  4. documentations/04_conventions_code.md
  5. documentations/08_modele_compte_rendu.md
  6. mesure/hypothese_et_instrument.md           — le modele de pre-inscription qui a
                                                   tenu deux tours d'audit

  Le moteur s'utilise ainsi :

      from courtisans.cards import Role
      from courtisans.config import GameConfig
      from courtisans.engine import Engine
      config = GameConfig(familles=4, roles=tuple(Role), exemplaires=2, joueurs=3)
      etat = Engine(config).reset(seed)
      etat.legal_actions() / etat.apply(a) / etat.is_terminal()
      etat.scores() / etat.returns() / etat.vue_privilegiee()
      etat.cibles_courantes() / etat.assassin_en_resolution()

  `vue_privilegiee()` est la vue de dieu : pioche, mains, cartes vivantes, defausse.
  Reservee aux tests et a la mesure. Un AGENT ne la voit jamais — il voit
  `information_state_string` et `information_state_tensor`. Le greedy que tu ecris est
  un agent : s'il lit la vue de dieu, il triche, et son winrate ne veut rien dire.
  C'est le point sur lequel je serai le plus exigeant.

  Note : uv exige UV_LINK_MODE=copy sur ce depot (OneDrive, os error 396).

CE QUE TU NE FAIS PAS

  - Tu ne modifies pas `courtisans/`. Il est audite deux fois. Si tu crois y voir un
    defaut, ARRETE-TOI et remonte-le : ne le corrige pas.
  - Tu n'entraines aucun reseau. La phase 2 mesure le terrain ; la phase 3 y joue.
    Pas de torch, pas de GPU, pas de self-play.
  - Tu ne changes aucun seuil pour faire passer une mesure. Si l'avantage de siege
    depasse le seuil, c'est un resultat, et il se rapporte tel quel.
  - Tu ne fais pas la phase 3. Pas d'agent entraine, pas de pool d'adversaires.
  - Tu ne modifies aucun document de `documentations/` sans mon accord. Les trois
    termes non definis du protocole — « retournement », « distribution non
    degeneree », « situations ou refuser de tuer est possible » — attendent une
    correction que tu peux PROPOSER, pas ecrire.

CE QUE TU DOIS ME DONNER A LA FIN

  1. L'hypothese et l'instrument des quatre mesures, ecrits et commites avant elles.
  2. Les quatre mesures, avec intervalles de confiance et denominateurs.
  3. Les sept definitions de B1 a B7, et pour chacune ce qu'une definition
     concurrente aurait donne comme chiffre.
  4. Le greedy, teste, avec la preuve qu'il ne lit pas la vue de dieu et qu'il sait
     refuser de tuer.
  5. Ce que tes mesures N'etablissent PAS — en particulier ce que la ligne de base de
     B1 et B3 ne dit pas d'une planification.
  6. Une proposition d'entree de journal, au format du paragraphe 4 de
     08_modele_compte_rendu.md.

UN CHIFFRE DE LA PHASE 1 QUI TE CONCERNE DIRECTEMENT

7,40 % des parties contiennent une perte d'acquis de famille qu'AUCUN des trois
joueurs ne pouvait voir — deux Espions de meme famille poses par deux joueurs
differents suffisent, et personne n'a alors la vue complete. Ces retournements sont
invulnerables a toute planification, par n'importe quel agent. Ta ligne de base de B1
doit etre lue en le sachant, et tu l'ecris dans ton rapport : c'est un plafond de ce
que B1 pourra jamais mesurer, pas un defaut d'agent.

COMMENCE PAR

  Les documents, puis tes douze lignes. Pas de code avant ma reponse.
```

---

## Notes pour l'humain qui lance ce prompt

**Ce qu'il faut donner :** l'accès au dépôt sur la branche `moteur-conforme`, et ce bloc.
Rien d'autre.

**Vérifie que sa base est la bonne.** Les deux agents des phases 0 et 1 ont tous les deux
démarré sur un worktree branché sur `main`, l'ancienne lignée, où `courtisans/` n'existe pas.
Les deux l'ont vu, mais après avoir lu les documents. Le contrôle tient en une ligne :
`git log --oneline -1` doit montrer `68a5c16` ou un descendant.

**Ce qu'il te demandera d'arbitrer :** les sept définitions de B1 à B7, la définition de
« parties appariées », et le seuil de M1 — le protocole en donne un qui ne discrimine rien.
Les trois sont des trous du protocole expérimental, pas du travail de l'agent.

**Le piège de cette phase.** Elle est annoncée comme ne pouvant pas échouer. C'est vrai du
go/no-go et faux du reste : une phase qui « produit des faits » produit surtout des chiffres
que toutes les phases suivantes citeront sans les revérifier. Une ligne de base fausse ne se
voit jamais — elle rend juste tous les progrès ultérieurs incomparables. C'est le mode de
défaut qui a coûté trois mois à ce projet.

**Le point de vigilance concret.** Le greedy est un agent, pas un instrument de mesure. S'il
lit `vue_privilegiee()`, il connaît les Espions adverses et son winrate est gonflé — et c'est
ce winrate qui fixera l'échelle de toutes les phases suivantes. Exige la preuve qu'il ne voit
que son info-set.

**Ensuite :** l'audit de la phase 2, dans une conversation distincte, avec
[09_phase2_audit.md](09_phase2_audit.md).
