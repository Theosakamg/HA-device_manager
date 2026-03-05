---
description: "Définissez les **rôles fonctionnels** de vos équipements (ex : lumière, volet, bouton, capteur)."
---

Chaque équipement doit être rattaché à une fonction — ce choix **impacte directement** les identifiants générés.

## Identifiants générés

| Identifiant | Motif |
|---|---|
| **Topic MQTT** | `{prefix}/{niveau}/{pièce}/{fonction}/{position}` |
| **Hostname** | `{niveau}_{pièce}_{fonction}_{position}` |
| **FQDN** | `{hostname}.{suffixe_dns}` |

## Pourquoi des fonctions cohérentes ?

- **Sécurité MQTT par ACL** : définissez des règles ACL par pattern de topic (ex : autoriser `light/#` uniquement pour les contrôleurs d'éclairage)
- **Filtrage par groupe** : ciblez rapidement tous les équipements "volet" dans un déploiement
- **Identifiants lisibles** : hostnames et topics MQTT auto-documentés dans votre réseau

## Bonnes pratiques

- Utilisez des noms courts, en minuscules et au singulier : `light`, `shutter`, `button`, `sensor`, `camera`
- Évitez les caractères spéciaux — la fonction fait partie des hostnames et des topics MQTT
- Définissez les fonctions de manière large (par rôle) plutôt qu'étroite (par modèle)

> **Exemple :** Un équipement Sonoff contrôlant un volet roulant → fonction `shutter`  
> → Topic MQTT : `home/1/salon/shutter/gauche`
