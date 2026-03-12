---
description: "Un **bâtiment** est le conteneur de plus haut niveau de votre hiérarchie de localisation."
---

Chaque équipement est finalement localisé dans un bâtiment. Un bâtiment regroupe un ou plusieurs étages et porte des métadonnées comme un slug (utilisé dans les identifiants générés), une description et une URL d'image optionnelle.

## Champs

| Champ | Requis | Notes |
|---|---|---|
| `name` | ✅ | Nom affiché du bâtiment |
| `slug` | ✅ | Identifiant court compatible machine — utilisé dans les topics MQTT et hostnames |
| `description` | — | Description libre visible dans le panneau de détail |
| `image` | — | URL HTTP/HTTPS vers une image représentative |

## Relations

```
Bâtiment
└── Étage (1…n)
    └── Pièce (1…n)
        └── Équipement (0…n)
```

> **Conseil :** Le slug du bâtiment se propage dans les identifiants des équipements — choisissez une valeur courte en minuscules (ex : `principal`, `annexe`) et évitez de le renommer une fois les équipements déployés.
