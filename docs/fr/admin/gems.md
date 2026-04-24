# Gestion des gems

Un **Gem** est une tâche d'IA réutilisable avec un objectif fixe. Les utilisateurs voient les gems sous forme de cartes sur l'écran d'accueil et remplissent un court formulaire pour les exécuter.

## Créer un gem

1. Ouvrez l'onglet **Gems** dans le panneau d'administration.
2. Cliquez sur **Nouveau gem**.
3. Remplissez le formulaire :

| Champ | Ce qu'il fait |
|---|---|
| **Nom** | Affiché sur la carte du gem. Restez court et descriptif. |
| **Description** | Facultatif. Une indication en une ligne affichée sous le nom. |
| **Teinte** | La couleur de l'icône du gem. Utilisez différentes couleurs pour distinguer facilement les gems d'un coup d'œil. |
| **Modèle de prompt** | L'instruction pour l'IA. Utilisez des espaces réservés `{{ variable_name }}` pour les champs que l'utilisateur remplit. |
| **Capacités** | Cochez *Accepte une image en entrée* si la tâche nécessite une photo ou une capture d'écran. |
| **Mode de sortie** | *Texte* pour une sortie ordinaire ; *Structuré (JSON)* pour une sortie lisible par machine. |
| **Accès aux documents** | Quels dossiers de documents ou fichiers individuels l'IA peut lire lors de l'exécution de ce gem. |

4. Cliquez sur **Créer**.

## Rédiger un bon modèle de prompt

Le modèle est l'instruction que l'IA reçoit. Il peut inclure n'importe quel texte, plus des espaces réservés :

```
Résumez le texte suivant en {{ language }}, en utilisant au maximum 5 points :

{{ text }}
```

Cela crée deux champs de saisie pour l'utilisateur : *language* et *text*.

**Conseils :**

- Soyez précis. Indiquez à l'IA exactement le format que vous souhaitez.
- Précisez la langue de sortie attendue si c'est important.
- Gardez les instructions courtes — le modèle fonctionne mieux avec des prompts clairs et concis.
- Testez le gem vous-même avant de le partager avec les utilisateurs.

## Accès aux documents

Chaque gem peut avoir accès à une partie de la bibliothèque de documents via l'arborescence de dossiers et de documents dans le formulaire du gem :

- **Accès au dossier** — cochez la case à côté d'un nom de dossier. L'IA peut voir chaque document dans ce dossier, y compris les nouveaux ajoutés ultérieurement. Cocher un dossier coche automatiquement tous les documents à l'intérieur.
- **Accès à un document individuel** — développez un dossier et cochez uniquement les documents spécifiques souhaités. Un dossier avec certains documents mais pas tous cochés affiche un indicateur partiel (−).
- **Aucun accès** (par défaut) — laissez toutes les cases décochées. L'IA n'utilise pas la bibliothèque de documents pour ce gem.

Lorsqu'un gem a accès aux documents, l'IA décide elle-même si elle doit consulter les documents ou répondre à partir de ses propres connaissances.

## Modifier et supprimer

Cliquez sur **Modifier** à côté d'un gem pour changer ses paramètres. Cliquez sur **Supprimer** pour le retirer définitivement. Il n'y a pas d'annulation.

!!! warning "Supprimer un gem"
    Les gems supprimés ne peuvent pas être récupérés. Les utilisateurs qui tentent d'ouvrir l'URL d'un gem supprimé verront une erreur.
