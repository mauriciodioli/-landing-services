# Nueva landing — DPIA Software Solutions

Aplicación independiente en ES/EN/IT para `https://web.dpia.site/`. No importa el código de la aplicación existente y no añade rutas a `dpia.site`. No incluye cambios de Nginx, DNS, certificados, contenedores ni workflows. El único cambio en la landing principal es el destino de los enlaces «Desarrollo web».

## Vista local

Desde este directorio, usa un entorno virtual propio e instala `requirements.txt`. No reutilices las credenciales o la base de datos de las aplicaciones existentes.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export APP_ENV=development
export PUBLIC_HOST=localhost
export DATABASE_URL=sqlite:///instance/leads.sqlite
.venv/bin/flask --app 'app:create_app()' run --port 8310
```

Abre `http://localhost:8310/es/`, `/en/` o `/it/`. La excepción HTTP para la cookie solo se habilita en desarrollo y para localhost/127.0.0.1. Sin esa excepción se exige cookie segura. La aplicación rechaza solicitudes con otro Host. La configuración de publicación, cuando se autorice, deberá usar `PUBLIC_HOST=web.dpia.site`, una clave secreta persistente y HTTPS. `PUBLIC_HOST` no redirige DNS ni publica el sitio.

## Formulario

`POST /api/leads` usa JSON, token CSRF de la sesión, validación de datos, campo trampa, límite de tamaño y un límite persistente de 15 intentos/hora por dirección. La configuración actual espera un único proxy de confianza que sustituya los encabezados de IP/protocolo y una conexión de backend no expuesta al exterior; al publicar, verificar esa topología antes de habilitar acceso. No se incluyen claves API en el cliente.

La respuesta `201` contiene una referencia solo después de confirmar la escritura en la base de datos. No se envían correos automáticos ni se conecta NexusERP: se registra la solicitud para que el equipo la revise. Los fallos de almacenamiento devuelven `503`, nunca una confirmación falsa. No existe una ruta pública para consultar solicitudes.

SQLite inicial es propia de este servicio. `DATABASE_URL` admite futura conexión PostgreSQL con un controlador y una migración explícitos; cambiar la URL no migra los datos. `lead_service.py` separa validación/persistencia de futuras integraciones, que deberán añadirse con credenciales privadas y autorización propia.

## Gestión privada

Con las mismas variables de entorno y desde este directorio:

```bash
.venv/bin/python manage.py export /ruta/privada/solicitudes.csv
.venv/bin/python manage.py purge --days 180
.venv/bin/python manage.py purge --days 180 --apply
```

La exportación crea un archivo nuevo con permisos privados, sin sobrescribir otros, y neutraliza fórmulas de hoja de cálculo. El comando de borrado primero permite revisar cuántas solicitudes se eliminarían. Programar su revisión periódica según la política publicada; excluir los casos de relación comercial activa antes de borrar. Las copias de seguridad también contienen datos personales y requieren acceso restringido y una política de eliminación. No versionar datos, exportaciones ni secretos. La base local está en `instance/`, excluido de Git.

## Comprobaciones

Desde la raíz del repositorio:

```bash
python -m unittest discover -s services/web/tests -v
```

Se prueban idiomas, host exclusivo, persistencia, validación, CSRF, origen, límite compartido, tamaño y fallos de base de datos. `robots.txt`, `sitemap.xml`, canonical y alternates apuntan a `web.dpia.site`. Las ilustraciones son conceptuales, no resultados de clientes. La política de privacidad describe cookies técnicas únicamente; no se incluye analítica ni trackers.

Pendiente fuera de este trabajo: publicación del subdominio, inspección de infraestructura y cualquier integración real. No se ha cambiado Nginx.
