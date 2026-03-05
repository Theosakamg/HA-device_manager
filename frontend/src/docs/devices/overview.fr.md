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

## Recherche et filtre

Utilisez la barre de recherche pour filtrer par n'importe quel champ visible : MAC, IP, pièce, étage, modèle, firmware, fonction ou données extra. Lorsque vous arrivez ici depuis une autre vue (ex. en cliquant sur une fonction dans Réglages), le filtre est pré-rempli — utilisez **✕ Effacer le filtre** pour le réinitialiser.

## Actions

- **+ Ajouter** — enregistrer un nouvel appareil manuellement
- **🚀 Déployer** — ouvrir le panneau de provisionnement pour pousser un firmware ou une configuration sur un ou plusieurs appareils
- **Modifier** (ligne) — mettre à jour les informations de l'appareil
- **Supprimer** (ligne) — retirer définitivement l'appareil du registre
