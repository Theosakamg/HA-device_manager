---
description: "**Opérations irréversibles** — à utiliser avec une extrême prudence."
---

La Zone de Danger contient deux actions destructives qui ne peuvent pas être annulées. Exportez toujours vos données en premier.

## Nettoyer la Base de Données

Supprime définitivement **toutes les données** dans chaque table — équipements, pièces, étages, bâtiments, modèles, firmwares et fonctions. La boîte de confirmation exige de saisir une phrase spécifique pour éviter toute exécution accidentelle.

**Cas d'usage :** remise à zéro complète pour une nouvelle installation ou la purge d'un environnement de test.

## Vider le Cache IP

Réinitialise le champ `ip` de **tous les équipements** à `NULL`. Les enregistrements des équipements sont conservés ; seules les adresses IP sont effacées.

**Cas d'usage :** après un changement de réseau majeur (nouveau sous-réseau, nouvelle plage DHCP) où toutes les IP stockées sont invalides. Enchaînez avec un **Scanner le Réseau** pour les repeupler.

---

> ⚠️ **Exportez toujours avant toute opération en Zone de Danger.** Il n'y a pas d'annulation.
