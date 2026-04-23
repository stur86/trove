## La fenêtre de contexte

La fenêtre de contexte contrôle la quantité de texte que le modèle peut lire et écrire en une seule tâche. Elle est mesurée en **tokens** — soit environ trois quarts de mot chacun.

**Recommandations :**

- **4 096–8 192** — adapté aux prompts courts et aux réponses brèves. Le plus rapide et utilise le moins de mémoire.
- **16 384–32 768** — approprié lorsque les tâches impliquent de longs documents ou des sorties détaillées.
- **Valeurs plus élevées** — utilisent nettement plus de mémoire. Sur les machines avec peu de RAM, cela peut ralentir le serveur ou le rendre non réactif.

Une bonne règle de base : réglez-la sur la valeur minimale permettant de gérer confortablement votre tâche la plus longue. Si une réponse semble coupée en milieu de phrase, augmentez cette valeur et cliquez sur **Enregistrer les paramètres** pour reconstruire.
