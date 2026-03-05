---
description: "Créez des équipements en masse depuis un **fichier CSV** — la façon la plus rapide de peupler l'inventaire."
---

L'importeur CSV lit un fichier structuré et crée ou met à jour les équipements ligne par ligne. Les références aux modèles, firmwares, fonctions, pièces, étages et bâtiments sont résolues par nom — assurez-vous que ces entités de référence existent dans les Paramètres avant de lancer un import.

## Colonnes CSV attendues

| Colonne | Requis | Notes |
|---|---|---|
| `name` | ✅ | Nom affiché de l'équipement |
| `mac` | ✅ | Adresse MAC (tout séparateur) |
| `model` | ✅ | Doit correspondre à un nom de modèle existant |
| `firmware` | ✅ | Doit correspondre à un nom de firmware existant |
| `function` | ✅ | Doit correspondre à un nom de fonction existant |
| `building` | — | Utilise le bâtiment par défaut de la Configuration si absent |
| `floor` | — | Étiquette d'étage dans le bâtiment |
| `room` | — | Étiquette de pièce dans l'étage |
| `position_name` | — | Libellé de position lisible |
| `ip` | — | Adresse IP statique optionnelle |
| `enabled` | — | `true` / `false` (défaut : `true`) |

## Conseils

- Utilisez **Export → CSV** pour obtenir un template valide avec toutes les colonnes
- Les lignes avec des références non résolues sont ignorées et listées dans le rapport d'erreurs
- L'import est **additif** — les équipements existants ne sont pas modifiés
