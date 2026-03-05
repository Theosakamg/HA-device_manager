---
description: "Définissez les **modèles matériels** utilisés dans votre installation."
---

Chaque équipement doit être rattaché à un modèle, ce qui permet de standardiser sa configuration. Le champ *Template* (optionnel) stocke une config partagée (ex : YAML ESPHome) pour tous les équipements du même modèle.

## Pourquoi utiliser les modèles ?

- **Standardisez** les configurations d'équipements identiques
- **Simplifiez** les imports CSV avec des noms de modèles cohérents
- **Partagez** un template commun pour la gestion en masse

## Champ Template

Le champ `template` est du texte libre — utilisez-le pour stocker un fragment YAML, un profil JSON, ou toute configuration commune à ce modèle. Lors d'un **déploiement**, ce template peut être injecté comme configuration de base pour chaque équipement ciblé.

> **Astuce :** Utilisez des noms de modèles courts et compatibles machines (ex : `esp32-cam`, `sonoff-basic`) pour obtenir des topics MQTT et des hostnames propres.
