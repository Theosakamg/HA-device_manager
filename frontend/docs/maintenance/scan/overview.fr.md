---
description: "Scanne le réseau local pour **découvrir les équipements connectés** et rafraîchir leurs adresses IP."
---

Le scanner réseau sonde le sous-réseau défini par le **Préfixe IP** dans la Configuration et tente de faire correspondre les hôtes découverts aux adresses MAC des équipements connus. Lorsqu'une correspondance est trouvée, l'IP de l'équipement est mise à jour automatiquement.

## Fonctionnement

1. Le backend itère sur la plage IP configurée
2. Chaque hôte joignable est interrogé pour son adresse MAC (ARP / mDNS)
3. Les équipements correspondants dans la base voient leur champ `ip` mis à jour
4. Le résumé indique combien d'adresses ont été résolues

## Optimisation réseau

Le scan réseau utilise un **cache IP local** pour éviter de rescanner inutilement les équipements déjà découverts. Le cache est stocké dans `cache_ip.yaml` et peut être réinitialisé depuis la Zone de Danger si nécessaire.

## Quand l'utiliser

- Après un renouvellement de bail DHCP qui a déplacé des équipements sur de nouvelles IP
- Après l'ajout de nouveaux équipements sur le réseau
- Périodiquement pour maintenir les IP à jour pour les opérations de déploiement
- Avant un déploiement massif pour s'assurer que les adresses IP sont correctes

> **Prérequis :** le **Préfixe IP** doit être configuré dans la section Configuration avant de scanner. Le scanner couvre uniquement le sous-réseau `/24` de ce préfixe.
