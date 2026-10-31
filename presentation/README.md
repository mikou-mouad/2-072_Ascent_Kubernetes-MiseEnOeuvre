# La présentation

76 slides : pour chaque chapitre, l'incident chez FestiPass, la solution, le concept (schémas et YAML), puis le TP.
Les pauses, les déjeuners, les débuts et fins de journée suivent les horaires de `programme-3-jours.md`
(9h00 – 12h30, 13h30 – 16h30, pauses à 10h30 et 15h00).

## Présenter

Ouvrez `index.html` dans un navigateur.

| Touche | Action |
|--------|--------|
| → / Espace / clic | slide suivante |
| ← | slide précédente |
| Début / Fin | première / dernière slide |
| N | afficher les notes du formateur |
| F | plein écran |

Les polices viennent de Google Fonts : sans Internet, le navigateur utilise des polices de remplacement.
Les icônes sont remplacées par des symboles simples.

## Les fichiers

- `deck.json` : l'ordre des slides et les chapitres
- `slides/<id>.html` : une slide par fichier (1920 × 1080, styles en ligne), avec les notes du formateur dans `<aside>`
- `construire.py` : assemble `index.html` à partir des slides

Après une modification d'une slide :

```bash
python presentation/construire.py
```

## La charte

| Usage | Couleur |
|-------|---------|
| Fond sombre (incidents, couverture, fins de journée) | bleu marine `#1D3557` |
| Accent principal | corail `#E76F51` (pauses café) |
| Accent sur fond sombre | jaune `#FFD166` |
| Fonds clairs | sable `#F6F1E9`, `#FBF8F3`, cartes `#EFE6D8` |
| Concept, TP | turquoise `#2A9D8F`, slides TP et déjeuners `#264653` |
| Code | fond `#14212E`, surlignage `#FFD166` et `#8FC1F0`, commentaires `#8A9BAD` |
