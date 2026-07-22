# Landing Inmersión IA: procesos, datos y decisiones

## Acceso

- Ruta directa: `/inmersion-ia-procesos`
- Subdominio predeterminado: `procesos.dpia.site`
- Alias admitido: `ia-procesos.dpia.site`

Los hosts pueden configurarse con:

```text
IA_PROCESSES_HOSTS=procesos.dpia.site
```

El endpoint del formulario se configura de forma independiente:

```text
IA_PROCESSES_REGISTRATION_ENDPOINT=https://api.example.com/registrations
```

## DNS

Crear un registro en el proveedor DNS:

```text
Tipo: A
Nombre: procesos.dpia.site
Contenido: 54.234.169.22
```

## Nginx

En el servidor:

```bash
sudo cp deploy/nginx/procesos.dpia.site.conf /etc/nginx/sites-available/procesos.dpia.site
sudo ln -s /etc/nginx/sites-available/procesos.dpia.site /etc/nginx/sites-enabled/procesos.dpia.site
sudo nginx -t
sudo systemctl reload nginx
```

Cuando HTTP responda correctamente:

```bash
sudo certbot --nginx -d procesos.dpia.site
```

## Archivos

- `src/templates/ia-processes/index.html`
- `src/static/ia-processes/base.css`
- `src/static/ia-processes/styles.css`
- `src/static/ia-processes/app.js`
- `src/static/ia-processes/assets/`
