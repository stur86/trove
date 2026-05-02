## Rédiger un bon modèle de prompt

Le modèle est l'instruction que vous donnez à l'IA. Utilisez `{{ nom_variable }}` n'importe où dans le texte pour créer un champ que l'utilisateur remplit avant d'exécuter le Gem.

**Exemple :**

```
Résumez le texte suivant en {{ langue }}, en utilisant au maximum {{ points_max }} points :

{{ texte }}
```

Cela crée trois champs de saisie : *langue*, *points_max* et *texte*.

**Conseils pour un bon prompt :**

- **Soyez précis** — indiquez au modèle exactement ce que vous voulez qu'il produise.
- **Précisez le format** — liste à puces, court paragraphe, étapes numérotées, tableau…
- **Donnez un exemple** — si la tâche est délicate, montrez à quoi ressemble une bonne réponse.
- **Restez concis** — le modèle fonctionne mieux avec des instructions claires et concises.
- **Nommez clairement les variables** — `{{ nom_patient }}` est préférable à `{{ nom }}`.
