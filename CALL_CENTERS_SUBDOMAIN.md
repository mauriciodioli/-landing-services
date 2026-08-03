# Subdominio call.dpia.site

## 1. DNS en DonWeb

En Nameservers y Zona DNS, pulse Agregar registro:

    Tipo:       A
    Nombre:     call.dpia.site
    Contenido:  54.234.169.22
    TTL:        900
    Prioridad:  0

No cree un CNAME adicional para el mismo nombre.

## 2. Desplegar Nginx

Después de actualizar el repositorio en el servidor:

    sudo cp deploy/nginx/call.dpia.site.conf /etc/nginx/sites-available/call.dpia.site
    sudo ln -s /etc/nginx/sites-available/call.dpia.site /etc/nginx/sites-enabled/call.dpia.site
    sudo nginx -t
    sudo systemctl reload nginx

Si el enlace ya existe, no vuelva a ejecutar ln -s.

## 3. Verificar

Antes de depender del DNS:

    curl -I -H 'Host: call.dpia.site' http://127.0.0.1:8300/

Después de la propagación:

    curl -I http://call.dpia.site/

La URL raíz debe mostrar Talent Call. La ruta /call-centers continúa disponible.

## 4. Activar HTTPS

Cuando el DNS ya resuelva a 54.234.169.22:

    sudo certbot --nginx -d call.dpia.site
    sudo nginx -t
    sudo systemctl reload nginx

Verificación final:

    curl -I https://call.dpia.site/

Variable opcional de entorno:

    CALL_CENTERS_HOSTS=call.dpia.site
