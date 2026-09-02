# Especificación base: álbum multimedia y regalos digitales

## Estado del documento

- Tipo: visión funcional y base para futuros cambios.
- Estado: implementación inicial activa en `feature/album-multimedia-gifts`; la rama estable permanece separada.
- Alcance actual: definir con precisión el resultado esperado, sus límites y una secuencia segura de desarrollo.
- Producto de referencia: álbum privado asociado a una cuenta DPIA, con páginas individuales compartibles públicamente.

## 1. Visión

Convertir el álbum en un espacio personal donde cada página pueda contar una historia completa mediante texto, música, imágenes, videos, contenido externo y regalos digitales.

El propietario podrá combinar archivos de su dispositivo con enlaces de servicios externos. También podrá preparar un regalo comprado en una tienda, representarlo mediante un QR o enlace y entregarlo dentro de una página del álbum.

La experiencia debe seguir siendo sencilla para una persona no técnica y conservar la privacidad actual:

- El álbum completo solo lo abre su propietario autenticado con su cuenta DPIA.
- Una página puede compartirse mediante su enlace individual sin exigir login al destinatario.
- Compartir una página no debe permitir navegar por el resto del álbum.
- Los regalos sensibles requieren más protección que el contenido multimedia normal.

## 2. Objetivos

1. Permitir música diferente en cada página.
2. Mantener una música general como opción predeterminada del álbum.
3. Aceptar imágenes, GIF, videos y música tanto por carga local como por enlace.
4. Mostrar contenido externo con una presentación consistente y segura.
5. Permitir agregar regalos digitales mediante QR, enlace o código.
6. Proteger códigos de regalo para evitar su exposición accidental.
7. Mantener compatibilidad con álbumes, páginas y archivos existentes.
8. Ofrecer controles claros para previsualizar, editar, ocultar, compartir y eliminar contenido.

## 3. Principios del producto

- **Sencillez:** agregar contenido debe requerir pocos pasos.
- **Privacidad por defecto:** una página o regalo nuevo no debe publicarse accidentalmente.
- **Compatibilidad:** las páginas existentes deben seguir funcionando sin cambios manuales.
- **Seguridad:** no se insertará HTML arbitrario ni se confiará ciegamente en enlaces externos.
- **Degradación elegante:** si un proveedor externo falla, la página debe continuar funcionando y mostrar una alternativa comprensible.
- **Control del propietario:** el usuario decide qué se muestra, qué se comparte y cuándo se revoca.
- **Experiencia móvil:** cargar, pegar enlaces, escanear QR y compartir deben funcionar cómodamente desde el celular.

## 4. Alcance funcional

### 4.1 Música por página

Cada página podrá tener una configuración musical opcional.

Comportamiento esperado:

- Si la página tiene música propia, se utiliza esa música.
- Si no tiene música propia, se utiliza la música general del álbum.
- Si tampoco existe música general, el control musical se muestra desactivado o no se muestra.
- Al cambiar de página, la reproducción anterior se detiene antes de iniciar otra.
- La reproducción automática dependerá de los permisos del navegador; si está bloqueada, se mostrará un botón de reproducción.
- El propietario podrá reemplazar o quitar la música de una página.
- La página compartida utilizará la misma configuración musical que la página original.

Fuentes iniciales recomendadas:

- Spotify.
- YouTube y YouTube Music.
- Enlaces directos de audio compatibles con el navegador.

Los proveedores adicionales se incorporarán mediante adaptadores, sin guardar código HTML entregado por el usuario.

### 4.2 Contenido multimedia mediante enlaces

El editor de página tendrá dos formas de agregar contenido:

1. **Subir desde el dispositivo.**
2. **Agregar mediante enlace.**

Tipos previstos:

- Imagen directa.
- GIF animado.
- Video de YouTube.
- Video de Vimeo.
- GIF de Giphy o Tenor.
- Audio o música admitida.
- Publicaciones de otras redes únicamente cuando exista una integración oficial y estable.

Flujo esperado:

1. El usuario pulsa **Agregar mediante enlace**.
2. Pega una URL.
3. El sistema identifica el proveedor y el tipo de contenido.
4. Se muestra una previsualización antes de guardar.
5. El usuario puede agregar un título o texto alternativo.
6. Al confirmar, el elemento se incorpora a la página actual.
7. El usuario puede cambiar el orden o eliminarlo posteriormente.

Reglas:

- No se admitirán esquemas distintos de HTTPS, salvo excepciones locales de desarrollo.
- No se guardará ni renderizará HTML arbitrario proporcionado por el usuario.
- Los `iframe` solo podrán provenir de proveedores autorizados.
- Una URL no reconocida debe rechazarse con una explicación clara.
- Las imágenes remotas deben tener texto alternativo configurable.
- Si el recurso deja de existir, se mostrará un estado de contenido no disponible sin romper la página.

### 4.3 Regalos digitales y QR

Una página podrá contener una o más tarjetas de regalo.

Formas de ingreso previstas:

- Subir una imagen que ya contiene un QR.
- Escanear un QR con la cámara del celular.
- Pegar el enlace de canje entregado por una tienda.
- Introducir un código de regalo y generar un QR a partir de él.
- Adjuntar opcionalmente una imagen, GIF, video, música y mensaje de dedicatoria.

Datos visibles de una tarjeta de regalo:

- Título del regalo.
- Mensaje personal.
- Comercio o proveedor.
- Imagen de presentación opcional.
- Fecha de vencimiento opcional.
- Botón **Descubrir regalo**.
- Estado: preparado, disponible, abierto, reclamado, vencido o revocado.

Flujo del propietario:

1. Selecciona **Agregar regalo**.
2. Elige QR, enlace o código.
3. Agrega mensaje y datos opcionales.
4. Revisa una previsualización.
5. Decide si el regalo estará protegido.
6. Publica la página y comparte su enlace.
7. Puede consultar el estado, ocultarlo o revocarlo.

Flujo del destinatario:

1. Abre el enlace público de la página.
2. Ve la tarjeta del regalo sin exponer inmediatamente el secreto.
3. Pulsa **Descubrir regalo**.
4. Supera la protección configurada, si existe.
5. Visualiza el QR, enlace o código.
6. Puede marcarlo como reclamado o el sistema puede registrar su primera apertura.

## 5. Protección de regalos

Un QR o código comprado puede tener valor monetario. Por ello, no debe tratarse como una imagen pública común.

Requisitos mínimos:

- El secreto del regalo se almacenará cifrado en el servidor.
- La respuesta pública normal de una página nunca incluirá el código, enlace de canje o contenido QR sensible.
- La revelación se realizará mediante un endpoint específico y controlado.
- Se podrá exigir un PIN del destinatario o un enlace secreto adicional.
- El propietario podrá revocar el acceso.
- Se registrará como máximo la información necesaria: fecha de primera apertura y estado del regalo.
- No se expondrán secretos completos en logs, mensajes de error, analítica ni URLs.
- El QR generado no debe quedar almacenado en cachés públicas.
- Los intentos de revelación deberán tener limitación de frecuencia.

Opciones de protección configurables:

- Sin protección adicional: apropiado solo para regalos sin valor sensible.
- PIN del destinatario.
- Enlace secreto de un solo propósito.
- Una sola revelación, con advertencia explícita sobre sus consecuencias.

El sistema no puede garantizar que una tienda acepte el código ni impedir que el destinatario haga una captura una vez revelado.

## 6. Acceso y permisos

### Propietario autenticado

Puede:

- Abrir su álbum completo.
- Crear, editar, ordenar y eliminar páginas.
- Configurar música general y música por página.
- Subir archivos y agregar enlaces.
- Crear, editar, revelar para prueba, revocar y eliminar regalos.
- Crear o revocar enlaces compartidos.
- Consultar estados básicos de regalos.

### Visitante de una página compartida

Puede:

- Ver únicamente la página correspondiente al enlace.
- Reproducir su contenido multimedia.
- Abrir un regalo cuando las reglas de protección lo permitan.

No puede:

- Navegar a otras páginas.
- Editar el contenido.
- Acceder al panel administrativo.
- Obtener datos internos del propietario.
- Consultar otros regalos o enlaces del álbum.

## 7. Experiencia de edición propuesta

Dentro de **Editar recuerdo** se agregarán secciones independientes:

- Datos de la página.
- Música de esta página.
- Archivos del dispositivo.
- Contenido mediante enlaces.
- Regalos.

Acciones principales:

- **Agregar fotos o videos**.
- **Agregar mediante enlace**.
- **Elegir música**.
- **Agregar regalo**.
- **Previsualizar como destinatario**.
- **Guardar cambios**.

Cada elemento tendrá, según corresponda:

- Previsualización.
- Nombre o título.
- Tipo y proveedor.
- Estado de disponibilidad.
- Controles para ordenar, editar y eliminar.

## 8. Modelo conceptual de datos

Los nombres definitivos se decidirán durante la implementación.

### Extensión de página

- Música propia opcional.
- Proveedor musical.
- Identificador normalizado del recurso.
- Preferencia de inicio/reproducción, si el proveedor lo permite.

### Recurso multimedia externo

- Página propietaria.
- Tipo: imagen, GIF, video, audio o publicación.
- URL original.
- Proveedor reconocido.
- Identificador externo normalizado.
- URL segura de inserción o visualización.
- Título y texto alternativo.
- Posición.
- Estado de validación.
- Fecha de creación y última comprobación.

### Regalo digital

- Página propietaria.
- Título, mensaje y proveedor.
- Tipo de secreto: QR, URL o código.
- Secreto cifrado.
- Imagen de presentación opcional.
- Fecha de vencimiento.
- Método de protección.
- Hash del PIN opcional.
- Estado.
- Fecha de primera apertura, reclamación o revocación.
- Identificador público aleatorio no predecible.

No se almacenarán contraseñas, PIN ni códigos de regalo en texto plano.

## 9. Seguridad técnica

### URLs externas

- Validar protocolo, longitud y formato.
- Mantener una lista explícita de proveedores y dominios permitidos.
- Evitar solicitudes del servidor a direcciones locales, privadas o de metadatos para prevenir SSRF.
- Aplicar tiempos límite, límites de tamaño y restricciones de red al obtener metadatos.
- Escapar títulos, descripciones y nombres antes de renderizarlos.
- Restringir `iframe` mediante `sandbox`, `allow` y una política CSP adecuada.
- No seguir redirecciones hacia dominios no autorizados.

### Sesiones y autorización

- Todas las operaciones de escritura requieren la sesión DPIA del propietario.
- Las acciones administrativas mantienen la protección administrativa vigente.
- Cada consulta debe comprobar que álbum, página, medio o regalo pertenecen al usuario autenticado.
- Los endpoints públicos solo aceptan identificadores firmados o aleatorios no predecibles.
- Cerrar sesión invalida el acceso al álbum completo, pero no altera enlaces compartidos existentes.

### Archivos y QR

- Mantener límites de tamaño y tipos admitidos.
- Validar el contenido real, no solo la extensión o MIME enviado por el navegador.
- Tratar el contenido decodificado de un QR como dato no confiable.
- Nunca abrir automáticamente la URL de un QR.
- Solicitar confirmación antes de guardar o visitar un destino detectado.

## 10. Compatibilidad y migración

- La música general actual continuará funcionando.
- Las páginas sin música propia heredarán la música general.
- Los archivos existentes conservarán su comportamiento.
- Los enlaces compartidos existentes seguirán mostrando una sola página.
- Las nuevas tablas o columnas serán opcionales inicialmente y se crearán mediante una migración idempotente.
- Un fallo de un proveedor externo no debe afectar archivos almacenados en el álbum.
- Ningún regalo existente se migrará automáticamente desde una imagen común sin confirmación del propietario.

## 11. Fases recomendadas

### Fase 1: música por página

- Campo musical en cada página.
- Herencia de la música general.
- Cambio y detención al navegar.
- Previsualización y validación de Spotify/YouTube.

### Fase 2: multimedia mediante enlaces

- Imágenes directas, GIF, YouTube y Vimeo.
- Previsualización antes de guardar.
- Lista de proveedores permitidos.
- Orden y eliminación de recursos externos.

### Fase 3: tarjetas de regalo

- Crear tarjetas con mensaje e imagen.
- Admitir QR subido, QR escaneado y enlace/código.
- Generar QR en el servidor o cliente de forma controlada.
- Cifrar el secreto y separarlo de la respuesta pública.

### Fase 4: entrega protegida

- PIN o enlace secreto.
- Revelación controlada.
- Estados abierto, reclamado, vencido y revocado.
- Registro mínimo de eventos y limitación de intentos.

### Fase 5: mejoras opcionales

- Reordenamiento mediante arrastrar y soltar.
- Portada personalizada para cada regalo.
- Fecha programada de disponibilidad.
- Notificación opcional al propietario cuando se descubre el regalo.
- Nuevos proveedores mediante adaptadores independientes.

## 12. Criterios de aceptación generales

La funcionalidad se considerará completa cuando:

- Una página pueda usar música propia o heredar la general sin afectar otras páginas.
- El propietario pueda pegar un enlace compatible, previsualizarlo y guardarlo.
- Una URL no compatible sea rechazada claramente y sin comprometer el servidor.
- Archivos locales y recursos externos puedan convivir y ordenarse en una misma página.
- Una página compartida siga siendo accesible sin login y no revele otras páginas.
- Un regalo protegido no exponga su secreto en el HTML o JSON inicial de la página.
- El destinatario pueda descubrir un regalo desde celular y escritorio.
- El propietario pueda revocar un regalo o enlace compartido.
- Los álbumes existentes continúen funcionando después de la migración.
- Existan pruebas de autorización, aislamiento entre usuarios, validación de proveedores, cifrado y revelación de regalos.

## 13. Decisiones pendientes antes de implementar

1. Qué proveedores externos se admitirán en la primera versión.
2. Si las imágenes remotas se mostrarán desde su origen o se copiarán al almacenamiento propio.
3. Si el propietario podrá elegir reproducción automática por página.
4. Qué protección de regalo será obligatoria cuando exista valor monetario.
5. Qué significa exactamente “reclamado”: confirmación manual o integración con la tienda.
6. Si los enlaces compartidos podrán revocarse y regenerarse individualmente.
7. Cuánto tiempo se conservarán los eventos de apertura.
8. Si se enviarán notificaciones y mediante qué canal.
9. Qué política se aplicará a contenido externo que desaparezca o cambie.
10. Si la primera versión permitirá varios regalos por página.

## 14. Fuera de alcance inicial

- Procesar pagos o vender tarjetas de regalo directamente.
- Garantizar saldo, validez o canje en sistemas de terceros.
- Descargar contenido protegido de redes sociales.
- Insertar cualquier sitio web sin validación.
- Reproducir música automáticamente cuando el navegador lo prohíba.
- Impedir capturas de pantalla después de revelar un regalo.
- Analítica invasiva o rastreo detallado del destinatario.

## 15. Resultado esperado

El propietario podrá crear una página emocional completa: escribir un recuerdo, elegir su música, combinar archivos propios con imágenes, GIF o videos externos y añadir un regalo digital que el destinatario descubre de manera segura.

La ampliación debe conservar la esencia del álbum actual: personal, sencilla, privada y fácil de compartir.
