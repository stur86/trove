# Paramètres

L'onglet **Paramètres** contrôle le modèle d'IA et les préférences d'affichage pour l'ensemble du serveur.

## Modèle d'IA

| Paramètre | Ce qu'il fait |
|---|---|
| **Modèle de base** | La variante Gemma 4 utilisée par Trove. Seuls les modèles déjà téléchargés apparaissent dans la liste. |
| **Fenêtre de contexte (num_ctx)** | La quantité de texte que le modèle peut tenir en mémoire à la fois, mesurée en tokens (environ ¾ d'un mot chacun). Des valeurs plus grandes gèrent des documents plus longs mais utilisent plus de RAM. |

Après avoir modifié le modèle ou la fenêtre de contexte, cliquez sur **Enregistrer et reconstruire** pour appliquer le changement. Trove reconstruit sa configuration interne du modèle ; cela prend environ 30 secondes et affiche la progression sur la page.

### Choisir un modèle

| Modèle | Paramètres effectifs | RAM minimale | Audio | Idéal pour |
|---|---|---|---|---|
| `gemma4:e2b` | 2,3B | ~4 Go | Oui | Machines très lentes, réponses les plus rapides |
| `gemma4:e4b` | 4,5B | ~6 Go | Oui | Équilibré — recommandé par défaut |
| `gemma4:26b` | 4B actifs (MoE) | ~10 Go | Non | Meilleure qualité, vitesse similaire à e4b |
| `gemma4:31b` | 31B dense | ~20 Go | Non | Qualité maximale, nécessite une machine puissante |

!!! tip "Gems audio et choix du modèle"
    Seuls `gemma4:e2b` et `gemma4:e4b` prennent en charge l'entrée audio. Si vous passez à un modèle sans support audio, les gems utilisant l'entrée audio seront masqués pour les utilisateurs jusqu'à ce que vous reveniez à un modèle avec prise en charge audio.

## Langue

Le sélecteur de **Langue** change la langue d'affichage de toute l'interface Trove, y compris l'écran d'accueil et le lanceur de gems côté utilisateur. Langues actuellement prises en charge : anglais, français, allemand, espagnol, portugais, chinois, italien.

## Données

La section **Données** vous permet de sauvegarder toute la configuration de Trove ou de restaurer une sauvegarde précédente.

### Exporter un bundle

Cliquez sur **Exporter le bundle** pour télécharger un fichier ZIP unique (`trove-bundle.zip`) contenant :

- Tous les gems et leurs paramètres.
- Tous les dossiers de documents, les métadonnées des documents et le texte converti de chaque document.

Utilisez ceci pour sauvegarder votre configuration avant d'effectuer de grands changements, ou pour copier une configuration vers une autre instance Trove.

### Importer un bundle

Cliquez sur **Importer le bundle** pour ouvrir la boîte de dialogue d'importation. Choisissez un fichier `.zip` exporté depuis n'importe quelle instance Trove, puis sélectionnez un mode d'importation :

| Mode | Ce qu'il fait |
|---|---|
| **Ajouter** (par défaut) | Fusionne le bundle avec les données actuelles. Les gems et documents existants sont conservés. Si un élément entrant a le même ID qu'un existant, il est importé sous un nouvel ID (ex. `policy-2`). |
| **Remplacer** | Supprime tous les gems, documents et dossiers actuels, puis importe tout depuis le bundle. |

!!! warning "Le mode Remplacer est irréversible"
    Le mode Remplacer supprime définitivement tous les gems et documents existants avant l'importation. Exportez une sauvegarde d'abord si vous souhaitez conserver l'état actuel.

Après une importation réussie, un résumé indique combien de gems et de documents ont été importés et si certains ont été renommés en raison de conflits d'ID.

## URL du réseau local

L'URL du réseau local affichée dans l'onglet Paramètres est l'adresse que les utilisateurs de votre réseau doivent ouvrir. Utilisez le bouton **Copier** et partagez-la — par exemple, affichez-la sur un tableau d'affichage ou envoyez-la par e-mail.
