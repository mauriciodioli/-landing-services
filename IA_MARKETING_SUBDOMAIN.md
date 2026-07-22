# Landing Inmersión IA

La landing independiente se sirve en:

- Ruta directa: `/inmersion-ia`
- Hosts predeterminados: `ia.dpia.site` y `marketing.dpia.site`

## Configuración

`IA_MARKETING_HOSTS` acepta uno o varios dominios separados por comas:

```text
IA_MARKETING_HOSTS=ia.dpia.site
```

El proxy o balanceador debe enviar el encabezado `Host` original al contenedor. Al recibir ese host en `/`, Flask muestra la landing de Inmersión IA en lugar de la landing principal.

Para conectar el formulario, configure:

```text
IA_REGISTRATION_ENDPOINT=https://api.example.com/registrations
```

Si el proxy reescribe rutas, también puede dirigir el subdominio a `/inmersion-ia`.

Los archivos están aislados en:

- `src/templates/ia-marketing/index.html`
- `src/static/ia-marketing/`
