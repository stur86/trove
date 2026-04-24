# Présentation de l'administration

Le panneau d'administration est accessible uniquement depuis la machine exécutant Trove. Ouvrez `http://localhost:7770/admin` dans un navigateur sur cette machine et connectez-vous avec les identifiants définis lors de la configuration.

!!! warning "L'accès administrateur est limité à localhost"
    La connexion administrateur est intentionnellement masquée pour tous les autres appareils du réseau. Il s'agit d'une mesure de sécurité. Pour gérer Trove, vous devez être physiquement présent au serveur ou utiliser un tunnel SSH.

## Les quatre onglets

| Onglet | Ce que vous pouvez faire |
|---|---|
| **Paramètres** | Choisir le modèle d'IA, définir la taille de la fenêtre de contexte, changer la langue d'affichage |
| **Documents** | Téléverser des fichiers, les organiser en dossiers, consulter les résumés générés par l'IA |
| **Gems** | Créer, modifier et supprimer des gems |
| **Journaux** | Afficher les 1 000 dernières lignes du journal du serveur, actualisé automatiquement toutes les 5 secondes |

## URL du réseau local

L'onglet Paramètres affiche l'**URL du réseau local** — l'adresse que les autres appareils doivent utiliser pour accéder à Trove. Copiez-la et partagez-la avec vos utilisateurs.

## Étapes suivantes

- [Installation](installation.md)
- [Gestion des gems](gems.md)
- [Gestion des documents](documents.md)
- [Référence des paramètres](settings.md)
