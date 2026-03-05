---
description: "Définissez les **firmwares** (OS / type de logiciel) embarqués sur vos équipements."
---

Chaque équipement doit être rattaché à un firmware, utilisé ensuite lors des **déploiements** pour sélectionner et filtrer les équipements ciblés.

## Pourquoi suivre les firmwares ?

- **Filtrez** les équipements par firmware lors du déploiement
- **Regroupez** les équipements par type d'OS pour des mises à jour cohérentes
- Maintenez cette liste à jour pour des **opérations de déploiement fiables**

## Types de firmware courants

| Firmware | Description |
|---|---|
| `tasmota` | Équipements ESP8266/ESP32 sous Tasmota |
| `esphome` | Équipements ESP gérés via ESPHome |
| `wled` | Contrôleurs LED sous WLED |
| `zigbee` | Équipements Zigbee (gérés par le coordinateur) |
| `zigbee2mqtt` | Équipements Zigbee connectés via Zigbee2MQTT |

> **Astuce :** Le nom du firmware est utilisé comme clé dans les workflows de provisioning. Utilisez des minuscules et soyez cohérent avec vos scripts de déploiement.
