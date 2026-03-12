---
description: "Un **étage** regroupe les pièces d'un bâtiment et fournit un index de niveau pour l'identification des équipements."
---

Un étage appartient à un bâtiment et contient une ou plusieurs pièces. Son slug et son nom sont utilisés pour composer les identifiants des équipements — un niveau numérique (ex : `1`, `2`) ou un libellé court (ex : `rdc`, `sous-sol`) fonctionnent bien.

## Champs

| Champ | Requis | Notes |
|---|---|---|
| `name` | ✅ | Nom affiché de l'étage (ex : "Rez-de-chaussée", "1er Étage") |
| `slug` | ✅ | Utilisé dans les identifiants — préférez un code de niveau court (ex : `0`, `1`, `rdc`) |
| `description` | — | Description libre optionnelle |
| `image` | — | URL HTTP/HTTPS vers un plan d'étage ou une image représentative |

## Impact sur les identifiants des équipements

Le slug de l'étage apparaît comme segment `{niveau}` dans tous les identifiants :

```
MQTT     : {préfixe}/{niveau}/{pièce}/{fonction}/{position}
Hostname : {niveau}_{pièce}_{fonction}_{position}
```

> **Conseil :** Utilisez des slugs numériques pour les étages si possible (`0`, `1`, `2`) — ils sont sans ambiguïté et se trient naturellement dans les listes et explorateurs de topics MQTT.
