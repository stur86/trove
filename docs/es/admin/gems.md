# Gestionar gems

Un **Gem** es una tarea de IA reutilizable con un propósito fijo. Los usuarios ven los gems como tarjetas en la pantalla de inicio y rellenan un formulario corto para ejecutarlos.

## Crear un gem

1. Abre la pestaña **Gems** en el panel de administración.
2. Haz clic en **Nuevo gem**.
3. Rellena el formulario:

| Campo | Qué hace |
|---|---|
| **Nombre** | Se muestra en la tarjeta del gem. Mantenlo corto y descriptivo. |
| **Descripción** | Opcional. Una pista de una línea que se muestra bajo el nombre. |
| **Tono** | El color del icono del gem. Usa colores distintos para distinguir fácilmente los gems de un vistazo. |
| **Plantilla de prompt** | La instrucción para la IA. Usa marcadores `{{ variable_name }}` para los campos que rellena el usuario. |
| **Capacidades** | Marca *Acepta entrada de imagen* si la tarea necesita una foto o captura de pantalla. |
| **Modo de salida** | *Texto* para salida normal; *Estructurado (JSON)* para salida legible por máquina. |
| **Acceso a documentos** | Qué carpetas de documentos o archivos individuales puede leer la IA al ejecutar este gem. |

4. Haz clic en **Crear**.

## Escribir una buena plantilla de prompt

La plantilla es la instrucción que recibe la IA. Puede incluir cualquier texto, más marcadores:

```
Resume el siguiente texto en {{ language }}, usando no más de 5 viñetas:

{{ text }}
```

Esto crea dos campos de entrada para el usuario: *language* y *text*.

**Consejos:**

- Sé específico. Dile a la IA exactamente el formato que quieres.
- Indica el idioma esperado de la respuesta si es importante.
- Mantén las instrucciones cortas — el modelo funciona mejor con prompts claros y concisos.
- Prueba el gem tú mismo/a antes de compartirlo con los usuarios.

## Acceso a documentos

Cada gem puede tener acceso a parte de la biblioteca de documentos mediante el árbol de carpetas y documentos del formulario del gem:

- **Acceso a carpeta** — marca la casilla junto al nombre de una carpeta. La IA puede ver cada documento en esa carpeta, incluidos los añadidos posteriormente. Marcar una carpeta marca automáticamente todos los documentos dentro.
- **Acceso a documento individual** — despliega una carpeta y marca solo los documentos específicos que quieras. Una carpeta con algunos documentos marcados pero no todos muestra un indicador parcial (−).
- **Sin acceso** (predeterminado) — deja todas las casillas desmarcadas. La IA no usa la biblioteca de documentos para este gem.

Cuando un gem tiene acceso a documentos, la IA decide por sí misma si consultar documentos o responder desde su propio conocimiento.

## Editar y eliminar

Haz clic en **Editar** junto a un gem para cambiar su configuración. Haz clic en **Eliminar** para eliminarlo permanentemente. No hay opción de deshacer.

!!! warning "Eliminar un gem"
    Los gems eliminados no se pueden recuperar. Los usuarios que intenten abrir la URL de un gem eliminado verán un error.
