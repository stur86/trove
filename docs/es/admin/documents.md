# Gestionar documentos

La biblioteca de documentos te permite dar a la IA acceso a los archivos de tu institución — políticas, manuales, hojas de referencia — sin tener que incluirlos en los prompts de cada gem individualmente.

## Subir un documento

1. Abre la pestaña **Documentos** en el panel de administración.
2. Selecciona una carpeta de destino (o crea una nueva).
3. Haz clic en **Subir** y elige un archivo.

Los formatos compatibles incluyen PDF, Word (`.docx`), texto plano y la mayoría de formatos de oficina habituales. Trove convierte los archivos subidos a texto plano internamente usando [Markitdown](https://github.com/microsoft/markitdown). El archivo original se conserva junto a la versión convertida.

Tras la subida, la IA genera automáticamente una descripción de una línea del documento. Esta descripción se muestra en el panel de administración y se usa cuando la IA decide qué documentos consultar.

## Carpetas

Los documentos se organizan en carpetas. Las carpetas son la unidad de control de acceso: cuando creas un gem, otorgas acceso a carpetas enteras o a documentos individuales dentro de ellas.

Para crear una carpeta, escribe un nombre en el campo **Nueva carpeta** y pulsa Enter (o el botón de añadir).

Para renombrar una carpeta o un documento, haz clic en su nombre en el panel de administración.

## Cómo usa la IA los documentos

Cuando un gem tiene acceso a documentos, Trove proporciona a la IA un resumen de todos los documentos accesibles antes de comenzar. La IA puede entonces solicitar el texto completo de cualquier documento que considere relevante. No hay búsqueda vectorial — la IA razona a partir de los resúmenes y obtiene el contenido completo bajo demanda.

Esto significa:
- **Los documentos cortos, bien nombrados y con buenas descripciones** son más fáciles de encontrar y usar para la IA.
- **Los documentos muy grandes** pueden truncarse para caber en la ventana de contexto del modelo.
- La IA no siempre usará documentos — los usa solo cuando parecen relevantes para la solicitud del usuario.

## Descargar documentos

Puedes descargar documentos individuales o carpetas enteras directamente desde la pestaña Documentos.

- **Carpeta** — haz clic en el icono de descarga (↓) junto al nombre de una carpeta para recibir un archivo ZIP con la versión Markdown convertida de cada documento de esa carpeta.
- **Documento** — haz clic en el icono de descarga junto al nombre de un documento para recibir su archivo Markdown convertido (`.md`).

Estas descargas contienen la versión en texto plano de cada archivo tal como Trove lo ve, no el archivo original subido.

## Eliminar un documento

Haz clic en el botón **Eliminar** junto a un documento en el panel de administración. El archivo y sus metadatos se eliminan permanentemente.
