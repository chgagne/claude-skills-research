# Analyse et plan d'amélioration des skills de recherche (2026-10-12)

Analyse des traces des protocoles A, B, B2 (surveying-literature) et C (verifying-bibliography).
Aucun run nouveau ; seules les traces existantes et des requêtes gratuites (arXiv, Crossref) ont
servi. Les chiffres par run sont des moyennes sur B2 sauf mention.

## Correction (2026-10-12, après les 7 premiers cas de l'étape 0)

**Le constat 4 et le levier A étaient faux.** Le décompte « une recherche par tour, 598 sur 598 »
comptait les événements du flux `stream-json`, qui émet un événement par bloc de contenu ;
regroupés par identifiant de message, les runs v2 lancent déjà leurs recherches par 4 à 6 dans
un même message. Le groupement n'avait aucune marge, et la v3 (groupée par 4) ne coûte que 9 % de
moins que la v2 sur le dev.

Mesure correcte, sur l'événement final `result` (`modelUsage`) des 80 runs de B2 :
**coût d'un run = 0,36 $ + 0,108 $ par recherche web (R² = 0,99)**. Chaque appel `WebSearch` est
un appel modèle séparé (environ 14 K tokens d'entrée non mis en cache, sa sortie et les frais de
recherche). La skill elle-même ajoute 0,05 $. Avec skill : 19 recherches par run ; sans : 5,4.
Le seul levier de coût est donc le **nombre de recherches web**, et la v3 en fait encore autant
que la v2 parce que sa vérification de chaque candidat passe elle aussi par `WebSearch`.

Levier A remplacé par A' : **8 recherches web de découverte, et la vérification des candidats
par des requêtes gratuites (Crossref, arXiv, DBLP) en un seul appel Bash**. Coût attendu :
0,36 + 8 × 0,108 ≈ 1,2 $ par run (contre 2,42 $), soit 50 % de la v2, sous le seuil de 55 %.

## 1. Ce que les mesures disent

### 1.1 surveying-literature

| | sans skill | avec skill (d6d64fa) |
|---|---|---|
| Rappel@30, clés hors mémoire, B2 (B) | 0,20 (0,34-0,40) | 0,26 (0,52) |
| Messages par run | 15 | 29 |
| Recherches web par run | 5 | 15 (jamais plus d'une par tour : 598 sur 598) |
| Tokens relus en cache par run | 0,40 M | 1,04 M |
| Tokens créés en cache par run | 74 K | 198 K |
| Tokens produits par run | 146 | 377 |
| Coût par run | 0,94 $ | 2,42 $ |
| Script `run-survey.py` exécuté | - | 0 run sur 80 (0 sur 120 en B) |

Sept constats :

1. **Le plafond est commun aux deux bras.** En B2, 18 des 25 références clés hors mémoire ne sont
   trouvées par aucun bras dans aucun run (B : 8 sur 20). Les 18 : 7 prépublications de 2026
   (voisines par le sujet, indexées tard), 6 classiques d'avant 2015 (Sprecher 1965, Macchi 1975,
   Magma 1997, Parsopoulos 2005...), 2 citations d'outils, 3 articles de 2021-2025. La skill ne
   perd presque jamais ce que l'agent nu trouve (1 paire discordante sur 12) ; elle n'atteint pas
   non plus ce qu'il rate.
2. **Rendements décroissants rapides.** En B, 74 % des trouvailles de la skill apparaissent dans
   les 6 premières recherches, 84 % dans les 9 premières ; en B2, 11 sur 12 dans les 3 premières.
   Sans skill, tout vient des 6 premières. Les recherches 10 à 15 rapportent 5 trouvailles sur 43
   au total.
3. **Ce qui trouve, c'est la précision, pas le volume.** Sur les 19 requêtes qui ont fait
   remonter une référence difficile, 16 nomment une méthode concurrente, un acronyme ou un auteur
   (ECP, BFGAN, FEBP, RL-DAS, KeplerAgent, « Sutton Whitley Howe »...). Les requêtes génériques
   « ... 2025 2026 arXiv » prescrites par la skill en ont produit 3. La valeur vient de l'étape 2
   (lister de mémoire les méthodes proches) transformée en recherches, pas de l'étape 3 telle
   qu'écrite.
4. **[Faux, voir la correction ci-dessus.] Le coût est un coût de tours, pas de réflexion.** 377 tokens produits par run ; tout le reste
   est la relecture du contexte (brouillon lu par `head`/`sed`, 15 résultats de recherche de 3 à
   5 K caractères chacun) à chaque message. Coût ≈ taille du contexte × nombre de tours. Une
   recherche par tour est le facteur unique qui double le coût.
5. **Le script et ses cinq moteurs sont du poids mort en pratique.** Aucun run ne l'a lancé, aucun
   `WebFetch` vers S2, arXiv, Crossref ou DBLP. Le gain mesuré vient des 12 requêtes `WebSearch`.
   Tout ce que le SKILL.md consacre au script (sections « Run it », « Where candidates come
   from », « Five engines », « Grading », « When a source is down » : 8 des 12 KB) n'influence pas
   le résultat.
6. **Les rangs ne limitent rien.** Les trouvailles sont aux rangs 1 à 6, deux au-delà de 10. Une
   liste de 15 candidats donnerait le même rappel.
7. **Le banc est propre mais faible.** Aucune référence retirée n'est encore nommée dans la prose
   (vérifié strictement). Mais 7 brouillons B2 sur 20 ont eu besoin de la règle de repli pour
   « clé » (citée une fois dans l'état de l'art), contre 1 sur 30 en A ; et 25 références hors
   mémoire ne détectent qu'un écart d'environ 20 points à p < 0,05. Le bassin n'est pas épuisé :
   141 candidats arXiv n'ont jamais été filtrés, 78 dans les bonnes catégories, soit environ 40
   brouillons admissibles de plus (le journal dit le contraire ; à corriger).

### 1.2 verifying-bibliography

| protocole C | sans skill | skill | self |
|---|---|---|---|
| Rappel / faux positifs | 1,00 / 0 | 1,00 / 0 | 1,00 / 0 |
| Messages par run | 6 | 6 | 6 |
| Coût par run | 0,22 $ | 0,27 $ | 0,31 $ |

L'agent nu interroge lui-même Crossref et arXiv par `curl` (5 appels Bash par run). Sur ces cas,
il n'y a rien à gagner ni en rappel ni en coût : la skill coûte 0,05 $ de plus pour le même
résultat. Un gain n'est mesurable que sur des cas que l'agent nu ne résout pas seul. Le matériel
existe localement : sur 3 398 références des 54 sources analysées, 810 (24 %) n'ont ni DOI ni
identifiant arXiv après recherche Crossref, dont 117 d'avant 2010 ; 12 sources citent 60 entrées
ou plus.

### 1.3 Moteurs gratuits sur les requêtes réelles de la skill

Test à coût nul : les requêtes `WebSearch` réellement émises par la skill en B2 (20 par brouillon,
11 brouillons) rejouées sur arXiv et Crossref (S2 écarté : 429 sur la clé dégradée), et une
recherche directe par titre pour savoir si la référence est indexée.

| 18 références jamais trouvées | |
|---|---|
| indexées dans arXiv ou Crossref (recherche par titre) | 14 |
| atteintes par les requêtes de la skill, top 20 d'un moteur | **2** (une au rang 2 de la 4e requête, une au rang 20 de la 15e) |

Les moteurs ne sont pas le goulot : les requêtes écrites ne décrivent pas ces références. Les 4
non indexées sont des prépublications de 2026 ; l'API arXiv a aussi rejeté 8 requêtes sur 440
(syntaxe), donc ce chiffre est approximatif. Un pipeline à moteurs gratuits avec les mêmes
requêtes rapporterait au plus 2 références sur 18, soit environ 2 points de rappel.

## 2. Leviers, classés par gain attendu sur coût

| | Levier | Gain attendu | Certitude | Coût de mise en œuvre |
|---|---|---|---|---|
| A | Grouper les recherches : 3 ou 4 appels `WebSearch` par tour | coût ÷ 2, rappel inchangé | haute (mécanique) | une phrase dans SKILL.md |
| B | 8 requêtes nommées au lieu de 12 dont 3 génériques | rappel ≥, coût ÷ 1,2 en plus | moyenne (constat 3, n = 19) | réécrire l'étape 3 |
| C | Candidats des moteurs gratuits remis à l'agent sous forme de titres (pipeline à deux étages) | ≈ +2 points (§1.3) ; coût ÷ 2 seulement si les pages web sortent du contexte | moyenne pour le coût, faible pour le rappel | script existant, nouvelle sortie courte |
| D | Retirer du SKILL.md ce qui n'est jamais exécuté | 3 K tokens par message, clarté | haute | réécriture, tests à adapter |
| E | Élargir et durcir le banc : 40 brouillons de plus, règle « clé » stricte seulement | puissance × 2,5 | haute | ~3 h de préparation, 60 % du coût d'une campagne |
| F | Banc bibliographique dur : entrées sans DOI, longues bibliographies | décide si la skill sert à quelque chose | haute | ~2 h, 15 $ |

Écarté : un modèle moins cher pour écrire les requêtes. La valeur vient de la mémoire du modèle
(constat 3) ; c'est précisément ce qu'un modèle plus petit a en moins. Écarté aussi : allonger la
liste de candidats ou le nombre de recherches (constats 2 et 6).

Projection si A, B et D tiennent : run avec skill à environ 12 messages et 0,45 M tokens relus,
soit 1,0 à 1,2 $ (contre 2,42 $), pour le même rappel de 0,26 à 0,40. La skill passerait de
2,6 fois à 1,2 fois le coût de l'agent nu.

## 3. Plan

Chaque étape a son protocole commité avant le premier run noté, une porte d'usage (40 % / 75 %),
2 runs par cas, le modèle `claude-opus-5-5` pour rester comparable à B et B2, et un critère de
passage écrit avant de lancer.

### Étape 0 : skill v3 sur le jeu de développement (surveying-literature)

- Écrire la v3 : étape 3 réécrite (8 requêtes, chacune nommant une méthode, un auteur ou un
  ingrédient technique associé au problème ; aucune requête composée seulement de mots-clés
  généraux et d'une année) ; étape 4 : « lance les requêtes par groupes de quatre dans un même
  tour » ; 15 candidats maximum ; sections du script réduites à un paragraphe « optionnel ».
- Mesurer sur les 10 brouillons de dev, 1 run par bras (≈ 25 $) : coût par run, messages,
  rappel hors mémoire.
- **Passage à l'étape 1 si** coût ≤ 55 % de la v2 et rappel hors mémoire ≥ v2 moins 2 points sur
  le dev. Sinon, garder A seul (le groupement) et passer à l'étape 1 avec cette version minimale.

### Étape 1 : protocole B3 sur 20 nouveaux brouillons

- Filtrer les 78 candidats non encore filtrés avec le pipeline B2 (`scrub_meta` compris), règle
  « clé » stricte uniquement (cités deux fois dans l'état de l'art), tirage à graine, sondes
  mémoire, plancher de 15 références clés hors mémoire.
- Bras : v3 contre sans skill, 2 runs ; en plus, 1 run de la v2 (d6d64fa) sur les mêmes
  brouillons pour mesurer v3 contre v2 directement (≈ 50 $ de plus).
- Coût : ≈ 100 $ avec la v3 moins chère, 10 à 12 % de la fenêtre de 7 jours.
- **Critère :** v3 ≥ sans skill + 6 points (l'estimation répliquée) à ≤ 1,3 fois le coût ;
  v3 ≥ v2 moins 3 points. Résultat secondaire : B, B2, B3 regroupés sous la règle par id.

### Étape 2 : pipeline à deux étages (reporté)

- Le §1.3 montre que les moteurs gratuits n'atteignent pas les références manquées avec les
  requêtes actuelles : au plus +2 points. L'étape ne vaut que comme réduction de coût (l'agent ne
  lit plus les pages de résultats) et seulement si les étapes 0 et 1 laissent le coût au-dessus de
  1,3 fois l'agent nu.
- L'agent écrit ses 8 requêtes dans un fichier ; `run-survey.py --angles-file` les passe aux
  moteurs (0 token) et imprime 40 titres dédupliqués avec année et identifiant ; l'agent les
  vérifie et classe sans jamais voir les pages de résultats web. Les 8 `WebSearch` restent pour
  ce que les moteurs n'indexent pas encore.
- Dev d'abord (étape 0 bis), même porte ; puis test sur les brouillons de B3 (v4 contre v3).

### Étape 3 : banc bibliographique dur (verifying-bibliography)

- Construire 6 bibliographies à partir des sources locales : 3 longues (60 à 190 entrées) et 3
  riches en entrées sans DOI ni arXiv. Planter 5 défauts par bibliographie, déterministes :
  pages ou année faussées dans une entrée sans DOI, coauteur inventé dans un vieil acte, entrée
  fabriquée imitant un atelier des années 2000, titre d'un vrai article attribué à un mauvais
  venue, prépublication citée alors qu'une version publiée existe.
- Bras : sans skill, skill, self ; 2 runs ; ≈ 15 $. Noter aussi la couverture : part des entrées
  réellement vérifiées (visible dans les traces) et le coût par entrée.
- **Lecture :** si l'agent nu reste à 1,00, la skill ne vaut que par son script (passe
  systématique) : la réduire à « lance le script, lis le rapport » et retirer le reste. Si l'agent
  nu décroche sur les longues bibliographies ou les entrées sans DOI, le gain est mesuré et la
  skill garde sa justification.

**Résultat (2026-10-23, protocoles D à D4).** L'agent nu reste à 1,00 sur les décalages de pages
plantés (13 après le filtre mémoire) : la skill a été réduite à son script. La première réduction
(D2) a perdu le suivi des entrées `WEAK` (22/26) ; sa remise en forme impérative (D3) a coûté
1,77 $ par run ; la version D4 (une passe Bash Crossref + DBLP groupée) tient 26/26 à 1,04 $.
Fusionnée et publiée (00dd1af). Détail : `verifying-bibliography/hard/RESULTS-D*.md`,
`journal/2026-10-23.md`.

### Hygiène de mesure, valable pour toutes les étapes

- Corriger dans `README.md` la phrase sur le bassin épuisé (§1.1, constat 7).
- Étiqueter dès la construction les références clés « strictes » et « de repli » et rapporter les
  deux ; le critère principal ne porte que sur les strictes.
- Vérifier dans les traces, pour chaque bras, le nombre de recherches par tour et l'exécution ou
  non du script ; un run qui n'a pas fait ce que la skill prescrit se compte mais se signale.
- Garder une analyse « première recherche qui fait apparaître la référence » (code de cette
  analyse à verser dans `_harness/`) : elle dit à chaque campagne combien de requêtes servent.

## 4. Ordre proposé et budget total

1. Étape 0 (dev, 25 $, une demi-journée) ; 2. étape 1 (100 à 150 $, une journée de runs derrière
la porte) ; 3. étape 3 en parallèle de l'étape 1 (15 $) ; 4. étape 2 seulement si le coût reste
trop haut après l'étape 1.
Total : environ 200 $ en équivalent API et 25 à 30 % de la fenêtre de 7 jours, étalés sur deux
semaines. Les décisions à prendre maintenant : valider les leviers A, B et D comme contenu de la
v3, et accepter que le banc B3 abandonne la règle de repli.

## Résultat de l'étape 0 (2026-10-12)

Dev, 10 brouillons, 1 run par bras (`private/v3dev/`, `analyze_step0.py`).

| Bras | Coût par run | Recherches facturées | Rappel hors mémoire | Rappel global |
|---|---|---|---|---|
| v2 (d6d64fa) | 2,48 $ | 19,7 | 4/23 | 30/60 |
| v3 (groupement par 4, 8 requêtes nommées ; 7 brouillons) | 2,27 $ | 18,9 | 3/20 | 18/42 |
| v3.1 (v3 + vérification par `lookup-titles.py`) | 1,59 $ | 11,5 | 2/23 | 30/60 |

**Critère non atteint** : coût v3.1/v2 = 0,64 (seuil 0,55) ; rappel hors mémoire −8,7 points
(seuil −2). La v3.1 suit la recette (8 appels `WebSearch` par 4, `lookup-titles.py` dans 10 runs
sur 10) ; un appel `WebSearch` déclenche 1,4 recherche côté serveur en moyenne. L'écart de rappel
tient à deux références que la v2 a trouvées à ses recherches 2 et 4 et pour lesquelles la v3.1
n'a pas écrit de requête ; la v2 avait obtenu 0,30 sur ces brouillons au dev de B contre 0,17
ici. Décision du 2026-10-12 : B3 mesure la v3.1, avec l'agent nu et la v2.

## Pas 0b (2026-10-15, écrit avant tout run) : v3.2 sur les brouillons de dev

B3 a mesuré les deux versions du skill sous l'agent nu sur les références que le modèle cite de
mémoire (clés connues : 0,83 contre 0,92 ; rappel global à 30 : 0,52 et 0,54 contre 0,59). La
v3.2 (branche `surveying-v32`, b22c2bc) fait de la liste de l'étape 2 des lignes de
`candidates.txt` et une partie de la réponse classée ; rien d'autre ne change.

Mesure : v3.2, 1 run par brouillon de dev (10 runs, environ 17 $), comparée aux runs existants
du pas 0 (v3.1) et aux runs « sans skill » du dev (`runs/dev-v2-skill-without`), rappel à 30
sous la règle id, `analyze.py --split dev`. Sur dev : 21 références clés connues de mémoire
(une vaut 4,8 points), 9 hors mémoire, 60 en tout.

| Mesure | sans skill | v3.1 (pas 0) | Seuil v3.2 |
|---|---|---|---|
| Clés connues de mémoire @30 | 0,833 | 0,810 | ≥ 0,833 (18 sur 21) |
| Toutes @30 | 0,542 | 0,500 | ≥ 0,542 |
| Clés hors mémoire @30 | 0,111 | 0,000 | rapporté, pas de seuil (9 références) |
| Coût par run | 0,73 $ | 1,59 $ | ≤ 1,75 $ (1,1 × v3.1) |

Les trois seuils tenus : v3.2 va en protocole B4 sur les 35 brouillons de B3 (bras v3.2 ×2,
comparé aux runs B3 existants de v3.1 et de l'agent nu, aucun run à refaire pour eux). Un seuil
manqué : la branche reste non fusionnée et la perte de rappel est traitée autrement.

### Résultat du pas 0b (2026-10-16)

| Mesure | sans skill | v3.1 | v3.2 | Seuil |
|---|---|---|---|---|
| Clés connues de mémoire @30 | 0,833 | 0,810 | 0,762 (16/21) | ≥ 0,833 : **manqué** |
| Toutes @30 | 0,542 | 0,500 | 0,483 | ≥ 0,542 : **manqué** |
| Clés hors mémoire @30 | 0,111 | 0,000 | 0,000 | rapporté |
| Coût par run | 0,73 $ | 1,59 $ | 1,58 $ | ≤ 1,75 $ : tenu |

v3.2 reste sur sa branche. Deux constats :

- **La consigne n'a pas été suivie.** Dans 8 runs sur 10, aucun `candidates.txt` n'est écrit
  avant les recherches : le fichier n'apparaît qu'à l'appel de `lookup-titles.py`, après les huit
  recherches, comme en v3.1. Une instruction en prose ne suffit pas à faire écrire la liste tôt.
- **Le dev ne peut pas trancher.** L'écart à combler sur dev est d'une demi-référence (agent nu
  0,833, v3.1 0,810) ; une référence vaut 4,8 points. La perte mesurée en B3 (0,92 contre 0,83)
  ne se voit que sur les 35 brouillons de test.

## Pas 0c (2026-10-27, écrit avant tout run) : v3.3, la liste de mémoire passée par le script

Choix du chercheur (2026-10-26) : correctif structurel plutôt que consigne. v3.3 (branche
`surveying-v33`, 6ffb40f) : `lookup-titles.py` exige `--memory memory.txt` (au moins 10 titres,
sinon il refuse), fusionne la liste de mémoire et les candidats de recherche (mémoire d'abord,
doublons fusionnés) et marque chaque ligne `[M]`, `[S]` ou `[M+S]` ; l'étape 6 demande de garder
dans la réponse chaque titre `[M]` non cité. Rien d'autre ne change.

Mesure : 10 runs de dev, 1 par brouillon, mêmes cas, octrois et limites que 0b, actifs v3.3
installés par le scaffold ; comparés aux runs existants (sans skill, v3.1, v3.2), `analyze.py
--split dev --rule id`. Le dev ne peut pas montrer le gain attendu (une demi-référence d'écart,
constat de 0b) : ce pas vérifie que le mécanisme fonctionne et ne coûte rien, B4 mesure le gain.

| Mesure | Seuil |
|---|---|
| Runs où `lookup-titles.py --memory` a tourné avec au moins 10 titres | ≥ 9 sur 10 |
| Titres `[M]` FOUND non cités présents dans la réponse finale | ≥ 90 % |
| Clés connues de mémoire @30 | ≥ 0,810 (v3.1, pas de régression) |
| Coût par run | ≤ 1,75 $ (1,1 × v3.1) |

Tous tenus : protocole B4 écrit ensuite (35 brouillons de B3, bras v3.3 ×2, 70 runs, environ
110 $, comparé aux runs B3 de v3.1 et de l'agent nu), lancé après accord du chercheur. Un seuil
manqué : diagnostic avec le chercheur, pas de B4.

### Résultat du pas 0c (2026-10-27)

| Mesure | sans skill | v3.1 | v3.3 | Seuil |
|---|---|---|---|---|
| `lookup-titles.py --memory` exécuté (≥ 10 titres) | - | - | 10/10 | ≥ 9 : tenu |
| Titres `[M]` FOUND non cités dans la réponse | - | - | 136/173 = 0,79 | ≥ 0,90 : **manqué** |
| Clés connues de mémoire @30 | 0,833 | 0,810 | **0,857** (18/21) | ≥ 0,810 : tenu |
| Toutes @30 | 0,542 | 0,500 | 0,533 | rapporté |
| Clés hors mémoire @30 | 0,111 | 0,000 | 0,111 | rapporté |
| Coût par run | 0,73 $ | 1,59 $ | **1,33 $** | ≤ 1,75 $ : tenu |

Le seuil manqué était mal posé : la consigne de réponse plafonne la liste à 30 entrées, et les
listes de mémoire comptaient jusqu'à 29 titres `[M]` FOUND non cités (moyenne 17) ; 9 réponses sur
10 ont exactement 30 entrées. Garder 90 % des `[M]` aurait évincé presque toutes les trouvailles de
recherche. L'étape 6 de v3.3 (« chaque titre `[M]` non cité reste dans la réponse ») entre en
conflit avec ce plafond de la même façon. Ce qui comptait pour le défaut visé, les clés connues de
mémoire, passe de 0,810 à 0,857, au-dessus de l'agent nu, pour un coût plus bas que v3.1. Selon la
règle écrite, pas de B4 sans diagnostic avec le chercheur.

## Pas 0d (2026-10-28, écrit avant tout run) : v3.4, la liste de mémoire couvre les fondations

B4 (RESULTS-B4.md) : v3.3 publiée (meilleure que v3.1 en mémoire et en coût) mais critère 1
manqué ; 23 des 25 références clés de mémoire perdues n'étaient jamais dans `memory.txt`, surtout
des travaux fondateurs. Choix du chercheur : publier v3.3, puis tester v3.4 sur dev. v3.4 (branche
`surveying-v34`, 347dab0) : l'étape 2 demande les articles que le brouillon devrait citer, en deux
groupes, les travaux les plus proches et les fondations sur lesquelles il s'appuie. Rien d'autre.

Mesure : 10 runs de dev comme 0c, comparés à v3.3 (0c) et à l'agent nu. Mesure ciblée :
`v3dev/memcov.py` (part des références clés de mémoire présentes dans `memory.txt` ; v3.3 sur dev
16/21 = 0,762, sur B4 136/166 = 0,819).

| Mesure | v3.3 (0c) | Seuil v3.4 |
|---|---|---|
| Références clés de mémoire dans `memory.txt` | 0,762 (16/21) | ≥ 0,857 (18/21) |
| Clés connues de mémoire @30 | 0,857 | ≥ 0,810 (une référence de marge) |
| Clés hors mémoire @30 | 0,111 | rapporté |
| Coût par run | 1,33 $ | ≤ 1,46 $ (1,1 × v3.3) |

Tous tenus : une mesure sur les 35 brouillons de B3 est proposée au chercheur (protocole B5, avec la
réserve que v3.4 est réglée sur le diagnostic de ces mêmes brouillons). Un seuil manqué : v3.4 reste
sur sa branche.

### Résultat du pas 0d (2026-10-28)

| Mesure | v3.3 (0c) | v3.4 | Seuil |
|---|---|---|---|
| Références clés de mémoire dans `memory.txt` | 0,762 (16/21) | 0,714 (15/21) | ≥ 0,857 : **manqué** |
| Clés connues de mémoire @30 | 0,857 | 0,714 | ≥ 0,810 : **manqué** |
| Toutes @30 | 0,533 | 0,450 | rapporté |
| Clés hors mémoire @30 | 0,111 | 0,111 | rapporté |
| Coût par run | 1,33 $ | 1,34 $ | ≤ 1,46 $ : tenu |

v3.4 reste sur sa branche. Demander aussi les fondations n'a pas fait entrer plus de références
clés dans la liste (médiane 28 titres contre 27) et a fait baisser le rappel : la liste s'allonge
de classiques que le brouillon cite déjà ou qui ne sont pas retirés, et ils prennent des places.
Un run (2609.35113) a lancé la recherche en arrière-plan et lu sa sortie dans un fichier, que le
détecteur ne voit pas ; ce n'est pas un refus. Sur dev, une référence vaut 4,8 points : l'écart
(trois références) est au-delà du bruit d'un seul run par brouillon, sans être grand. Fil 5 :
v3.3 publiée reste la version en place ; la perte restante est consignée dans SKILL.md.
