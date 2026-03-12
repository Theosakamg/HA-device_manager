---
description: "Inventaire complet de tous les appareils enregistrés dans votre infrastructure."
---

Cette vue est l'inventaire central de tous les appareils gérés par Device Manager, quelle que soit leur localisation physique.

Chaque ligne représente un appareil avec ses attributs principaux :

- **Statut** — actif ou désactivé (point coloré)
- **Adresse MAC** — identifiant matériel unique
- **Étage / Pièce** — emplacement physique dans la hiérarchie
- **Fonction** — le rôle de l'appareil (ex. interrupteur, capteur, lumière)
- **Position** — l'emplacement nommé dans la pièce
- **Firmware / Modèle** — le profil matériel et logiciel
- **Statut déploiement** — résultat du dernier déploiement (✓ Succès / ✗ Échec / Jamais)
- **Dernier déploiement** — horodatage de la dernière tentative de déploiement

## Recherche et filtre

Deux systèmes de filtrage sont disponibles et peuvent être combinés :

### Recherche textuelle
La barre de recherche en haut à droite filtre les appareils sur tous les champs visibles (MAC, IP, pièce, étage, modèle, firmware, fonction, données extra, statut déploiement).

### Filtres par colonne (style Excel)
Chaque en-tête de colonne dispose d'un bouton **▾** qui ouvre un menu déroulant listant toutes les valeurs distinctes de cette colonne. Sélectionnez une ou plusieurs valeurs — seules les lignes correspondant à **tous** les filtres actifs sont affichées.

- Un **champ de recherche** dans chaque menu permet de trouver rapidement une valeur dans les listes longues.
- Les filtres actifs apparaissent sous forme de **badges** sous le panneau de documentation.
- Chaque badge dispose d'un **✕** individuel pour supprimer ce filtre.
- Le bouton **✕ Effacer les filtres** supprime tous les filtres colonne en une fois.
- Le bouton **🔗 Partager** copie une URL avec tous les filtres actifs encodés — collez-la pour restaurer exactement la même vue.
- Les filtres sont **persistés en sessionStorage** : naviguer ailleurs puis revenir restaure votre dernier état de filtre.

> **Astuce :** En cliquant sur le bouton 🔍 à côté d'un firmware, modèle ou fonction dans la vue **Paramètres**, vous arrivez ici avec le filtre colonne correspondant déjà appliqué.

## Colonnes de statut déploiement

| Colonne | Description |
|---|---|
| **Statut déploiement** | Badge indiquant le résultat du dernier déploiement : ✓ *Succès* (vert), ✗ *Échec* (rouge), ou *Jamais* (gris) |
| **Dernier déploiement** | Horodatage local de la dernière tentative de déploiement (mis à jour automatiquement) |

Ces champs sont **en lecture seule** — ils sont mis à jour automatiquement après chaque déploiement et ne peuvent pas être modifiés manuellement.

## Actions

- **+ Ajouter** — enregistrer un nouvel appareil manuellement
- **🚀 Déployer** — ouvrir le panneau de provisionnement pour pousser un firmware ou une configuration sur un ou plusieurs appareils
- **Modifier** (ligne) — mettre à jour les informations de l'appareil
- **Supprimer** (ligne) — retirer définitivement l'appareil du registre
