## Escribir una buena plantilla de instrucción

La plantilla es la instrucción que le das a la IA. Usa `{{ nombre_variable }}` en cualquier lugar del texto para crear un campo que el usuario rellena antes de ejecutar el Gem.

**Ejemplo:**

```
Resume el siguiente texto en {{ idioma }}, usando no más de {{ puntos_max }} puntos:

{{ texto }}
```

Esto crea tres campos de entrada: *idioma*, *puntos_max* y *texto*.

**Consejos para una buena instrucción:**

- **Sé específico** — dile al modelo exactamente qué quieres que produzca.
- **Indica el formato** — lista con viñetas, párrafo corto, pasos numerados, tabla…
- **Da un ejemplo** — si la tarea es compleja, muestra cómo es una buena respuesta.
- **Sé conciso** — el modelo funciona mejor con instrucciones claras y concisas.
- **Nombra las variables con claridad** — `{{ nombre_paciente }}` es mejor que `{{ nombre }}`.
