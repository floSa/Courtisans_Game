# Audit — phase 2, tour 3 — VERDICT : ACCEPTÉ

Corrections auditées : `479a57e` (avec `db0816b`). Tours précédents :
[verdict_phase_2.md](verdict_phase_2.md), [verdict_phase_2_tour_2.md](verdict_phase_2_tour_2.md).
Re-vérification limitée aux deux réserves. **977 tests verts, 0 rouge**, en 93 s — je n'ai plus
aucun test rouge contre son code.

## Réserve 1 — **levée**

**`test_p3_les_compteurs_juges_par_l_evaluation_myope_sont_QUATRE_et_nommes` passe au vert.**
C'était mon dernier rouge du tour 2 ; il revient par son nom.

Le §4 bis écrit désormais « **Quatre** compteurs de B4 sont jugés par cette même évaluation
myope », les nomme tous les quatre — `B4-strict`, `B4-departage`, `B4-contre-nature`,
`B4-meurtre-couteux` — et ajoute la phrase qui manquait : « Les **deux zéros absolus** sont dans
ce lot : ni l'un ni l'autre ne dit que le greedy n'a jamais mal joué, seulement qu'il n'a jamais
contredit sa propre évaluation. » C'est la lecture juste, et elle est écrite là où le lecteur de
la phase 3 la trouvera.

MESURÉ, le « quatre » et les quatre noms sont présents dans les **six** fichiers concernés —
`agents/greedy.py`, `mesure/comportements.py`, `mesure/resultats/phase2.md`,
`phase2_corrections_audit.md`, `phase2_definitions_et_concurrentes.md`,
`phase2_entree_de_journal.md` — et **aucune occurrence de « trois compteurs de B4 » ne
survit** dans le dépôt. Le dépassement vers `agents/greedy.py` était le bon choix : c'est la
spécification de l'agent, la phrase y était la même, et l'y laisser fausse aurait laissé le
défaut 3 à moitié une troisième fois.

## Réserve 2 — **levée**

`verifier_inclusion_b1` **lève**, et j'ai éprouvé les deux branches aux **deux grains** :
`B1-collectif < B1-motif` lève au grain du couple et au grain `-par-partie` ; l'inclusion qui
tient passe, y compris **à égalité** — `B1-collectif` majore, il n'est pas strictement
supérieur, et une garde stricte aurait interdit un cas licite. Un grain absent est ignoré et
ne lève pas : « compteur manquant » et « inclusion tombée » restent deux choses différentes.

**Mon contrôle sur l'appel avait la mauvaise forme, et je le corrige.** J'avais cherché trois
sites d'appel dans `rapport_phase2.py` ; il n'y en a qu'**un**, dans une boucle sur les trois
populations — le meilleur motif, et la même discipline que `budget_d_un_compteur`. Je le
vérifie désormais en exécutant : `section_m4` appelée avec une troisième population dont
l'inclusion est fausse **refuse d'écrire** et lève. Et l'absence de troisième population
n'empêche pas la vérification des deux autres.

L'extension au grain `-par-partie` est plus que ce que je demandais, et elle tient : les trois
couples publiés satisfont l'inclusion aux deux grains — couple `7008 ≥ 4794`, `20157 ≥ 10836`,
`21538 ≥ 13843` ; `-par-partie` `7008 ≥ 4794`, `8990 ≥ 7191`, `9327 ≥ 8254`.

**L'échantillon de mon `3 916 ≥ 2 528`, puisqu'il fallait le dire** :
`campagne_b(donnes=600, depart=6000000, nb_greedys=3)`, soit les **600 premières donnes** de la
même plage de graines, 5 400 couples `(partie, siège)`. Le sien porte les 3 334 donnes
entières, 30 006 couples. Les deux se comparent en taux : **72,52 % contre 71,78 %** pour
`B1-collectif`, **46,81 % contre 46,13 %** pour `B1-motif`.

## Sur votre réserve 3 — ce qui était juste, ce qui ne l'était pas

Le libellé était faux et je l'ai corrigé : `parties` comptait des itérations, l'unité est le
siège-partie mesuré, 10 200 dans les deux populations. Le dénominateur partagé de 4 145, lui,
était juste, et pour une raison structurelle désormais tenue par un test plutôt que déduite.
Vous avez identifié vous-même l'erreur de lecture — mon « 0,406 contre 0,407 » comparait ma
population à la sienne, pas mes deux populations entre elles. C'est cette ambiguïté qui rendait
votre inférence raisonnable, et elle venait de ma phrase.

## Dernier coup d'œil à ce qui a été écrit en dernier — hors réserves, non compté

Suivant votre ordre de lecture, j'ai regardé `db0816b`, le plus récent, et non les mesures. Il
contient **une quatrième occurrence de la même faute, trouvée par le constructeur dans sa propre
dernière phrase** : la ligne des durées machine annonçait « −26 % à +16 % » sur « les cinq
campagnes », alors que le −26 % venait de `B, 3 greedys`, qui n'existe que dans les passes 3 à 5
et que la phrase excluait. Deux chiffres exacts sur une population que la phrase ne nommait pas.
Corrigé en « −23,3 % à +15,5 % », et j'ai refait les trois : `83,5/108,8 = −23,25 %`,
`108,8/94,2 = +15,50 %`, `133,6/180,0 = −25,78 %`. Exacts.

Il ajoute aussi, à côté de son contrôle de non-régression, ce que ce contrôle **ne dit pas** :
qu'il établit la neutralité du refactor et non la justesse de l'unité, et que le piège du
`2 234` s'applique à un contrôle aussi bien qu'à un nombre. C'est l'enseignement du tour 2
retourné contre son propre instrument, et c'est la bonne façon de le retenir.

## Justification du verdict

Les deux réserves sont levées, mon dernier test rouge est vert et nommé, et aucun de mes 39
contrôles de re-vérification ni de mes 66 contrôles hostiles ne tombe contre `479a57e`. Les
deux corrections sont des **levées d'exception**, pas des phrases : c'est ce qui les distingue
d'un correctif, et c'est désormais le motif constant de cette phase.

La phase 2 est auditée. Je propose la clôture.
