# Participantes de cursos

## URLs

- Registro público: `POST /api/course-participants`
- Panel: `/admin/participantes`
- ABM protegido: `/api/course-participants`
- Recordatorios próximos: `POST /api/course-participants/reminders/run`

## Variables de entorno

```env
PARTICIPANTS_ADMIN_TOKEN=un-token-largo-y-aleatorio

SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=usuario
SMTP_PASSWORD=clave
SMTP_FROM=cursos@dpia.site
SMTP_USE_TLS=true

COURSE_DATE_IA_MARKETING=2026-08-10T18:00:00+02:00
COURSE_DATE_IA_PROCESSES=2026-08-17T18:00:00+02:00
COURSE_DATE_MASTERCLASS_IA=2026-08-24T18:00:00+02:00
COURSE_TIMEZONE=Europe/Rome
COURSE_REMINDER_DAYS=2
```

Las fechas con zona horaria se normalizan a UTC en la base.

## Ejecución automática de recordatorios

El endpoint revisa participantes registrados cuyo curso comienza dentro de
`COURSE_REMINDER_DAYS` y que todavía no recibieron recordatorio.

Ejemplo para un cron diario:

```bash
curl -fsS -X POST \
  -H "X-Admin-Token: $PARTICIPANTS_ADMIN_TOKEN" \
  http://127.0.0.1:8300/api/course-participants/reminders/run
```

No se debe colocar el token en HTML, JavaScript público ni en el repositorio.
