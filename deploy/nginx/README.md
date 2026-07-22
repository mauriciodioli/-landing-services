# Nginx para marketing.dpia.site

El DNS mostrado ya tiene el registro necesario:

```text
marketing.dpia.site  A  54.234.169.22
```

La aplicación reconoce `marketing.dpia.site` mediante `IA_MARKETING_HOSTS` y muestra la landing de Inmersión IA al acceder a `/`.

## Instalar la configuración

En el servidor `54.234.169.22`:

```bash
sudo cp deploy/nginx/marketing.dpia.site.conf /etc/nginx/sites-available/marketing.dpia.site
sudo ln -s /etc/nginx/sites-available/marketing.dpia.site /etc/nginx/sites-enabled/marketing.dpia.site
sudo nginx -t
sudo systemctl reload nginx
```

Si el enlace ya existe, no vuelva a ejecutar `ln -s`.

## Verificaciones previas

La aplicación debe responder localmente en el servidor:

```bash
curl -I -H 'Host: marketing.dpia.site' http://127.0.0.1:8300/
```

Después de recargar Nginx:

```bash
curl -I http://marketing.dpia.site/
```

## Activar HTTPS

Una vez que HTTP responda correctamente y el DNS haya propagado:

```bash
sudo certbot --nginx -d marketing.dpia.site
sudo nginx -t
sudo systemctl reload nginx
```

Certbot añadirá el bloque TLS y la redirección de HTTP a HTTPS sin incluir rutas de certificados inexistentes en la configuración inicial.

## Variables del contenedor

El host ya está incluido en los valores predeterminados. Para declararlo explícitamente:

```text
IA_MARKETING_HOSTS=marketing.dpia.site
```

Para conectar el formulario:

```text
IA_REGISTRATION_ENDPOINT=https://api.example.com/registrations
```
