# Landing Services — Servicios Personal &amp; DPIA

Estructura de landing pages para **Servicios Personal** y **DPIA** (Evaluación de Impacto en Protección de Datos).

## Páginas

| Archivo | Descripción |
|---|---|
| `index.html` | Landing principal con hero, catálogo de servicios, sección DPIA, proceso y contacto |
| `servicios-personal.html` | Página detallada de todos los servicios de asesoría personal |
| `dpia.html` | Página detallada de DPIA: qué es, cuándo es obligatoria, proceso, precios y FAQ |

## Estructura del proyecto

```
.
├── index.html                  # Landing principal
├── servicios-personal.html     # Página de Servicios Personal
├── dpia.html                   # Página de DPIA
├── css/
│   ├── styles.css              # Estilos globales (reset, navbar, hero, secciones, footer)
│   └── pages.css               # Estilos específicos de páginas internas
├── js/
│   └── main.js                 # JS: menú móvil, accordion, formulario, animaciones
└── assets/
    └── images/                 # Imágenes del proyecto
```

## Características

- **Diseño responsive** — funciona en móvil, tablet y escritorio
- **Navbar fija** con menú hamburguesa en móvil
- **Hero** con badge, título, descripción y botones CTA
- **Barra de estadísticas** con contadores animados
- **Sección Servicios Personal** con 6 tarjetas de servicio
- **Sección DPIA** con features y fases del proceso
- **Sección Proceso** con pasos numerados
- **Sección Contacto** con formulario funcional
- **Página Servicios Personal** con tarjetas detalladas, timeline y precios
- **Página DPIA** con marco normativo, cuándo es obligatoria, proceso, matriz de riesgo, precios y FAQ con accordion
- **Footer** con columnas de navegación y año dinámico

## Uso

Abre `index.html` en cualquier navegador moderno. No requiere servidor ni dependencias.

## Servicios cubiertos

### Servicios Personal
- Gestión Documental
- Orientación Profesional
- Asesoría Legal Básica
- Planificación Financiera
- Privacidad Digital
- Acompañamiento Continuo

### DPIA (Evaluación de Impacto en Protección de Datos)
- Marco normativo (RGPD / LOPDGDD)
- Proceso en 5 fases
- Análisis de riesgo con matriz probabilidad × impacto
- Tres niveles de servicio: Básica, Completa, Empresarial
- FAQ con las preguntas más habituales
