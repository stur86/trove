# Installation

Ce guide est destiné à la personne qui configure Trove. Aucune expérience en programmation n'est requise.

## Ce dont vous avez besoin

- Un ordinateur fonctionnant sous **Linux** (Ubuntu 22.04 ou version ultérieure recommandée)
- Au moins **4 Go de RAM** (8 Go ou plus est préférable)
- Au moins **10 Go d'espace disque libre**
- Une connexion internet *uniquement pendant l'installation* — ensuite, Trove fonctionne entièrement hors ligne

## Étape 1 — Installer Trove

Ouvrez un terminal et exécutez :

```bash
curl -LsSf https://raw.githubusercontent.com/stur86/trove/main/install.sh | bash
```

Cela télécharge le programme d'installation, récupère la dernière version de Trove et configure tout. Cela prend quelques minutes.

!!! tip "Commande introuvable ensuite ?"
    Si vous voyez `trove: command not found` après la fin de l'installation, exécutez la commande affichée (quelque chose comme `export PATH="$HOME/.local/bin:$PATH"`), puis ouvrez une nouvelle fenêtre de terminal.

## Étape 2 — Lancer l'assistant de configuration

Exécutez l'assistant de configuration **sur le même ordinateur où vous venez d'installer Trove**. La page de configuration n'est accessible que depuis cette machine — c'est intentionnel.

```bash
trove setup
```

Ensuite, ouvrez un navigateur **sur ce même ordinateur** et accédez à :

```
http://localhost:7071
```

L'assistant vous guide à travers six étapes :

1. **Langue** — choisissez la langue de l'interface
2. **Bienvenue** — confirme votre matériel et ce que Trove va installer
3. **Installer Ollama** — télécharge le moteur d'IA (ignoré si déjà installé)
4. **Choisir un modèle** — sélectionnez un modèle Gemma 4 ; seuls les modèles compatibles avec votre matériel sont affichés. Cette étape nécessite une connexion internet et peut prendre 10 à 30 minutes.
5. **Compte administrateur** — définissez un nom d'utilisateur et un mot de passe pour le panneau d'administration
6. **Installer le service** — enregistre Trove pour qu'il démarre automatiquement au démarrage

Une fois terminé, le tableau de bord affiche l'adresse à communiquer à vos utilisateurs.

## Étape 3 — Donner aux utilisateurs une adresse fiable

Lorsque Trove démarre, il affiche une adresse du type `http://192.168.1.42:7770`. Les utilisateurs sur d'autres appareils l'ouvrent dans n'importe quel navigateur — aucune application à installer.

**L'adresse peut changer** à chaque redémarrage du serveur, car les routeurs domestiques et professionnels réattribuent les adresses automatiquement. Si elle change, les utilisateurs obtiendront une erreur « site inaccessible ».

!!! info "Résoudre cela avec une adresse IP statique"
    La définition d'une adresse IP fixe (« statique ») pour l'ordinateur serveur empêche l'adresse de changer. Vous ne le faites qu'une seule fois, dans les paramètres de votre routeur.

    1. Ouvrez la page d'administration de votre routeur — généralement `http://192.168.1.1` ou `http://192.168.0.1` (vérifiez l'étiquette de votre routeur).
    2. Trouvez la section appelée **DHCP**, **LAN** ou **Réservation IP**.
    3. Trouvez le serveur Trove dans la liste des appareils connectés et attribuez-lui une adresse fixe.
    4. Enregistrez et redémarrez le routeur si demandé.

    Si vous avez besoin d'aide, contactez votre support informatique — c'est une tâche courante.

## Démarrer et arrêter Trove

Si vous avez installé le service lors de la configuration, Trove démarre automatiquement au démarrage. Vous pouvez également le contrôler manuellement :

```bash
systemctl --user status trove    # check if running
systemctl --user restart trove   # restart
systemctl --user stop trove      # stop
```

Si vous n'avez pas installé le service, démarrez Trove manuellement si nécessaire :

```bash
trove start
```

Appuyez sur `Ctrl + C` pour l'arrêter. Pour maintenir le service en cours d'exécution même lorsque personne n'est connecté (utile sur un serveur sans interface graphique) :

```bash
loginctl enable-linger $USER   # one-time setup; may require sudo
```

## Guide de sélection des modèles

| Modèle | RAM minimale | Audio | Idéal pour |
|---|---|---|---|
| Gemma 4 E2B | 4 Go | Oui | Machines très lentes, réponses les plus rapides |
| Gemma 4 E4B | 6 Go | Oui | Équilibré — recommandé par défaut |
| Gemma 4 26B | 10 Go | Non | Meilleure qualité, vitesse similaire à E4B |
| Gemma 4 31B | 20 Go | Non | Qualité maximale, nécessite une machine puissante |

## Dépannage

**« trove: command not found »**
Exécutez `export PATH="$HOME/.local/bin:$PATH"` et réessayez. Pour que ce soit permanent, ajoutez cette ligne à `~/.bashrc`.

**La page de configuration ne se charge pas**
Assurez-vous d'être sur le même ordinateur où vous avez exécuté `trove setup`, et que la commande est toujours en cours d'exécution dans le terminal.

**Les autres appareils ne peuvent pas accéder à Trove**
Vérifiez que `trove start` (ou le service) est en cours d'exécution. Assurez-vous que tous les appareils sont sur le même réseau Wi-Fi ou filaire. Si l'adresse continue de changer, définissez une IP statique sur votre routeur (voir étape 3).

**Le téléchargement du modèle est très lent**
Le premier téléchargement peut prendre 10 à 30 minutes selon votre connexion internet. Il ne se produit qu'une seule fois.
