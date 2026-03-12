---
description: "Configurez les **préfixes réseau, domaines et paramètres de provisioning** utilisés dans toute l'application."
---

Ces paramètres définissent les conventions de nommage globales et les configurations de déploiement appliquées automatiquement au calcul des identifiants des équipements et aux opérations de provisioning. Toute modification est immédiate — aucun redémarrage requis.

## Paramètres réseau & nommage

| Champ | Exemple | Effet |
|---|---|---|
| **Préfixe IP** | `192.168.0` | Préfixé aux IP numériques courtes — `42` devient `192.168.0.42` |
| **Suffixe DNS** | `domo.local` | Ajouté au hostname pour construire le FQDN |
| **Préfixe MQTT** | `home` | Premier segment de chaque topic MQTT |
| **Bâtiment par défaut** | `Maison` | Bâtiment attribué aux équipements importés sans colonne bâtiment explicite |

## Paramètres de provisioning

Ces paramètres sont utilisés lors du déploiement automatique de firmwares sur vos équipements :

| Champ | Usage |
|---|---|
| **SSH Key File** | Chemin vers la clé privée SSH pour accéder aux équipements |
| **SSH User / Host** | Identifiants pour les connexions SSH distantes |
| **Device Password** | Mot de passe par défaut pour les nouveaux équipements |
| **WiFi SSID / Password** | Identifiants WiFi configurés lors du provisioning |
| **Bus Host / Port** | Adresse du broker MQTT (généralement `mosquitto:1883`) |
| **Bus Username / Password** | Identifiants pour se connecter au broker MQTT |
| **NTP Server** | Serveur NTP pour la synchronisation horaire |
| **Bridge Host** | Adresse du pont Zigbee2MQTT si utilisé |

## Impact sur les identifiants

```
Hostname : {niveau}_{pièce}_{fonction}_{position}
FQDN     : {hostname}.{suffixe_dns}
MQTT     : {préfixe_mqtt}/{niveau}/{pièce}/{fonction}/{position}
```

> **Conseil :** Modifier le suffixe DNS ou le préfixe MQTT ne renomme pas les topics MQTT retenus dans votre broker — vous devrez peut-être les purger manuellement. Les paramètres de provisioning sont stockés de manière sécurisée et ne sont accessibles qu'à l'API backend.
