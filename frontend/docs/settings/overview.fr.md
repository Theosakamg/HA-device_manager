---
description: "Gérez les **données de référence** utilisées pour classifier et configurer vos équipements."
---

La section Paramètres centralise les trois briques de base auxquelles chaque équipement doit être rattaché avant de pouvoir être entièrement configuré ou déployé.

## Les trois onglets de référence

| Onglet | Rôle |
|---|---|
| **Modèles** | Modèles matériels — standardise la configuration des équipements identiques |
| **Firmwares** | OS / type de logiciel — utilisé pour filtrer les équipements lors des déploiements. Le flag **Déployable** contrôle quels firmwares apparaissent dans le modal de déploiement |
| **Fonctions** | Rôle fonctionnel — détermine directement les topics MQTT, hostnames et FQDNs |

> **L'ordre est important :** renseignez les Modèles, Firmwares et Fonctions *avant* d'ajouter des équipements ou de lancer un import, sous peine d'erreurs sur les références inconnues.

## Compteurs en temps réel

Chaque onglet affiche un **badge de compteur** synchronisé avec les statistiques système. Ces compteurs sont optimisés pour minimiser la charge réseau — une seule requête API charge les trois compteurs simultanément.

## Filtrer les équipements depuis les Paramètres

Chaque ligne d'un onglet de paramètres dispose d'un bouton 🔍. En cliquant dessus, vous accédez à la vue **Équipements** avec un **filtre colonne Excel** pré-appliqué sur la colonne correspondante (ex. cliquer sur 🔍 à côté du firmware "Tasmota" filtre le tableau pour n'afficher que les équipements Tasmota). Le badge de filtre est visible et peut être effacé normalement.
