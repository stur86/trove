## La ventana de contexto

La ventana de contexto controla cuánto texto puede leer y escribir el modelo en una sola tarea. Se mide en **tokens** — aproximadamente tres cuartas partes de una palabra cada uno.

**Directrices:**

- **4.096–8.192** — adecuado para prompts cortos y respuestas breves. El más rápido y el que usa menos memoria.
- **16.384–32.768** — apropiado cuando las tareas implican documentos largos o salidas detalladas.
- **Valores más altos** — usan significativamente más memoria. En máquinas con poca RAM, esto puede ralentizar el servidor o hacer que deje de responder.

Una buena regla general: establécelo en el valor más pequeño que gestione cómodamente tu tarea más larga prevista. Si una respuesta parece cortarse a mitad de frase, aumenta este valor y haz clic en **Guardar configuración** para reconstruir.
