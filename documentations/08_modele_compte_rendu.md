# Modèle de compte rendu d'agent

**Format imposé. Tout agent, constructeur ou auditeur, rend compte dans ce format. Pas de prose libre.**

Objectif : que l'humain puisse lire quinze comptes rendus successifs sans réapprendre à
les lire, et repérer en dix secondes ce qui n'est pas solide.

---

## 1. Les trois niveaux de preuve

**À utiliser dans chaque affirmation factuelle. Sans exception.**

| Niveau | Signification | Exemple |
|---|---|---|
| **MESURÉ** | J'ai exécuté et lu le résultat | *MESURÉ : 8 250 001 états, traversée exhaustive en 786 s* |
| **DÉDUIT** | J'ai lu le code et raisonné, je n'ai pas exécuté | *DÉDUIT de `is_done` ligne 236 — non exécuté* |
| **SUPPOSÉ** | Je n'ai ni mesuré ni lu, c'est une hypothèse | *SUPPOSÉ : le GPU réduirait l'itération à ~1 min* |

**Ne jamais présenter un DÉDUIT comme un MESURÉ.** C'est l'erreur la plus coûteuse de
l'historique de ce projet, et elle s'est produite trois fois — voir
[07_protocole_audit_croise.md](07_protocole_audit_croise.md) §2.

---

## 2. Compte rendu de construction

```markdown
## Étape <n> — <titre>

### 1. Fait
<Une phrase. Ce qui a été produit.>

### 2. Tests
- écrits    : <nombre>
- verts     : <nombre>
- rouges    : <nombre> — <lesquels et pourquoi>
- commande  : <la commande exacte pour les rejouer>

### 3. Critères d'acceptation
| # | Critère | Statut | Preuve |
|---|---|---|---|
| A1 | ... | ✅ / ❌ | <MESURÉ : ...> |

### 4. Trouvé, non prévu
<Ce qui est apparu et n'était pas au programme, Y COMPRIS mes propres erreurs.
 Si rien : "rien" — mais c'est rare et suspect.>

### 5. Incertain
<Ce que je ne peux pas garantir, et pourquoi.>

### 6. Chiffres
<Chaque chiffre cité ci-dessus, avec sa décomposition ou sa ligne de code.
 Un chiffre que le lecteur ne peut pas reconstruire n'a pas sa place ici.>

### 7. Bloqué sur
<Ce qui nécessite un arbitrage humain. "rien" si rien.>
```

---

## 3. Compte rendu d'audit

```markdown
## Audit — <phase> — VERDICT : ACCEPTÉ | ACCEPTÉ SOUS RÉSERVE | REJETÉ

### Constats

| # | Contrôle | Résultat |
|---|---|---|
| A1 | Tests rejoués moi-même | <nombre verts / annoncés> |
| A2 | Tests relus contre la spec | <combien vérifient le code au lieu de la règle> |
| A3 | Tests hostiles écrits par moi | <nombre> — <verts / rouges> |
| A4 | Critères d'acceptation revérifiés | <n/N> |
| A5 | Niveaux de preuve du compte rendu | <combien de DÉDUIT présentés comme MESURÉ> |
| A6 | Valeurs en dur, duplications | <nombre trouvé> |
| A7 | Chiffres reconstruits | <n/N> |

### Tests hostiles écrits
1. <intitulé> — <ce qu'il cherche à casser> — <vert / rouge>
2. ...
3. ...

### Défauts
| # | Gravité | Défaut | Où | Preuve |
|---|---|---|---|---|
| 1 | bloquant / majeur / mineur | ... | fichier:ligne | <MESURÉ : ...> |

### Justification du verdict
<Deux à cinq lignes. Si ACCEPTÉ : pourquoi les sept contrôles sont concluants.
 Un audit qui ne trouve rien doit expliquer pourquoi il n'a rien trouvé.>
```

---

## 4. Entrée de journal

À reporter dans [06_journal_decisions.md](06_journal_decisions.md) après chaque cycle
construction + audit.

```markdown
## [date] Phase <n> — <titre>

Hypothèse   : <énoncé falsifiable, écrit AVANT>
Instrument  : <métrique, seuil chiffré, durée à laquelle elle devient décisive>
Résultat    : <ce qui a été mesuré>
Audit       : <verdict + ce que l'auditeur a trouvé que le constructeur avait manqué>
Décision    : go / pivot / abandon — <justification>
Impact plan : <phases invalidées ou modifiées>
```

---

## 5. Ce qui rend un compte rendu irrecevable

| Symptôme | Correction |
|---|---|
| « Les tests passent » | Donner le nombre et la commande |
| Une affirmation sans niveau de preuve | Préfixer MESURÉ, DÉDUIT ou SUPPOSÉ |
| Section « Trouvé, non prévu » vide sur une étape non triviale | Suspect — relire |
| Section « Incertain » vide | Toujours suspect |
| Un chiffre non décomposable | Le décomposer ou le retirer |
| Un critère d'acceptation coché sans preuve | Fournir la preuve ou décocher |
| De la prose à la place du format | Reformater |
