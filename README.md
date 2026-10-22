# DPIA Solutions — Landing page

Landing estática profesional para DPIA Solutions, creada con HTML5, CSS y JavaScript sin dependencias de framework.

## Vista local

Abrí `index.html` directamente o ejecutá un servidor local:

```powershell
python -m http.server 8080
```

Luego visitá `http://localhost:8080`.

## Publicar en GitHub Pages

1. Subí `index.html`, `styles.css`, `script.js` y la carpeta `assets/` a la rama principal.
2. En GitHub abrí **Settings > Pages**.
3. Elegí **Deploy from a branch**, rama `main`, carpeta `/ (root)`.
4. Guardá y esperá que GitHub muestre la URL pública.

## Versión Flask

La misma landing está integrada en `src/templates/index.html`; sus recursos se encuentran en `src/static/b2b/`.

## Idiomas

El selector ES/IT/EN está preparado visualmente. Español es la versión activa; las traducciones se incorporarán en archivos separados.

## Landing de desarrollo web

La nueva landing está integrada en el mismo Flask y en la imagen Docker existente (puerto 8300):

- Ruta directa: `/desarrollo-web` (redirige a ES, EN o IT según el navegador).
- Idiomas: `/desarrollo-web/es/`, `/desarrollo-web/en/`, `/desarrollo-web/it/`.
- El host `web.dpia.site` selecciona esta landing desde `/`, como los otros subdominios. Se puede configurar con `WEB_LANDING_HOSTS`.
- Plantillas: `src/templates/web/`. Recursos y video: `src/static/web/`.
- Controlador: `src/controllers/web_landing.py`. Contenido y validación: `src/services/web_landing/`.
- El formulario usa `/desarrollo-web/api/leads` y `get_db_session()` de `src/utils/db_session.py` para commit, rollback y liberación de la sesión compartida. Los modelos `Lead` y `RateWindow` están en `src/models/web_lead.py`, heredan de `db.Model` y se registran en el `db.create_all()` del arranque existente. No se crean tablas durante las peticiones. No requiere otra base de datos ni credenciales. Confirmación solo tras guardar.
- No se han modificado Nginx, DNS, el Dockerfile ni GitHub Actions. El despliegue actual incluye los archivos al copiar `src/`.

Pruebas aisladas: `python -m unittest discover -s tests -p test_web_landing.py -v`. No requieren las credenciales ni los servicios externos de producción. La validación de persistencia se realiza con SQLite temporal; MySQL utiliza UPSERT propio de su dialecto.

## Administración de solicitudes web

El login existente abre `/admin`, con navegación separada entre `/admin/participantes` y `/admin/solicitudes-web`. El segundo panel permite alta, consulta, edición, eliminación, búsqueda y filtros paginados de `web_leads`; no mezcla datos con cursos. Las API `/admin/api/web-leads` comprueban el usuario activo y su rol en cada operación: únicamente ADMINISTRADOR y MODERADOR. Se reutilizan los tokens o credenciales existentes y `get_db_session()`; no se añaden conexiones ni columnas a la base de datos. El acceso existente de usuarios avanzados al panel de cursos se conserva.

La creación manual exige confirmar que el contacto autorizó el tratamiento. La edición conserva la referencia, fecha y versión del consentimiento original. Eliminar requiere confirmación en la interfaz. Este ABM no envía respuestas por correo; los contactos y sus necesidades se consultan para su seguimiento por el equipo.

Pruebas: `python -m unittest discover -s tests -p 'test_web*.py' -v`.
