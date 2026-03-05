---
description: "Configurez les **préfixes réseau et domaines par défaut** utilisés dans toute l'application."
---

Ces paramètres définissent les conventions de nommage globales appliquées automatiquement au calcul des identifiants des équipements. Toute modification est immédiate — aucun redémarrage requis.

## Champs

| Champ | Exemple | Effet |
|---|---|---|
| **Préfixe IP** | `192.168.0` | Préfixé aux IP numériques courtes — `42` devient `192.168.0.42` |
| **Suffixe DNS** | `domo.local` | Ajouté au hostname pour construire le FQDN |
| **Préfixe MQTT** | `home` | Premier segment de chaque topic MQTT |
| **Bâtiment par défaut** | `Maison` | Bâtiment attribué aux équipements importés sans colonne bâtiment explicite |

## Impact sur les identifiants

```
Hostname : {niveau}_{pièce}_{fonction}_{position}
FQDN     : {hostname}.{suffixe_dns}
MQTT     : {préfixe_mqtt}/{niveau}/{pièce}/{fonction}/{position}
```

> **Conseil :** Modifier le suffixe DNS ou le préfixe MQTT ne renomme pas les topics MQTT retenus dans votre broker — vous devrez peut-être les purger manuellement.
