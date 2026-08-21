# Plan d'audit de la phase 3 — pré-inscrit AVANT toute lecture du code du constructeur

Ecrit apres lecture de `documentations/07`, `08` et `05` seuls. Aucun fichier de
`agents/`, `mesure/phase3*`, `tests/agents/`, `tests/mesure/` n'a ete ouvert a
l'instant de ce commit. Le commit qui suit fait foi.

## Ce que je tiens pour non acquis

Les quatre chiffres que le pilote me remet (suite verte, 20 mutations, sa contre-mesure
-0,1719, sa variance 0,4275) sont des affirmations a auditer, pas des acquis. Je les
refais a ma facon. Mon soupcon prealable le plus fort, formule avant d'avoir rien lu :

**S0.** Le garde-fou pre-inscrit du protocole (§ phase 3) dit : *l'agent est compare a
la part fractionnee du greedy contre deux aleatoires, 86,52 %, et s'il ne l'a pas
depassee au dernier checkpoint, on arrete : l'agent n'apprend pas.* Le resultat annonce
est **70,13 %** au dernier checkpoint. 70,13 < 86,52. La phrase « ET L'AGENT APPREND »
est donc, au sens litteral du garde-fou pre-inscrit, la conclusion inverse de celle que
la pre-inscription attachait a ce chiffre. Je cherche en priorite si la consequence
pre-inscrite a ete tiree ou si elle a ete rehabillee apres coup. C'est le meme motif que
le defaut « sigma a bouge de 12,1 % » que le pilote me signale : une regle chiffree
ecrite avant, franchie, et declaree au lieu d'etre suivie.

## Axe 1 — L'agent ne triche pas (cible n° 1)

- **T1 brouillage differentiel.** Deux etats qui ne different QUE par de l'information
  cachee au siege courant (mains adverses, ordre residuel de la pioche, identite des dos
  non revelee). Exiger l'observation encodee identique **bit a bit**, et la sortie du
  reseau identique. Contre-controle obligatoire : prouver que mon brouilleur a
  reellement change la verite cachee (sinon je verrouille le defaut, comme le test vert
  de la phase 2).
- **T2 piege qui mord.** Rendre explosive toute fonction d'acces privilegie
  (`vue_privilegiee`, `scores`, `returns`, mains, pioche) pendant `choisir`. Controle du
  piege : un appel volontaire doit lever. Si le piege ne mord pas, le test ne vaut rien.
- **T3 comptage d'appels.** Compter, pas seulement interdire : zero appel a chaque
  fonction privilegiee sur N decisions reelles, avec un compteur dont je prouve qu'il
  compte.
- **T4 masque legal.** L'agent ne joue jamais une action illegale, et l'information qui
  entre dans le masque est celle qu'un siege a le droit de connaitre.
- **T5 dix tests d'aveuglement du constructeur.** Verifier qu'ils s'EXECUTENT et ne se
  SAUTENT pas faute de `final.pt`, en lisant le compte des skipped.

## Axe 2 — Le niveau nul est exact

- **T6 zero algebrique.** Trois greedys, sieges permutes systematiquement, memes donnes :
  le gain moyen agrege doit valoir **exactement 0,0000**, par identite de somme nulle, si
  et seulement si la permutation est complete et les agents identiques. Sa calibration
  annonce **+0,0062 avec un IC**. Un ecart non nul mesure donc autre chose : soit le
  greedy n'est pas deterministe, soit la permutation n'est pas complete, soit les trois
  greedys ne consomment pas le meme alea. Je determine laquelle, et je verifie que son IC
  couvre bien cette source-la.
- **T7 valeur nulle de la part fractionnee.** 33,3333 % n'est la valeur nulle que sous
  une composition homogene et une permutation complete. Je la reconstruis.

## Axe 3 — Populations nommees et disjointes

- **T8 disjonction au niveau des DONNES, pas des seeds.** Deux plages de seeds disjointes
  peuvent produire des donnes identiques si la donne est derivee du seed par autre chose
  que l'identite. Je hache les donnes effectivement produites sur la plage
  d'entrainement, sur celle du pool, sur celle de la mesure, sur celle de la calibration,
  et j'intersecte les empreintes. Attendu : intersection vide.
- **T9 enumeration des plages.** Reconstruire par le code, et non par la phrase du
  rapport, les bornes reellement consommees (nombre de parties x sieges x checkpoints).

## Axe 4 — Les grains

- **T10 regeneration a un siege.** Verifier que la ligne de base regeneree ne change QUE
  le nombre de sieges comptes : memes seeds, meme composition, meme decalage 6000000.
  Test hostile : recalculer la baseline a trois sieges a partir de la regeneration a un
  siege et retrouver le chiffre de la phase 2.
- **T11 la garde de grain MORD.** Appeler `verifier_inclusion_b1`, `ecart_de_taux` et
  `cumuler` avec deux grains differents et exiger qu'elles LEVENT. Puis avec le meme
  grain et exiger qu'elles ne levent pas. Une garde qui ne leve jamais est le defaut, pas
  la parade.

## Axe 5 — Les deux phrases, separement

- **T12 « battu ».** Population = 1 agent + 2 greedys. 6 000 parties = combien de donnes ?
  Le bootstrap est-il reellement PAR DONNE (bloc de 3) ou par partie ? Je calcule les
  deux IC et je regarde lequel est publie. Un bootstrap par partie sur des parties
  correlees sous-estime l'IC.
- **T13 « apprend ».** Population = 1 agent + 2 aleatoires. Les 8 checkpoints sont-ils
  evalues sur les MEMES donnes ? Quel n par checkpoint, quel IC sur chaque ecart
  successif ? « Monotone sans exception » sur 8 points est peu impressionnant si chaque
  pas est dans le bruit : je calcule la probabilite d'une monotonie fortuite au n annonce.
- **T14 les denominateurs.** Chaque taux publie porte-t-il l'unite qu'il compte ?

## Axe 6 — sigma a le droit d'avoir bouge

- **T15** Recalculer le budget requis sous sigma pre-inscrit 0,6494 et sous sigma mesure
  0,5710, et verifier que la consequence pre-inscrite a ete EXECUTEE, pas seulement
  ecrite. Meme controle que S0.

## Axe 7 — L'auto-audit mord

- **T16** Pour chacun des dix controles de `mesure/phase3_audit.py`, je reinjecte
  moi-meme la faute qu'il pretend attraper (mutation ciblee du code de mesure) et
  j'exige le rouge. Je lis les CORPS de `tests/mesure/test_phase3_audit.py`, pas les
  noms — precedent
  `test_vue_du_joueur_publique_refuse_un_identifiant_qui_n_est_pas_un_siege`.
- **T17** Grep de toute la suite a la recherche du meme motif : une docstring qui
  interdit, un corps qui autorise. Je lis les assertions, pas les intitules.

## Axe 8 — La faute maison : un chiffre exact sur une population non nommee

- **T18** Passer chaque nombre du rapport, de la pre-inscription et de la proposition
  d'entree de journal, et pour chacun : quelle composition, quel grain, quel
  denominateur, quelles seeds, et la phrase les nomme-t-elle ? Y compris dans le prompt
  d'audit du pilote lui-meme.

## Axe 9 — Le texte ecrit en dernier

- **T19** Relire en dernier, et le plus durement, `phase3_entree_de_journal.md` et le
  paragraphe de decision : quatre fois en phase 2 le defaut neuf est ne la.

## Axe 10 — Le diagnostic du critique (point d du pilote)

- **T20 l'unite avant la valeur.** Que sont exactement les `retours` de `mse_loss` :
  gains de fin de partie bruts, retours actualises, ou cibles GAE `avantage + valeur` ?
  Les trois n'ont pas la meme variance. Si ce sont des cibles GAE, la reference 0,4275 du
  pilote est la mauvaise reference et son « 11 % de la variance » tombe.
- **T21 trancher entre ses deux lectures, par la profondeur.** La variance du retour
  conditionnee a l'info-set doit s'effondrer vers la fin de partie : a l'avant-dernier
  coup, le score est presque ecrit. Je mesure la variance residuelle du gain par
  profondeur de noeud. Si elle s'effondre en fin de partie alors que la perte du critique
  reste plate a 0,39 sur tous les etats, la lecture « le jeu est impredictible » est
  refutee et il reste « critique mal specifie ou sous-entraine ». C'est le test qui separe
  ses deux lectures, et il ne demande aucun entrainement.
- **T22** Verifier que la perte lue dans le journal est bien une perte de validation
  comparable entre checkpoints, et non une perte post-mise-a-jour sur le batch courant.

## Ce que je ne fais pas

Je ne corrige rien, je ne relance aucun entrainement, je ne juge pas le choix de PPO, je
ne touche a aucun fichier de `documentations/`.
