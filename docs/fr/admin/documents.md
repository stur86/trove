# Gestion des documents

La bibliothèque de documents vous permet de donner à l'IA accès aux fichiers de votre institution — politiques, manuels, fiches de référence — sans les intégrer dans les prompts des gems individuels.

## Téléverser un document

1. Ouvrez l'onglet **Documents** dans le panneau d'administration.
2. Sélectionnez un dossier de destination (ou créez-en un nouveau).
3. Cliquez sur **Téléverser** et choisissez un fichier.

Les formats pris en charge incluent PDF, Word (`.docx`), texte brut et la plupart des formats bureautiques courants. Trove convertit les fichiers téléversés en texte brut en interne à l'aide de [Markitdown](https://github.com/microsoft/markitdown). Le fichier original est conservé aux côtés de la version convertie.

Après le téléversement, l'IA génère automatiquement une description en une ligne du document. Cette description est affichée dans le panneau d'administration et utilisée lorsque l'IA décide quels documents consulter.

## Dossiers

Les documents sont organisés en dossiers. Les dossiers sont l'unité de contrôle d'accès : lorsque vous créez un gem, vous accordez l'accès à des dossiers entiers ou à des documents individuels à l'intérieur.

Pour créer un dossier, tapez un nom dans le champ **Nouveau dossier** et appuyez sur Entrée (ou le bouton d'ajout).

Pour renommer un dossier ou un document, cliquez sur son nom dans le panneau d'administration.

## Comment l'IA utilise les documents

Lorsqu'un gem a accès aux documents, Trove fournit à l'IA un résumé de tous les documents accessibles avant qu'elle commence. L'IA peut ensuite demander le texte complet de tout document qu'elle juge pertinent. Il n'y a pas de recherche vectorielle — l'IA raisonne à partir des résumés et récupère le contenu complet à la demande.

Cela signifie :
- **Les documents courts, bien nommés avec de bonnes descriptions** sont plus faciles à trouver et à utiliser pour l'IA.
- **Les documents très volumineux** peuvent être tronqués pour tenir dans la fenêtre de contexte du modèle.
- L'IA n'utilisera pas toujours les documents — elle les utilise uniquement lorsqu'ils semblent pertinents pour la demande de l'utilisateur.

## Télécharger des documents

Vous pouvez télécharger des documents individuels ou des dossiers entiers directement depuis l'onglet Documents.

- **Dossier** — cliquez sur l'icône de téléchargement (↓) à côté d'un nom de dossier pour recevoir une archive ZIP contenant la version Markdown convertie de chaque document dans ce dossier.
- **Document** — cliquez sur l'icône de téléchargement à côté d'un nom de document pour recevoir son fichier Markdown converti (`.md`).

Ces téléchargements contiennent la version en texte brut de chaque fichier tel que Trove le voit, pas le fichier original téléversé.

## Supprimer un document

Cliquez sur le bouton **Supprimer** à côté d'un document dans le panneau d'administration. Le fichier et ses métadonnées sont supprimés définitivement.
