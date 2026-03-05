---
description: "Une **pièce** est le parent direct des équipements et le niveau le plus bas de la hiérarchie de localisation."
---

Une pièce appartient à un étage et contient des équipements. C'est le nœud le plus important opérationnellement — les topics MQTT, hostnames et FQDNs des équipements sont tous construits à partir du slug de la pièce. Les pièces supportent aussi des identifiants d'accès optionnels (login / mot de passe) pour les cas où une passerelle locale nécessite une authentification.

## Champs

| Champ | Requis | Notes |
|---|---|---|
| `name` | ✅ | Nom affiché (ex : "Salon", "Cuisine") |
| `slug` | ✅ | Utilisé dans chaque identifiant d'équipement de cette pièce |
| `description` | — | Description libre optionnelle |
| `image` | — | URL HTTP/HTTPS vers une photo ou découpe de plan |
| `login` | — | Identifiant optionnel stocké au niveau de la pièce |
| `password` | — | Mot de passe optionnel stocké au niveau de la pièce |

## Impact sur les identifiants des équipements

Le slug de la pièce apparaît comme segment `{pièce}` dans tous les identifiants :

```
MQTT     : {préfixe}/{niveau}/{pièce}/{fonction}/{position}
Hostname : {niveau}_{pièce}_{fonction}_{position}
```

> **Conseil :** Gardez les slugs de pièce courts et en minuscules sans caractères spéciaux (ex : `salon`, `cuisine`, `garage`) — ils font partie de chaque topic MQTT et hostname de la pièce.
