# Configuración

La pestaña **Configuración** controla el modelo de IA y las preferencias de visualización para todo el servidor.

## Modelo de IA

| Ajuste | Qué hace |
|---|---|
| **Modelo base** | La variante de Gemma 4 que usa Trove. Solo aparecen en la lista los modelos que ya has descargado. |
| **Ventana de contexto (num_ctx)** | Cuánto texto puede mantener el modelo en memoria a la vez, medido en tokens (aproximadamente ¾ de una palabra cada uno). Valores más grandes manejan documentos más largos pero usan más RAM. |

Después de cambiar el modelo o la ventana de contexto, haz clic en **Guardar y reconstruir** para aplicar el cambio. Trove reconstruye su configuración interna del modelo; esto tarda unos 30 segundos y muestra el progreso en la página.

### Elegir un modelo

| Modelo | Parámetros efectivos | RAM mínima | Audio | Ideal para |
|---|---|---|---|---|
| `gemma4:e2b` | 2,3B | ~4 GB | Sí | Ordenadores muy lentos, respuestas más rápidas |
| `gemma4:e4b` | 4,5B | ~6 GB | Sí | Equilibrado — opción predeterminada recomendada |
| `gemma4:26b` | 4B activos (MoE) | ~10 GB | No | Mejor calidad, velocidad similar a e4b |
| `gemma4:31b` | 31B denso | ~20 GB | No | Mayor calidad, necesita un equipo potente |

!!! tip "Gems de audio y elección de modelo"
    Solo `gemma4:e2b` y `gemma4:e4b` admiten entrada de audio. Si cambias a un modelo sin soporte de audio, los gems que usan entrada de audio se ocultarán a los usuarios hasta que vuelvas a cambiar.

## Idioma

El selector de **Idioma** cambia el idioma de visualización de toda la interfaz de Trove, incluida la pantalla de inicio y el ejecutor de gems para usuarios. Idiomas actualmente compatibles: inglés, francés, alemán, español, portugués, chino, italiano.

## Datos

La sección **Datos** te permite hacer una copia de seguridad de toda la configuración de Trove o restaurar una copia de seguridad anterior.

### Exportar un bundle

Haz clic en **Exportar bundle** para descargar un único archivo ZIP (`trove-bundle.zip`) que contiene:

- Todos los gems y sus configuraciones.
- Todas las carpetas de documentos, los metadatos de los documentos y el texto convertido de cada documento.

Úsalo para hacer una copia de seguridad de tu configuración antes de realizar grandes cambios, o para copiar una instalación a otra instancia de Trove.

### Importar un bundle

Haz clic en **Importar bundle** para abrir el diálogo de importación. Elige un archivo `.zip` exportado desde cualquier instancia de Trove, luego selecciona un modo de importación:

| Modo | Qué hace |
|---|---|
| **Añadir** (predeterminado) | Combina el bundle con los datos actuales. Los gems y documentos existentes se conservan. Si un elemento entrante tiene el mismo ID que uno existente, se importa con un nuevo ID (p. ej. `policy-2`). |
| **Reemplazar** | Elimina todos los gems, documentos y carpetas actuales, luego importa todo del bundle. |

!!! warning "El modo Reemplazar es irreversible"
    El modo Reemplazar elimina permanentemente todos los gems y documentos existentes antes de importar. Exporta primero una copia de seguridad si quieres conservar el estado actual.

Después de una importación exitosa, un resumen muestra cuántos gems y documentos se importaron y si alguno fue renombrado por conflictos de ID.

## URL de LAN

La URL de LAN que se muestra en la pestaña Configuración es la dirección que deben abrir los usuarios de tu red. Usa el botón **Copiar** y compártela — por ejemplo, ponla en un tablón de anuncios o envíala por correo electrónico.
