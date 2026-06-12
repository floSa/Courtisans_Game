# Synthèse — où en est l'IA Courtisans (12/06/2026)

> Résumé grand-angle pour reprendre le projet en 5 minutes. Détails techniques :
> `etat_des_lieux_et_roadmap.md` (passation) et `rapport_expert.md` (historique complet,
> briques CFR aux §28-33).

## Le parcours en une phrase

AlphaZero (mai) était le mauvais paradigme pour un jeu à information imparfaite → pivot
**CFR/Deep CFR** (juin) avec l'**exploitabilité** comme vérité-terrain, validé brique par
brique sur des instances croissantes — toutes les briques sont vertes à ce jour.

## Les briques validées

Protocole : isoler UN mécanisme du jeu par mini-instance, calculer l'équilibre Nash exact
(oracle CFR+ tabulaire), vérifier que Deep CFR (réseaux) converge vers lui.

| Brique | Mécanisme isolé | États | Oracle | Deep CFR | Verdict |
|---|---|---|---|---|---|
| 1 | pipeline neuronal (2 fam) | 3 141 | 0.0002 | 0.0037 | ✅ |
| 2.1a | 3 familles | 263 761 | 0.000089 | 0.0137 | ✅ |
| 2.1b | canonicalisation ÷6 | 263 761 | 0.000122 | 0.019 à ¼ du budget | ✅ |
| 2.1c | assassins + gardes | 123 921 | 0.000093 | 0.0063 | ✅ |
| 2.1d | 2 manches avec pioche | 3 166 801 | 0.000673 | 0.0195 | ✅ |

(Exploitabilité : de combien un adversaire parfait peut exploiter la stratégie ; 0 = Nash.)

## Le playbook de débogage (acquis durement, à réutiliser)

Quand Deep CFR plafonne au-dessus de l'oracle, deux goulots **indépendants**, dans cet ordre :

1. **Budget d'entraînement des réseaux** (brique 2.1c) : la tête policy (brique 1) PUIS le
   réseau d'avantage (2.1c : 500→1500 steps = plateau 0.031→0.011). Symptôme : plateau
   précoce de la courbe buffer-exacte, couverture du buffer normale.
2. **Variance par info-set** (briques 2.1b/2.1d) : la force brute (traversals) ne suffit
   plus ; la **canonicalisation par symétrie des familles** (quotient lossless ÷6, prouvé
   par oracle identique + même équilibre) la réduit frontalement. 2.1d : 0.109→0.0195 à
   budget égal quand traversals ×3 ne faisait RIEN.

Courbes : `cfr/deep_cfr_assassin_compare.png` (2.1c) et `cfr/deep_cfr_redeal_compare.png` (2.1d).

## Ce qui reste avant l'objectif (IA forte jouable à 2 joueurs)

1. **Brique 2.1e [PROCHAIN]** : combiner les mécanismes (assassins + pioche) dans une même
   instance — dernière validation avec oracle exact.
2. **Jeu complet** (6 familles × 5 rôles × 3 exemplaires = 90 cartes) : plus d'oracle
   calculable → pilotage à l'exploitabilité approchée + matchs vs greedy PIMC (borne basse).
3. **Branchement dans l'interface** : l'agent Deep CFR remplace le greedy comme adversaire
   par défaut de l'app Streamlit.
4. *(Plus tard)* **3-5 joueurs** : plus d'équilibre de Nash garanti → ligue/PSRO, Elo vs
   pool. Le moteur `app/jeu.py` supporte déjà N joueurs.

## En attendant : jouer dès maintenant

```bash
streamlit run streamlit_app/courtisans_app.py
```

Adversaire par défaut = **greedy PIMC** (le plus fort agent mesuré, bat l'ancien réseau
AlphaZero ~99 %). Sélecteur d'adversaire + force réglable dans la barre latérale.
