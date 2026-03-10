---
description: "Scanne le réseau local pour **découvrir les équipements connectés** et rafraîchir leurs adresses IP."
---

Le scanner réseau exécute un **script bash configurable** (configuré dans Système → Commun) pour découvrir les correspondances MAC-IP sur votre réseau. Le script peut interroger des serveurs DHCP, des routeurs, ou effectuer des scans ARP. Lorsqu'une adresse MAC correspond à un équipement connu, l'IP est mise à jour directement dans la base de données.

## Fonctionnement

1. Le backend exécute le script de scan configuré (stocké dans les paramètres DB)
2. Le script retourne du YAML au format : paires `ip: mac`
3. Chaque adresse MAC est comparée aux équipements de la base
4. Les équipements correspondants voient leur champ `ip` mis à jour
5. Le résumé indique combien d'adresses ont été résolues

## Configuration du script

Le contenu du script de scan est configuré dans **Système → Commun → Script de scan réseau**. Variables d'environnement disponibles :
- `$SCAN_SCRIPT_SSH_USER` - Nom d'utilisateur SSH pour les requêtes distantes
- `$SCAN_SCRIPT_SSH_HOST` - Hôte SSH (routeur/serveur DHCP)
- `$SCAN_SCRIPT_PRIVATE_KEY_FILE` - Chemin du fichier de clé SSH

## Quand l'utiliser

- Après un renouvellement de bail DHCP qui a déplacé des équipements sur de nouvelles IP
- Après l'ajout de nouveaux équipements sur le réseau
- Périodiquement pour maintenir les IP à jour pour les opérations de déploiement
- Avant un déploiement massif pour s'assurer que les adresses IP sont correctes

> **Prérequis :** Configurez le **Script de scan réseau** dans Système → Commun et assurez-vous que les identifiants SSH sont valides si votre script nécessite un accès distant à un serveur DHCP ou routeur.
