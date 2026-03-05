---
description: "Téléchargez un **snapshot complet** de tous vos équipements dans le format de votre choix."
---

L'export produit un fichier unique contenant tous les équipements avec l'ensemble de leurs champs (MAC, IP, modèle, firmware, fonction, pièce, position, topic MQTT, hostname, FQDN, etc.).

## Formats

| Format | Usage idéal |
|---|---|
| **CSV** | Édition tableur, ré-import après modification en masse |
| **JSON** | Intégration API, scripting, sauvegarde |
| **YAML** | Fichiers de config lisibles, workflows GitOps |

## Workflow recommandé

1. **Exporter en CSV** avant toute opération en masse
2. Éditer le fichier dans votre tableur
3. **Ré-importer** via la section Import pour appliquer les modifications

> **Avant la Zone de Danger :** exportez toujours en premier — c'est votre seule option de rollback.
