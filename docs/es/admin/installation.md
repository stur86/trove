# Instalación

Esta guía es para la persona que configura Trove. No se necesita experiencia en programación.

## Lo que necesitas

- Un ordenador con **Linux** (Ubuntu 22.04 o posterior recomendado)
- Al menos **4 GB de RAM** (8 GB o más es mejor)
- Al menos **10 GB de espacio libre en disco**
- Conexión a internet *solo durante la instalación* — después, Trove funciona completamente sin conexión

## Paso 1 — Instalar Trove

Abre un terminal y ejecuta:

```bash
curl -LsSf https://raw.githubusercontent.com/stur86/trove/main/install.sh | bash
```

Esto descarga el instalador, obtiene la última versión de Trove y lo configura todo. Tarda unos minutos.

!!! tip "¿Comando no encontrado después?"
    Si ves `trove: command not found` después de que termine el instalador, ejecuta el comando que muestra (algo como `export PATH="$HOME/.local/bin:$PATH"`), luego abre una nueva ventana de terminal.

## Paso 2 — Ejecutar el asistente de configuración

Ejecuta el asistente de configuración **en el mismo ordenador donde acabas de instalar Trove**. La página de configuración solo es accesible desde ese equipo — esto es intencionado.

```bash
trove setup
```

Luego abre un navegador **en ese mismo ordenador** y ve a:

```
http://localhost:7071
```

El asistente te guía por seis pasos:

1. **Idioma** — elige el idioma de la interfaz
2. **Bienvenida** — confirma tu hardware y lo que Trove instalará
3. **Instalar Ollama** — descarga el motor de IA (omitido si ya está instalado)
4. **Elegir un modelo** — elige un modelo Gemma 4; solo se muestran los modelos que tu hardware puede ejecutar. Este paso requiere conexión a internet y puede tardar 10–30 minutos.
5. **Cuenta de administrador** — establece un nombre de usuario y contraseña para el panel de administración
6. **Instalar servicio** — registra Trove para que se inicie automáticamente al arrancar

Al terminar, el panel muestra la dirección que debes dar a tus usuarios.

## Paso 3 — Dar a los usuarios una dirección fiable

Cuando Trove arranca muestra una dirección como `http://192.168.1.42:7770`. Los usuarios en otros dispositivos la abren en cualquier navegador — sin ninguna aplicación que instalar.

**La dirección puede cambiar** cada vez que el servidor se reinicia, porque los routers domésticos y de oficina reasignan las direcciones automáticamente. Si cambia, los usuarios obtendrán un error de "sitio inaccesible".

!!! info "Solucionarlo con una IP estática"
    Asignar una dirección IP fija ("estática") al ordenador servidor evita que la dirección cambie. Solo lo haces una vez, en la configuración de tu router.

    1. Abre la página de administración de tu router — normalmente `http://192.168.1.1` o `http://192.168.0.1` (consulta la etiqueta de tu router).
    2. Busca la sección llamada **DHCP**, **LAN** o **Reserva de IP**.
    3. Busca el servidor de Trove en la lista de dispositivos conectados y asígnale una dirección fija.
    4. Guarda y reinicia el router si se te pide.

    Si necesitas ayuda con esto, consulta a tu soporte informático — es una tarea habitual.

## Iniciar y detener Trove

Si instalaste el servicio durante la configuración, Trove se inicia automáticamente al arrancar el equipo. También puedes controlarlo manualmente:

```bash
systemctl --user status trove    # comprobar si está en ejecución
systemctl --user restart trove   # reiniciar
systemctl --user stop trove      # detener
```

Si omitiste el servicio, inicia Trove manualmente cuando lo necesites:

```bash
trove start
```

Pulsa `Ctrl + C` para detenerlo. Para mantener el servicio en ejecución incluso cuando nadie ha iniciado sesión (útil en un servidor sin interfaz gráfica):

```bash
loginctl enable-linger $USER   # configuración única; puede requerir sudo
```

## Guía de selección de modelos

| Modelo | RAM mínima | Audio | Ideal para |
|---|---|---|---|
| Gemma 4 E2B | 4 GB | Sí | Ordenadores muy lentos, respuestas más rápidas |
| Gemma 4 E4B | 6 GB | Sí | Equilibrado — opción predeterminada recomendada |
| Gemma 4 26B | 10 GB | No | Mejor calidad, velocidad similar a E4B |
| Gemma 4 31B | 20 GB | No | Mayor calidad, necesita un equipo potente |

## Solución de problemas

**"trove: command not found"**
Ejecuta `export PATH="$HOME/.local/bin:$PATH"` e inténtalo de nuevo. Para hacerlo permanente, añade esa línea a `~/.bashrc`.

**La página de configuración no carga**
Asegúrate de estar en el mismo ordenador donde ejecutaste `trove setup` y que el comando sigue ejecutándose en el terminal.

**Otros dispositivos no pueden llegar a Trove**
Comprueba que `trove start` (o el servicio) está en ejecución. Asegúrate de que todos los dispositivos están en la misma red Wi-Fi o por cable. Si la dirección sigue cambiando, establece una IP estática en tu router (ver paso 3).

**La descarga del modelo es muy lenta**
La primera descarga puede tardar 10–30 minutos según tu conexión a internet. Solo ocurre una vez.
