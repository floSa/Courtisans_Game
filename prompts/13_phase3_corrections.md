# Corrections après l'audit — phase 3, tour 1

**À coller dans la conversation n° 6 — Construction de la phase 3.** Elle est rouverte.

Verdict de la conversation n° 7 : **REJETÉ**, deux bloquants, quatre majeurs, huit mineurs.

---

```
L'AUDIT A RENDU : REJETE. Deux bloquants, quatre majeurs, huit mineurs.

Tu rouvres pour corriger. Tu ne recommences pas la phase.

CE QUE LE PILOTE A RECALCULE LUI-MEME AVANT DE TE TRANSMETTRE

Je ne te relaie pas un verdict, je te relaie ce que j'ai verifie. Sur TON PROPRE
`models/phase3/journal.jsonl` :

  - les huit intervalles de tes checkpoints se recouvrent 7 FOIS SUR 7 ;
  - ckpt 1 contre ckpt 8 : [53,92 ; 60,85] contre [67,05 ; 73,19], AUCUN recouvrement ;
  - ton dernier pas vaut +0,86 pt pour un detectable que TA pre-inscription fixe a 2,75.

Et j'ai relu le texte de ta pre-inscription ligne 321. L'auditeur a raison contre moi sur
ce point, je te le dis avant de te demander quoi que ce soit.

CE QUI EST ACQUIS, ET QUI NE SE REFAIT PAS

Ne retouche a rien de tout ceci. Trois implementations concordent.

  - LE VERDICT. L'agent est battu par le greedy. Toi -0,1643, moi -0,1719, l'auditeur
    -0,1734 ; les trois IC se contiennent, les trois bornes hautes sont negatives.
  - L'AVEUGLEMENT. 88 controles de l'auditeur : tenseur, chaine et logits identiques bit a
    bit sous permutation de la pioche, des mains et de l'identite des dos ; zero appel
    privilegie compte pendant la decision ; son brouilleur attrape un tenseur qui fuiterait
    UNE composante. Ton agent ne triche pas.
  - LA DISJONCTION DES POPULATIONS, verifiee AU NIVEAU DES DONNES et pas des seeds :
    0 collision de pioche entre tes 14 600 donnes de mesure et les 1 486 336 donnes
    d'entrainement balayees en entier. Le defaut que ton auto-audit avait trouve etait
    reel, et ta correction tient.
  - LA CALIBRATION DU NIVEAU NUL, refaite : +0,0152 IC [-0,0036 ; +0,0338] chez l'auditeur
    contre ton +0,0062 IC [-0,0124 ; +0,0255]. Les deux contiennent 0.
  - QUE L'AGENT APPREND entre son premier et son dernier checkpoint : ecart apparie
    +14,22 pt, IC [+10,99 ; +17,49].
  - 20/20 mutations, 1 132 verts, 0 rouge, 0 saute.

LES DEUX BLOQUANTS

  1. « IL PROGRESSAIT ENCORE AU DERNIER » N'EST PAS ETABLI, ET C'EST CETTE PHRASE QUI PORTE
     TA DECISION.

     Tes sept pas valent +2,19 / +2,25 / +1,45 / +1,83 / +2,50 / +1,71 / +0,86 pt. Ta
     propre pre-inscription §8.1 fixe l'ecart detectable de ce budget a 2,75 pt. AUCUN des
     sept n'est detectable. Les huit IC se recouvrent 7 fois sur 7 — je l'ai recalcule.

     La remesure de l'auditeur, MEMES DONNES et autre aleatoire de tirage, porte DEUX
     inversions et un dernier pas NEGATIF : -0,53 pt, IC [-3,19 ; +2,23]. La monotonie
     n'est pas une propriete de ton agent, c'est une propriete de ton tirage.

     Et ton propre §3 te contredisait deja : contre tes checkpoints 5, 6, 7 et 8, les
     quatre IC contiennent zero. Ton entree de journal, ecrite APRES, dit « l'agent
     apprend, SANS AMBIGUITE » et n'en reprend rien. C'est la quatrieme fois dans ce
     projet que le texte ecrit en dernier durcit ce que la mesure nuancait.

     CE QUE TU CORRIGES. « L'agent apprend » reste, c'est etabli — +14,22 pt entre le
     premier et le dernier. « Monotone sans exception » et « encore en progression au
     dernier » disparaissent, du rapport ET de l'entree de journal. Et ta decision, qui
     s'appuyait dessus pour designer le budget, tombe avec.

     TU PUBLIES DESORMAIS L'IC DE TES ECARTS, pas seulement de tes niveaux. Un ecart
     appari ne coute pas une partie de plus. C'est devenu une regle du §0.2 du protocole.

  2. TU N'AS RIEN A CORRIGER SUR LE SECOND : IL EST A MOI.

     Le garde-fou que j'ai reecrit le 21/08 se declenchait sur trois checkpoints
     consecutifs a intervalles recouvrants. Comme ils se recouvrent 7 fois sur 7, il aurait
     tue ton run au CHECKPOINT 3, a 45 minutes sur 120. Je l'ai recalcule, c'est exact.

     Quatrieme defaut du meme garde-fou, ne dans le texte qui corrigeait le troisieme.
     Corrige au protocole, et CETTE FOIS eprouve sur tes donnees avant d'etre ecrit : la
     portee passe a trois checkpoints, et tes cinq ecarts de portee trois valent +5,89,
     +5,54, +5,79, +6,05 et +5,07 pt pour un detectable de 2,75. Aucun ne declenche.

     La regle generale, que les quatre versions n'avaient pas : UN GARDE-FOU NE PEUT
     CHERCHER QU'UN PROGRES PLUS GRAND QUE L'ECART DETECTABLE A SON PROPRE BUDGET.

LES QUATRE MAJEURS

  3. DEUX DE TES DIX CONTROLES NE PEUVENT PAS ECHOUER. `mesure/phase3_audit.py`, R4 et R5
     passent un `True` LITTERAL en troisieme argument de `_c(...)`. Verifie par moi. Et
     `tests/mesure/test_phase3_audit.py` n'en casse que 6 sur 10.

     Ton entree de journal ecrit « CHACUN est verifie capable d'echouer... qui les casse un
     par un ». C'est faux pour quatre, et structurellement impossible pour deux.

     Corrige les deux pour qu'ils puissent echouer, casse les quatre non casses, ou donne
     aux non-falsifiables un statut DISTINCT — releve, pas concluant. Et reecris la phrase.

  4. R4 NE VOIT PAS LES DEUX ZEROS QUE TON PROPRE RAPPORT PUBLIE. Il ne regarde que
     `c.agent`, et imprime « 0 valeur extreme chez l'agent -- aucune », alors que
     `B4-contre-nature` 0,00 % (0/1967) et `B4-meurtre-couteux` 0,00 % (0/10382) sont du
     cote ligne de base. La regle du §0.2 — un zero absolu se confronte a un cas construit
     a la main — n'est donc exercee sur AUCUN des deux zeros du rapport.

  5. DEUX POPULATIONS PUBLIEES SOUS LE MEME NOM. La chaine
     « 1 agent entraine contre 2 aleatoires (garde-fou) » est a `phase3_mesure.py:413` ET a
     `campagne.py:154`, pour deux campagnes differentes — 600 donnes seeds 40000-40599 au
     checkpoint courant, et 500 donnes seeds 70000-70499 sur `final.pt`. Verifie par moi.
     Le rapport publie 70,03 % pour l'une et 70,13 % pour l'autre.

     Ton controle R2 ne voit pas le doublon parce qu'il ne s'applique qu'a la liste `pool`.
     C'est la faute maison du projet, dans le controle cense l'attraper.

  6. TA REGLE « HORS BUDGET » EST DU CODE MORT. `comparer` appelle `budget_d_un_compteur`
     avec `ecart=None`, donc `hors_budget` est toujours faux et la branche `elif` est
     inatteignable. Verifie par moi. Or ta pre-inscription §9.2 annonce que les 8 lignes
     hors budget a 6 000 parties NE SONT PAS comparees, et les nomme. Tu les as toutes
     comparees, et tu en declares quatre « separables ». Rien ne signale l'ecart.

LES HUIT MINEURS

  7. LA MARGE DE 10 % NE PORTAIT PAS SUR SIGMA, ET ELLE N'EST PAS FRANCHIE. Ta
     pre-inscription ligne 321 dit « la DEMI-LARGEUR sera remesuree ; si ELLE en differe de
     plus de 10 % ». Demi-largeur 0,0181 contre 0,0183 pre-inscrit : -1,1 %. Le
     declencheur n'est pas franchi.

     J'AI PROPAGE TON ERREUR SANS LA VOIR, alors que j'avais lu ce paragraphe. Je te le
     signale parce que la correction est a faire quand meme : le rapport declare franchie
     une regle portant sur une autre grandeur, sans dire qu'il change de grandeur.

     Et le constat vaut mieux que le defaut : ta regle etait AVEUGLE au mouvement qu'elle
     pretendait detecter. Sigma a chute de 12,1 % et l'effet de plan est monte de 0,7200 a
     0,8870 ; les deux se compensent dans la demi-largeur. Ecris-le.

  8. L'ECART DETECTABLE DES COMPORTEMENTS suppose des denominateurs egaux ; cinq lignes ne
     les ont pas. Recalcule avec les effectifs reels : `B4-strict` passe de 2,37 a 3,96 pt.
     Aucune des 34 lignes ne change de statut — mais le chiffre publie est faux. Et la
     docstring de `ecart_de_taux_detectable` dit que son argument est le taux du greedy ;
     `comparer` lui passe celui de l'agent.

  9. LE TABLEAU CENTRAL DE TON RAPPORT NE SE REND PAS COMME UN TABLEAU.
     `rapport_phase3.py:362-377` insere un blockquote puis une ligne vide entre l'en-tete et
     les 34 lignes : elles sortent dans un `<p>`.

 10. « LES QUATRE PLAGES » SUIVI D'UNE LISTE DE SIX, `phase3_mesure.py:71`, dont cinq sont
     sous 100 000, une ne l'est pas, et la variante deterministe manque a la liste. Un
     compte n'est pas une liste de noms — dans le texte qui documente la correction.

 11. « MEMES SEEDS » DESIGNE LA PHASE 2, PAS TA CAMPAGNE. Ta ligne de base des comportements
     joue les donnes 0-1999, ton agent les donnes 60000-61999 : les deux echantillons ne
     partagent aucune donne et la comparaison n'est pas appariee. Dis-le.

 12. `verifier_inclusion_b1` compare des numerateurs sans garde de grain — elle ne consulte
     `grain` que pour le message d'erreur.

 13. « PARAGRAPHE 10 DE LA PRE-INSCRIPTION » POUR 7 POINTS dont un est au §9.2, et le point 6
     du §10 ne figure pas dans la liste.

 14. LES 20 MUTATIONS NE COUVRENT AUCUN FICHIER DE LA PHASE 3. Elles ciblent toutes
     `courtisans/`, ce qui est conforme au §0.3 — mais « 20 mutations, toutes detectees » ne
     dit alors RIEN de `agents/reseau.py`, `agents/entrainement.py`, `agents/campagne.py` ni
     de `mesure/phase3*.py`. Ne mute pas ces fichiers sans me le demander : c'est un
     arbitrage de perimetre, pas une correction. Ecris la limite dans ton rapport.

LE DIAGNOSTIC DU CRITIQUE — L'AUDITEUR A TRANCHE, ET CA CHANGE TA DECISION

J'avais mesure que ton critique explique environ 11 % de la variance des retours et ne
progresse jamais. Je laissais deux lectures ouvertes. L'auditeur en a REFUTE une.

Il a mesure le PLANCHER — la part de variance qu'aucun critique ne peut predire — en
rejouant le meme etat 24 fois : `E[Var(R | etat)] = 0,1815`, soit 43 % d'irreductible. Un
critique parfait plafonnerait vers 0,18 ; le tien est a 0,38. Et surtout, le plancher
S'EFFONDRE avec la profondeur (0,32 -> 0,0075 a l'avant-derniere decision) alors que ta MSE
reste PLATE (0,36 -> 0,30). A l'avant-derniere decision la partie est presque ecrite, et ton
critique y fait quarante fois l'erreur qu'il devrait.

La lecture « la valeur est impredictible dans ce jeu » est donc REFUTEE. Il reste : le
critique est mal specifie ou sous-entraine, `R2 = 0,09` la ou 0,57 est atteignable.

CONSEQUENCE, ET C'EST L'ARBITRAGE DU PILOTE : LE LEVIER N'EST PAS LE BUDGET.

Ton entree de journal ecrit « ce que le resultat ecarte est le budget, pas la methode » et
designe le levier 1. Les deux jambes de cette phrase sont tombees : la courbe ne montre pas
qu'elle montait encore, et le critique est mesure defaillant. Rallonger un run dont
l'avantage de PPO est domine par le bruit du retour rallonge le bruit.

Reecris ta decision. Le levier que la mesure designe est la TETE DE VALEUR — ce que ton
propre §7.1 avait ecrit d'avance comme reponse prevue. Tu ne l'implementes PAS maintenant :
c'est la phase 4. Tu corriges le texte qui designait le budget.

CE QUE TU ME RENDS

  1. Les defauts 1, 3, 4, 5, 6 corriges, chacun avec ce qui l'empeche de se defaire.
  2. Les mineurs 7 a 13 corriges. Le 14 documente, pas corrige.
  3. Le rapport et l'entree de journal reecrits sur les deux points qui tombent : la
     monotonie, et la decision.
  4. La suite verte et les 20 mutations rejouees si tu touches a `courtisans/`.
  5. RELIS EN DERNIER CE QUE TU AS ECRIT EN DERNIER. Cinq fois dans ce projet, le defaut
     neuf est ne dans la correction du precedent — y compris chez moi, hier, sur le
     garde-fou.

Tu ne refais aucune campagne. Aucun chiffre acquis ci-dessus ne bouge.
```

---

## Notes pour l'humain qui colle ce bloc

**Destinataire :** conversation n° 6 — Construction de la phase 3. Elle est rouverte, ce n'est
pas une conversation neuve.

**Ensuite :** retour à la conversation n° 7 — Audit de la phase 3, pour re-vérifier **uniquement**
ces défauts. Pas un audit complet.
