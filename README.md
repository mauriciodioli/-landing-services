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
