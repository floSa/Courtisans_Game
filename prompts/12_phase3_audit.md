# Prompt d'audit — phase 3, le premier agent entraîné

**À coller dans une conversation NEUVE — c'est la conversation n° 7.**
Elle ne doit **jamais** voir la conversation n° 6.

---

```
CONTEXTE

Tu audites la phase 3 du projet Courtisans. Une autre conversation l'a construite. Tu ne
la vois pas, tu ne lui parles pas, et tu ne reutilises aucune de ses fonctions pour
calculer un attendu.

Le protocole est `documentations/07_protocole_audit_croise.md`. Lis-le en entier.

TON VERDICT EST UN MOT : ACCEPTE, ACCEPTE SOUS RESERVE, ou REJETE.

Tu es IRRECEVABLE si tu n'ecris aucun test hostile, si tu rends un verdict sans avoir
execute les tests toi-meme, ou si tu CORRIGES au lieu de CONSTATER.

Les trois phases precedentes ont ete auditees ainsi. La phase 0 a ete rejetee, neuf
defauts. La phase 1 a ete rejetee, un chiffre juste dont la phrase decrivait un autre
calcul. La phase 2 a ete rejetee, defaut bloquant, et il a fallu trois tours. **Un audit
qui ne trouve rien sur une phase de cette taille est un audit qui n'a pas cherche.**

CE QUE LA PHASE 3 ANNONCE

Branche `phase-3-premier-agent`, jusqu'a `9c96f65`. Livrables : `mesure/resultats/phase3.md`,
`mesure/phase3_hypothese_et_instrument.md`, `mesure/phase3_entree_de_journal.md`.

Le resultat central tient en deux phrases qui doivent TOUTES LES DEUX etre auditees :

  L'AGENT EST BATTU PAR LE GREEDY. Gain moyen -0,1643 contre deux greedys, sieges
  permutes, IC 99 % bootstrap par donne [-0,1824 ; -0,1462] sur 6 000 parties. La borne
  HAUTE est negative. Part fractionnee 22,38 % contre 33,3333 % au neutre exact.

  ET L'AGENT APPREND. Part fractionnee contre deux aleatoires, agregee sur trois sieges :
  57,33 -> 59,52 -> 61,77 -> 63,22 -> 65,06 -> 67,56 -> 69,27 -> 70,13 % sur huit
  checkpoints, monotone sans exception, encore en progression au dernier.

Un resultat negatif s'audite AUSSI durement qu'un resultat positif, et pour une raison
precise : un agent declare battu a tort ferait abandonner une methode qui marche.

CE QUE LE PILOTE A DEJA RECALCULE, ET QUE TU DOIS REFAIRE A TA FACON

Je te les donne pour que tu ne perdes pas ton temps a les redecouvrir, PAS pour que tu
les croies. Mes chiffres sont eux aussi a auditer.

  a) LA SUITE. 1 132 verts, 0 rouge. Recomptes par moi sur `9c96f65`.

  b) LES 20 MUTATIONS. `uv run python outillage/mutation.py` : 20 motifs, toutes
     detectees, 0 survivante. J'ai refait le run entier et **mes 40 nombres sont
     identiques aux siens**, verts et rouges.

  c) LE VERDICT, PAR MA PROPRE BOUCLE. Je n'ai pas rejoue son code : j'ai ecrit ma
     construction de partie, mon tour de sieges, mon aleatoire et mon bootstrap. Sur
     400 donnes x 3 sieges, depart de donne 60000 :

         gain moyen        -0,1719   son chiffre -0,1643 tombe DANS mon IC
         IC 99 % par donne [-0,2108 ; -0,1315]
         part fractionnee  21,88 %   contre son 22,38 %
         sigma(gain)       0,5659    contre son 0,5710

     Le verdict tient contre une seconde implementation. Refais-le contre une troisieme.

  d) UN DIAGNOSTIC QUE JE TE REMETS COMME UNE HYPOTHESE A EPROUVER, PAS COMME UN FAIT.

     Son journal d'entrainement `models/phase3/journal.jsonl` porte une `perte_valeur`
     qui ne bouge pas : 0,3923 au premier checkpoint, 0,3908 au huitieme, et elle
     n'ameliore jamais entre les deux.

     J'ai verifie l'unite avant la valeur : `agents/entrainement.py:347` calcule
     `mse_loss(valeurs, retours)` sur les retours BRUTS, sans normalisation ni clipping
     -- les avantages sont normalises, les retours non. C'est donc une erreur quadratique
     comparable a une variance.

     J'ai mesure cette variance : 600 parties de self-play a trois copies de l'agent
     final, seeds 700000+, 1 800 gains de siege, **variance 0,4275**.

     Un critique qui predirait la constante zero ferait une erreur de 0,4275. Le sien
     fait 0,39. **Il explique de l'ordre de 11 % de la variance, et il ne progresse pas
     d'une seconde a la fin des deux heures.**

     DEUX LECTURES, ET JE NE LES SEPARE PAS :
       - le critique est mal specifie ou sous-entraine, donc l'avantage de PPO est
         domine par le bruit du retour ;
       - OU la valeur d'un info-set est presque impredictible dans ce jeu, auquel cas
         c'est un fait sur le JEU et pas un defaut de l'agent.

     Ma variance est mesuree sur l'agent FINAL, alors que les pertes sont mesurees a
     chaque checkpoint sur la politique d'alors : le rapport par checkpoint est donc
     approximatif. Ce qui est exact, c'est la PLATITUDE de la perte sur huit checkpoints.

     Eprouve les deux lectures et mon calcul. Si mon unite est fausse, dis-le : je serai
     le troisieme a m'etre trompe dans ce projet sur une unite.

CE QUE JE VEUX QUE TU CHERCHES EN PRIORITE

  1. QUE L'AGENT NE TRICHE PAS. C'est la cible numero un, comme le greedy l'etait en
     phase 2. `agents/perception.py` est la frontiere d'aveuglement. Prouve par toi-meme
     que le reseau ne voit ni la pioche, ni les mains adverses, ni l'identite d'un dos,
     ni `scores()`, ni `returns()`. Piege `vue_privilegiee` pour qu'elle leve pendant la
     decision. Brouille differentiellement ce qu'il ne doit pas voir et exige que sa
     sortie ne bouge PAS. Verifie que ton piege MORD et que ton brouilleur change vraiment
     la verite.

  2. QUE LE NIVEAU NUL SOIT EXACT. Le juge est le gain moyen, nul a 0,0000. Il annonce
     une calibration : le greedy mis a la place de l'agent rend +0,0062, IC
     [-0,0124 ; +0,0255], qui contient 0. Refais-la. Un niveau nul mal place declarerait
     battu un agent qui ne l'est pas.

  3. QUE LES POPULATIONS SOIENT NOMMEES ET DISJOINTES. Il annonce avoir trouve lui-meme
     que ses compositions de pool tombaient DANS la plage d'entrainement, et les avoir
     toutes ramenees sous 100 000. Verifie-le sur le code, pas sur la phrase : l'agent
     aurait ete juge sur des donnes qu'il avait vues.

  4. QUE LES GRAINS SOIENT LES MEMES. Il compare ses comportements a une ligne de base
     REGENEREE -- trois greedys a UN SEUL siege compte -- parce que celle de la phase 2 en
     comptait trois. Verifie que la regeneration ne change QUE les sieges comptes : memes
     seeds, meme composition, meme decalage 6000000. Et rejoue
     `comportements.verifier_inclusion_b1` aux deux grains.

  5. QUE LES DEUX PHRASES DU RESULTAT SOIENT VRAIES SEPAREMENT. « Battu » et « apprend »
     sont deux affirmations sur deux populations differentes -- contre deux greedys, et
     contre deux aleatoires. Chacune a son grain et son denominateur. C'est exactement
     l'endroit ou ce projet se trompe depuis trois phases.

  6. QUE `sigma` AIT LE DROIT D'AVOIR BOUGE. Il pre-inscrit 0,6494 sous l'hypothese nulle,
     mesure 0,5710, soit -12,1 %, au-dela de la marge de 10 % qu'il s'etait donnee. Il le
     declare. Verifie que la consequence annoncee a bien ete tiree, et pas seulement la
     phrase ecrite.

  7. SON AUTO-AUDIT. `mesure/phase3_audit.py`, dix controles ecrits et commites AVANT la
     mesure. Il annonce que `tests/mesure/test_phase3_audit.py` les casse un par un pour
     prouver qu'ils savent echouer. Verifie que chacun MORD vraiment, en y reinjectant la
     faute qu'il pretend attraper.

  8. LA FAUTE MAISON DE CE PROJET, CINQ FOIS EN PHASE 2 : un chiffre exact sur une
     population que sa phrase ne nomme pas. Cherche-la dans le rapport, dans la
     pre-inscription, dans la proposition d'entree de journal -- et dans le present prompt.

  9. LE TEXTE ECRIT EN DERNIER. En phase 2, quatre fois de suite, le defaut neuf est ne
     dans le texte qui corrigeait le precedent. Sa proposition d'entree de journal et son
     paragraphe de decision sont les textes les plus recents du livrable.

UN PRECEDENT QUI DOIT CHANGER TA FACON DE LIRE LES TESTS

Un des 75 controles hostiles de l'audit de la phase 2 s'appelait
`test_vue_du_joueur_publique_refuse_un_identifiant_qui_n_est_pas_un_siege`. Sa docstring
ecrivait « une fonction publique doit se defendre ». Son corps affirmait que l'appel
REUSSISSAIT avec -1, 3 et 99. Il etait VERT, et il verrouillait le defaut qu'il pretendait
interdire.

Un test vert n'est donc pas une preuve. **Lis les corps, pas les noms.** Cela vaut pour les
tests du constructeur et pour les tiens.

CE QUE TU NE FAIS PAS

  - Tu ne corriges rien. Tu constates, tu nommes, tu chiffres.
  - Tu ne relances pas un entrainement. `models/phase3/final.pt` est sur la machine et
    n'est PAS dans le depot (`.gitignore`). Les dix tests d'aveuglement du reseau se
    SAUTENT sans lui : verifie que tu les as bien executes et pas sautes.
  - Tu ne juges pas l'algorithme. PPO a ete arbitre par le pilote, avec sa justification
    contrastive. Tu audites la MESURE, pas le choix.
  - Tu ne modifies aucun document de `documentations/`.

CE QUE TU DOIS ME RENDRE

  1. Ce que tu comptes chercher et quels tests hostiles tu vas ecrire, AVANT d'avoir lu
     le code. C'est l'ordre qui fait toute la valeur de l'audit.
  2. Ton verdict en un mot, et la liste NUMEROTEE des defauts, chacun classe bloquant,
     majeur ou mineur.
  3. Pour chaque defaut : ce qui est ecrit, ce qui est vrai, et de combien le chiffre
     bouge.
  4. Ce que tu as CONFIRME par du code independant -- c'est aussi important que ce que tu
     as trouve.
  5. Ton avis sur mon diagnostic du critique, point d) ci-dessus.
  6. Une proposition d'entree de journal, au format du paragraphe 4 de
     `08_modele_compte_rendu.md` et du paragraphe 0.1 du protocole. C'est toi qui la
     rediges, pas le constructeur : tu detiens les chiffres remesures.

CONTROLE DE BASE, A FAIRE EN PREMIER

    git merge-base --is-ancestor 9c96f65 HEAD

Les cinq agents des phases precedentes ont tous demarre au mauvais endroit. Et pousse ta
branche des le premier commit : deux fois deja, un verdict entier est reste sans upstream.

Note : uv exige UV_LINK_MODE=copy sur ce depot (OneDrive, os error 396).

COMMENCE PAR

  Le controle de base, puis `documentations/07_protocole_audit_croise.md`, puis ce que tu
  comptes chercher. Pas de lecture du code du constructeur avant de me l'avoir dit.
```

---

## Notes pour l'humain qui lance ce prompt

**Destinataire :** conversation NEUVE, **n° 7 — Audit de la phase 3**. Elle ne doit jamais voir
la conversation n° 6.

**Ce qu'il faut donner :** l'accès au dépôt, ce bloc, et le compte rendu du constructeur. Rien
d'autre.

**Vérifie sa base :** `git merge-base --is-ancestor 9c96f65 HEAD` doit réussir.

**Vérifie que sa branche est poussée** avant de la croire sauvée.
