# Descripción general de administración

El panel de administración solo es accesible desde el equipo que ejecuta Trove. Abre `http://localhost:7770/admin` en un navegador en ese equipo e inicia sesión con las credenciales que estableciste durante la configuración.

!!! warning "El acceso de administrador es solo para localhost"
    El inicio de sesión de administrador está oculto intencionalmente para todos los demás dispositivos de la red. Esto es una medida de seguridad. Para gestionar Trove debes estar físicamente en el servidor o usar un túnel SSH.

## Las cuatro pestañas

| Pestaña | Qué puedes hacer |
|---|---|
| **Configuración** | Elegir el modelo de IA, establecer el tamaño de la ventana de contexto, cambiar el idioma de visualización |
| **Documentos** | Subir archivos, organizarlos en carpetas, ver resúmenes generados por IA |
| **Gems** | Crear, editar y eliminar gems |
| **Registros** | Ver las últimas 1.000 líneas del registro del servidor, actualizadas automáticamente cada 5 segundos |

## URL de LAN

La pestaña Configuración muestra la **URL de LAN** — la dirección que deben usar otros dispositivos para acceder a Trove. Cópiala y compártela con tus usuarios.

## Pasos siguientes

- [Instalación](installation.md)
- [Gestionar gems](gems.md)
- [Gestionar documentos](documents.md)
- [Referencia de configuración](settings.md)
