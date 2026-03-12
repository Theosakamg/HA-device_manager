---
description: "Définissez les **firmwares** (OS / type de logiciel) embarqués sur vos équipements."
---

Chaque équipement doit être rattaché à un firmware, utilisé ensuite lors des **déploiements** pour sélectionner et filtrer les équipements ciblés.

## Champs

| Champ | Description |
|---|---|
| **Nom** | Identifiant unique du firmware (utilisé comme clé dans les workflows de provisioning) |
| **Déployable** | Quand activé, ce firmware apparaît dans le modal de déploiement comme cible valide. Désactivez-le pour les firmwares utilisés uniquement à des fins de classification mais qui ne doivent jamais être déployés directement |
| **Activé** | Indique si ce firmware est disponible pour être assigné aux équipements |

## Pourquoi suivre les firmwares ?

- **Filtrez** les équipements par firmware lors du déploiement
- **Regroupez** les équipements par type d'OS pour des mises à jour cohérentes
- **Contrôlez** quels firmwares peuvent être ciblés par les déploiements via le flag `Déployable`
- Maintenez cette liste à jour pour des **opérations de déploiement fiables**

## Le flag Déployable

Seuls les firmwares avec **Déployable = activé** apparaissent dans la liste de sélection du modal de déploiement. Cela vous permet de conserver des firmwares de référence (ex. `zigbee`, `esphome`) dans le catalogue pour la classification et le filtrage, tout en évitant des tentatives de déploiement accidentelles sur des types de firmware qui ne supportent pas le provisioning distant.

## Types de firmware courants

| Firmware | Description |
|---|---|
| `tasmota` | Équipements ESP8266/ESP32 sous Tasmota |
| `esphome` | Équipements ESP gérés via ESPHome |
| `wled` | Contrôleurs LED sous WLED |
| `zigbee` | Équipements Zigbee (gérés par le coordinateur) |
| `zigbee2mqtt` | Équipements Zigbee connectés via Zigbee2MQTT |

> **Astuce :** Le nom du firmware est utilisé comme clé dans les workflows de provisioning. Utilisez des minuscules et soyez cohérent avec vos scripts de déploiement.
