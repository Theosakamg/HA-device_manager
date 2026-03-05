---
description: "Gérez les **données de référence** utilisées pour classifier et configurer vos équipements."
---

La section Paramètres centralise les trois briques de base auxquelles chaque équipement doit être rattaché avant de pouvoir être entièrement configuré ou déployé.

## Les trois onglets de référence

| Onglet | Rôle |
|---|---|
| **Modèles** | Modèles matériels — standardise la configuration des équipements identiques |
| **Firmwares** | OS / type de logiciel — utilisé pour filtrer les équipements lors des déploiements |
| **Fonctions** | Rôle fonctionnel — détermine directement les topics MQTT, hostnames et FQDNs |

> **L'ordre est important :** renseignez les Modèles, Firmwares et Fonctions *avant* d'ajouter des équipements ou de lancer un import, sous peine d'erreurs sur les références inconnues.
