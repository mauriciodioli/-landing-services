/* DPIA Solutions — internacionalización ES / IT / EN */
(function () {
  'use strict';

  const STORAGE_KEY = 'dpia-language';
  const supportedLanguages = ['es', 'it', 'en'];

  const translations = {
    es: {
      language: 'Idioma',
      menu: 'Menú',
      closeMenu: 'Cerrar menú',
      problems: 'Problemas',
      method: 'Método',
      services: 'Servicios',
      experience: 'Experiencia',
      onlineCourses: 'Cursos online',
      courseMarketing: 'IA y sistemas automáticos',
      courseProcesses: 'IA para procesos y decisiones',
      courseMasterclass: 'Del mundo físico a la IA',
      contact: 'Contacto',
      team: 'Equipo',
      initialConversation: 'Conversación inicial',
      heroTitle: 'Soluciones digitales para industria y comercio',
      heroText: 'Analizamos procesos, tecnología y comunicación para identificar dónde tu empresa pierde tiempo, dinero u oportunidades antes de que inviertas en la solución equivocada.',
      heroButton: 'Solicitar conversación inicial',
      supportRole: 'SOPORTE COMERCIAL Y TÉCNICO · CONO SUR',
      supportName: 'Jorge Rivolta',
      supportDescription: 'Soporte comercial y técnico de DPIA para acompañar oportunidades, clientes e implementaciones en Argentina, Brasil y Uruguay.',
      supportRegions: 'Argentina · Brasil · Uruguay · atención comercial · soporte técnico',
      privacy: 'Política de privacidad',
      whatsappMessage: 'Hola, quiero analizar una oportunidad de mejora en mi empresa.'
    },
    it: {
      language: 'Lingua',
      menu: 'Menu',
      closeMenu: 'Chiudi menu',
      problems: 'Problemi',
      method: 'Metodo',
      services: 'Servizi',
      experience: 'Esperienza',
      onlineCourses: 'Corsi online',
      courseMarketing: 'IA e sistemi automatici',
      courseProcesses: 'IA per processi e decisioni',
      courseMasterclass: 'Dal mondo fisico all’IA',
      contact: 'Contatti',
      team: 'Team',
      initialConversation: 'Conversazione iniziale',
      heroTitle: 'Soluzioni digitali per l’industria e il commercio',
      heroText: 'Analizziamo processi, tecnologia e comunicazione per individuare dove la tua azienda perde tempo, denaro o opportunità, prima che investa nella soluzione sbagliata.',
      heroButton: 'Richiedi una conversazione iniziale',
      supportRole: 'SUPPORTO COMMERCIALE E TECNICO · CONO SUD',
      supportName: 'Jorge Rivolta',
      supportDescription: 'Supporto commerciale e tecnico DPIA per seguire opportunità, clienti e implementazioni in Argentina, Brasile e Uruguay.',
      supportRegions: 'Argentina · Brasile · Uruguay · assistenza commerciale · supporto tecnico',
      privacy: 'Informativa sulla privacy',
      whatsappMessage: 'Ciao, vorrei analizzare un’opportunità di miglioramento nella mia azienda.'
    },
    en: {
      language: 'Language',
      menu: 'Menu',
      closeMenu: 'Close menu',
      problems: 'Problems',
      method: 'Method',
      services: 'Services',
      experience: 'Experience',
      onlineCourses: 'Online courses',
      courseMarketing: 'AI and automated systems',
      courseProcesses: 'AI for processes and decisions',
      courseMasterclass: 'From the physical world to AI',
      contact: 'Contact',
      team: 'Team',
      initialConversation: 'Initial conversation',
      heroTitle: 'Digital solutions for industry and commerce',
      heroText: 'We analyze processes, technology and communication to identify where your company loses time, money or opportunities before you invest in the wrong solution.',
      heroButton: 'Request an initial conversation',
      supportRole: 'COMMERCIAL AND TECHNICAL SUPPORT · SOUTHERN CONE',
      supportName: 'Jorge Rivolta',
      supportDescription: 'DPIA commercial and technical support for opportunities, customers and implementations in Argentina, Brazil and Uruguay.',
      supportRegions: 'Argentina · Brazil · Uruguay · commercial assistance · technical support',
      privacy: 'Privacy policy',
      whatsappMessage: 'Hello, I would like to analyze an improvement opportunity in my company.'
    }
  };

  function normalizeLanguage(language) {
    const normalized = String(language || '').slice(0, 2).toLowerCase();
    return supportedLanguages.includes(normalized) ? normalized : 'es';
  }

  function translate(language, key) {
    const lang = normalizeLanguage(language);
    return translations[lang][key] || translations.es[key] || key;
  }

  function applyLanguage(language) {
    const lang = normalizeLanguage(language);
    document.documentElement.lang = lang;
    localStorage.setItem(STORAGE_KEY, lang);

    document.querySelectorAll('[data-i18n]').forEach((element) => {
      element.textContent = translate(lang, element.dataset.i18n);
    });

    document.querySelectorAll('[data-i18n-aria-label]').forEach((element) => {
      element.setAttribute('aria-label', translate(lang, element.dataset.i18nAriaLabel));
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach((element) => {
      element.setAttribute('placeholder', translate(lang, element.dataset.i18nPlaceholder));
    });

    document.querySelectorAll('.language-switch button').forEach((button) => {
      const isActive = button.textContent.trim().toLowerCase() === lang;
      button.classList.toggle('active', isActive);
      button.setAttribute('aria-pressed', String(isActive));
    });

    document.querySelectorAll('a[href*="wa.me/"][href*="text="]').forEach((link) => {
      const url = new URL(link.href);
      url.searchParams.set('text', translate(lang, 'whatsappMessage'));
      link.href = url.toString();
    });

    document.dispatchEvent(new CustomEvent('dpia:languagechange', { detail: { lang } }));
    return lang;
  }

  function initialize() {
    document.querySelectorAll('.language-switch button').forEach((button) => {
      button.removeAttribute('title');
      button.addEventListener('click', () => applyLanguage(button.textContent));
    });

    const savedLanguage = localStorage.getItem(STORAGE_KEY);
    const browserLanguage = navigator.language || 'es';
    applyLanguage(savedLanguage || browserLanguage);
  }

  window.DPIAI18n = {
    translations,
    t: (key, language) => translate(language || document.documentElement.lang, key),
    setLanguage: applyLanguage,
    getLanguage: () => normalizeLanguage(document.documentElement.lang)
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
  } else {
    initialize();
  }
})();

/* Full-page content translations. Every translated node is marked data-i18n-auto. */
(function () {
  'use strict';
  const rows = `
Servicios y ofertas|Services and offers|Servizi e offerte
Diagnóstico de oportunidades|Opportunity assessment|Analisi delle opportunità
Auditoría técnico-comercial|Technical and commercial audit|Audit tecnico-commerciale
Sprint de implementación|Implementation sprint|Sprint di implementazione
Acompañamiento mensual|Monthly support|Supporto mensile
Áreas de intervención|Areas of intervention|Aree di intervento
Monitorización industrial|Industrial monitoring|Monitoraggio industriale
Desarrollo full stack|Full-stack development|Sviluppo full stack
Mercadotecnia técnica|Technical marketing|Marketing tecnico
Método DPIA|DPIA method|Metodo DPIA
Diagnóstico|Assessment|Analisi
Auditoría|Audit|Audit
Priorización|Prioritization|Definizione delle priorità
Implementación|Implementation|Implementazione
Conocé DPIA|Discover DPIA|Scopri DPIA
Justificación de inversión|Investment rationale|Giustificazione dell’investimento
Empecemos por el problema, no por la tecnología.|Let’s start with the problem, not the technology.|Partiamo dal problema, non dalla tecnologia.
Hablar con DPIA →|Talk to DPIA →|Parla con DPIA →
PROCESOS · TECNOLOGÍA · COMERCIALIZACIÓN|PROCESSES · TECHNOLOGY · COMMERCIALIZATION|PROCESSI · TECNOLOGIA · COMMERCIALIZZAZIONE
Conocer el método DPIA|Discover the DPIA method|Scopri il metodo DPIA
Procesos · Tecnología · Automatización · IA aplicada · UX · Comercialización|Processes · Technology · Automation · Applied AI · UX · Commercialization|Processi · Tecnologia · Automazione · IA applicata · UX · Commercializzazione
DIAGNÓSTICO ANTES QUE TECNOLOGÍA|ASSESSMENT BEFORE TECHNOLOGY|ANALISI PRIMA DELLA TECNOLOGIA
¿Qué está frenando a tu empresa?|What is holding your company back?|Cosa sta frenando la tua azienda?
No vendemos proyectos genéricos. Identificamos el costo empresarial del problema y definimos qué conviene resolver primero.|We do not sell generic projects. We identify the business cost of the problem and determine what should be solved first.|Non vendiamo progetti generici. Identifichiamo il costo aziendale del problema e definiamo cosa conviene risolvere per primo.
Procesos manuales|Manual processes|Processi manuali
Consumen horas, generan errores y vuelven el crecimiento dependiente de más carga administrativa.|They consume hours, generate errors and make growth dependent on more administrative work.|Consumano ore, generano errori e rendono la crescita dipendente da un maggiore carico amministrativo.
Sistemas desconectados|Disconnected systems|Sistemi scollegati
CRM, ERP, pagos y plataformas aisladas reducen velocidad, control y trazabilidad.|Isolated CRM, ERP, payment systems and platforms reduce speed, control and traceability.|CRM, ERP, pagamenti e piattaforme isolate riducono velocità, controllo e tracciabilità.
Datos desaprovechados|Underused data|Dati non sfruttati
La información existe, pero no ayuda a decidir ni anticipar problemas.|The information exists, but it does not help make decisions or anticipate problems.|Le informazioni esistono, ma non aiutano a decidere né ad anticipare i problemi.
Plataformas frágiles|Fragile platforms|Piattaforme fragili
Mantener, integrar o escalar cuesta más de lo que debería y bloquea nuevas oportunidades.|Maintaining, integrating or scaling costs more than it should and blocks new opportunities.|Mantenere, integrare o scalare costa più del necessario e blocca nuove opportunità.
IA sin caso de uso|AI without a use case|IA senza un caso d’uso
Invertir sin objetivos, datos y control claros aumenta el riesgo y desperdicia presupuesto.|Investing without clear objectives, data and control increases risk and wastes budget.|Investire senza obiettivi, dati e controllo chiari aumenta il rischio e spreca budget.
Valor difícil de explicar|Value that is hard to explain|Valore difficile da spiegare
Un buen producto pierde ventas cuando el mercado no comprende rápido por qué debería elegirlo.|A good product loses sales when the market does not quickly understand why it should choose it.|Un buon prodotto perde vendite quando il mercato non capisce rapidamente perché dovrebbe sceglierlo.
PROCESOS Y DATOS|PROCESSES AND DATA|PROCESSI E DATI
Ver la operación completa permite decidir qué mejorar primero.|Seeing the complete operation helps decide what to improve first.|Vedere l’intera operatività permette di decidere cosa migliorare per primo.
Explorar sistemas industriales →|Explore industrial systems →|Esplora i sistemi industriali →
Claridad antes de invertir|Clarity before investing|Chiarezza prima di investire
Conocer las ofertas →|Explore our offers →|Scopri le offerte →
Del roadmap a una mejora funcional.|From roadmap to a working improvement.|Dalla roadmap a un miglioramento funzionante.
Automatización, integración, datos, IA, UX o comercialización según el problema real.|Automation, integration, data, AI, UX or commercialization according to the real problem.|Automazione, integrazione, dati, IA, UX o commercializzazione in base al problema reale.
Ver el método →|See the method →|Vedi il metodo →
Primero entendemos. Después priorizamos. Finalmente implementamos.|First we understand. Then we prioritize. Finally, we implement.|Prima comprendiamo. Poi definiamo le priorità. Infine implementiamo.
No recomendamos tecnología por moda. Proponemos únicamente acciones coherentes con el proceso y los objetivos reales.|We do not recommend technology because it is fashionable. We only propose actions aligned with the process and real objectives.|Non consigliamo tecnologie per moda. Proponiamo solo azioni coerenti con il processo e gli obiettivi reali.
Comprendemos la situación, el problema y los objetivos.|We understand the situation, the problem and the objectives.|Comprendiamo la situazione, il problema e gli obiettivi.
Analizamos flujos, personas, sistemas, datos y fricciones.|We analyze workflows, people, systems, data and friction.|Analizziamo flussi, persone, sistemi, dati e attriti.
Evaluamos impacto, urgencia, esfuerzo, costo y riesgo.|We evaluate impact, urgency, effort, cost and risk.|Valutiamo impatto, urgenza, impegno, costo e rischio.
Ejecutamos una mejora o acompañamos al equipo responsable.|We implement an improvement or support the team responsible.|Realizziamo un miglioramento o affianchiamo il team responsabile.
01 · SISTEMAS INDUSTRIALES|01 · INDUSTRIAL SYSTEMS|01 · SISTEMI INDUSTRIALI
De la máquina a una operación visible y controlable.|From the machine to a visible, controllable operation.|Dalla macchina a un’operatività visibile e controllabile.
DPIA desarrolla sistemas para fabricantes y plantas industriales que capturan datos de PLC y sensores, los procesan y muestran producción, fallos y rendimiento en tiempo real.|DPIA develops systems for manufacturers and industrial plants that capture PLC and sensor data, process it, and display production, failures and performance in real time.|DPIA sviluppa sistemi per costruttori e stabilimenti industriali che acquisiscono dati da PLC e sensori, li elaborano e mostrano produzione, guasti e prestazioni in tempo reale.
QUÉ|WHAT|COSA
DÓNDE|WHERE|DOVE
PARA QUIÉN|FOR WHOM|PER CHI
CÓMO|HOW|COME
ENTREGABLE|DELIVERABLE|CONSEGNA
Monitorización y control de maquinaria|Machinery monitoring and control|Monitoraggio e controllo dei macchinari
Producción, estados, ciclos, alarmas, variables físicas, consumo, calidad y fallos.|Production, status, cycles, alarms, physical variables, consumption, quality and failures.|Produzione, stati, cicli, allarmi, variabili fisiche, consumi, qualità e guasti.
Fábricas y plantas industriales|Factories and industrial plants|Fabbriche e stabilimenti industriali
Máquinas individuales, líneas productivas, bancos de prueba y equipamiento conectado.|Individual machines, production lines, test benches and connected equipment.|Macchine singole, linee produttive, banchi prova e apparecchiature connesse.
Fabricantes y responsables de producción|Manufacturers and production managers|Costruttori e responsabili di produzione
Equipos que necesitan trazabilidad, diagnóstico y decisiones basadas en datos reales.|Teams that need traceability, diagnostics and decisions based on real data.|Team che necessitano di tracciabilità, diagnosi e decisioni basate su dati reali.
PLC, sensores y comunicación industrial|PLC, sensors and industrial communication|PLC, sensori e comunicazione industriale
Adquisición mediante interfaces industriales, TCP/IP, serial, I2C, APIs y WebSockets.|Acquisition through industrial interfaces, TCP/IP, serial, I2C, APIs and WebSockets.|Acquisizione tramite interfacce industriali, TCP/IP, seriale, I2C, API e WebSocket.
Un sistema funcionando en producción|A system running in production|Un sistema operativo in produzione
Captura de datos, visualización, alertas, registro histórico y documentación técnica.|Data capture, visualization, alerts, historical records and technical documentation.|Acquisizione dati, visualizzazione, avvisi, storico e documentazione tecnica.
02 · DESARROLLO FULL STACK|02 · FULL-STACK DEVELOPMENT|02 · SVILUPPO FULL STACK
Construimos la plataforma que convierte los datos industriales en una herramienta operativa.|We build the platform that turns industrial data into an operational tool.|Costruiamo la piattaforma che trasforma i dati industriali in uno strumento operativo.
No entregamos una pantalla aislada. Desarrollamos el recorrido completo desde la adquisición del dato hasta una aplicación segura y desplegada.|We do not deliver an isolated screen. We develop the complete journey from data acquisition to a secure, deployed application.|Non consegniamo una schermata isolata. Sviluppiamo l’intero percorso, dall’acquisizione del dato a un’applicazione sicura e distribuita.
Consultar un desarrollo full stack →|Discuss a full-stack development →|Richiedi uno sviluppo full stack →
MÁQUINA|MACHINE|MACCHINA
DATOS|DATA|DATI
APLICACIÓN|APPLICATION|APPLICAZIONE
PRODUCCIÓN|PRODUCTION|PRODUZIONE
QUÉ DESARROLLAMOS|WHAT WE DEVELOP|COSA SVILUPPIAMO
Aplicaciones web operativas|Operational web applications|Applicazioni web operative
Dashboards, paneles de control, gestión de usuarios, reportes, alarmas y flujos de trabajo.|Dashboards, control panels, user management, reports, alarms and workflows.|Dashboard, pannelli di controllo, gestione utenti, report, allarmi e flussi di lavoro.
TECNOLOGÍAS|TECHNOLOGIES|TECNOLOGIE
Frontend, backend e infraestructura|Frontend, backend and infrastructure|Frontend, backend e infrastruttura
Aplicación desplegada y documentada|Deployed and documented application|Applicazione distribuita e documentata
Código fuente, base de datos, APIs, interfaz, contenedores y procedimiento de despliegue.|Source code, database, APIs, interface, containers and deployment procedure.|Codice sorgente, database, API, interfaccia, container e procedura di distribuzione.
03 · MERCADOTECNIA TÉCNICA|03 · TECHNICAL MARKETING|03 · MARKETING TECNICO
DPIA convierte soluciones complejas en ofertas claras y fáciles de comprar.|DPIA turns complex solutions into clear offers that are easy to buy.|DPIA trasforma soluzioni complesse in offerte chiare e facili da acquistare.
Para fabricantes, empresas industriales y productos tecnológicos que tienen una solución valiosa, pero no logran comunicar con claridad el problema que resuelven.|For manufacturers, industrial companies and technology products with a valuable solution that struggle to clearly communicate the problem they solve.|Per produttori, aziende industriali e prodotti tecnologici con una soluzione di valore, che non riescono a comunicare chiaramente il problema che risolvono.
POSICIONAMIENTO|POSITIONING|POSIZIONAMENTO
CONVERSIÓN|CONVERSION|CONVERSIONE
MATERIALES|MATERIALS|MATERIALI
ADOPCIÓN|ADOPTION|ADOZIONE
Definición de cliente, problema, diferenciación y propuesta de valor.|Definition of customer, problem, differentiation and value proposition.|Definizione di cliente, problema, differenziazione e proposta di valore.
Landing page, estructura de oferta, llamadas a la acción y recorrido comercial.|Landing page, offer structure, calls to action and sales journey.|Landing page, struttura dell’offerta, call to action e percorso commerciale.
Presentación comercial, fichas de servicio, contenidos y guion de demostración.|Sales presentation, service sheets, content and demonstration script.|Presentazione commerciale, schede di servizio, contenuti e copione dimostrativo.
UX, onboarding, capacitación y mensajes para usuarios y equipos internos.|UX, onboarding, training and messaging for users and internal teams.|UX, onboarding, formazione e messaggi per utenti e team interni.
Un sistema comercial listo para presentar y vender la solución.|A commercial system ready to present and sell the solution.|Un sistema commerciale pronto per presentare e vendere la soluzione.
Mensaje central, oferta, landing o material comercial y recomendaciones de adopción.|Core message, offer, landing page or sales material and adoption recommendations.|Messaggio centrale, offerta, landing o materiale commerciale e raccomandazioni per l’adozione.
OFERTAS CONCRETAS|CONCRETE OFFERS|OFFERTE CONCRETE
Comprá claridad antes de comprar complejidad.|Buy clarity before buying complexity.|Acquista chiarezza prima di acquistare complessità.
3 a 5 días|3 to 5 days|Da 3 a 5 giorni
7 a 15 días|7 to 15 days|Da 7 a 15 giorni
2 a 4 semanas|2 to 4 weeks|Da 2 a 4 settimane
Mensual|Monthly|Mensile
Revisión inicial e identificación de 5 a 10 oportunidades con el siguiente paso recomendado.|Initial review and identification of 5 to 10 opportunities with the recommended next step.|Revisione iniziale e identificazione di 5-10 opportunità con il passo successivo consigliato.
Entrevistas, mapa de procesos, riesgos, prioridades y roadmap de implementación.|Interviews, process map, risks, priorities and implementation roadmap.|Interviste, mappa dei processi, rischi, priorità e roadmap di implementazione.
Automatización, integración, dashboard, mejora técnica, UX o mejora comercial concreta.|Automation, integration, dashboard, technical improvement, UX or a concrete commercial improvement.|Automazione, integrazione, dashboard, miglioramento tecnico, UX o miglioramento commerciale concreto.
Acompañamiento|Ongoing support|Supporto
Dirección técnica y comercial externa, priorización y capacidad reservada cada mes.|External technical and commercial leadership, prioritization and reserved capacity each month.|Direzione tecnica e commerciale esterna, definizione delle priorità e capacità riservata ogni mese.
Los proyectos complejos se dividen en fases. Nunca se cotiza una implementación extensa sin comprender primero el alcance, los riesgos y las dependencias.|Complex projects are divided into phases. We never quote an extensive implementation without first understanding its scope, risks and dependencies.|I progetti complessi vengono suddivisi in fasi. Non preventiviamo mai un’implementazione estesa senza prima comprenderne ambito, rischi e dipendenze.
CAPACIDADES COMPLEMENTARIAS|COMPLEMENTARY CAPABILITIES|COMPETENZE COMPLEMENTARI
Experiencia sénior, técnica y comercial.|Senior technical and commercial experience.|Esperienza senior, tecnica e commerciale.
TECNOLOGÍA · ARQUITECTURA · IMPLEMENTACIÓN|TECHNOLOGY · ARCHITECTURE · IMPLEMENTATION|TECNOLOGIA · ARCHITETTURA · IMPLEMENTAZIONE
Ingeniero informático con más de 20 años de experiencia en software, embedded, automatización, backend, datos, IA e integración industrial.|Computer engineer with more than 20 years of experience in software, embedded systems, automation, backend, data, AI and industrial integration.|Ingegnere informatico con oltre 20 anni di esperienza in software, sistemi embedded, automazione, backend, dati, IA e integrazione industriale.
COMERCIALIZACIÓN · UX · ADOPCIÓN|COMMERCIALIZATION · UX · ADOPTION|COMMERCIALIZZAZIONE · UX · ADOZIONE
Especialista en posicionamiento, comunicación, experiencia de usuario, conversión y adopción de soluciones digitales.|Specialist in positioning, communication, user experience, conversion and adoption of digital solutions.|Specialista in posizionamento, comunicazione, esperienza utente, conversione e adozione di soluzioni digitali.
Propuesta de valor · marketing digital · UX · contenidos · conversión · capacitación|Value proposition · digital marketing · UX · content · conversion · training|Proposta di valore · marketing digitale · UX · contenuti · conversione · formazione
Python · C/C++ · Java · APIs · SQL · Docker · AWS · PLC · IoT · datos en tiempo real|Python · C/C++ · Java · APIs · SQL · Docker · AWS · PLC · IoT · real-time data|Python · C/C++ · Java · API · SQL · Docker · AWS · PLC · IoT · dati in tempo reale
EXPERIENCIA TÉCNICA APLICADA|APPLIED TECHNICAL EXPERIENCE|ESPERIENZA TECNICA APPLICATA
EXPERIENCIA APLICADA|APPLIED EXPERIENCE|ESPERIENZA APPLICATA
Industria · plataformas · datos|Industry · platforms · data|Industria · piattaforme · dati
De la industria al cloud.|From industry to the cloud.|Dall’industria al cloud.
Sistemas de control, adquisición de datos, monitorización y mejora de procesos para maquinaria industrial en condiciones reales.|Control systems, data acquisition, monitoring and process improvement for industrial machinery in real-world conditions.|Sistemi di controllo, acquisizione dati, monitoraggio e miglioramento dei processi per macchinari industriali in condizioni reali.
Plataforma internacional end-to-end con backend, microservicios, pagos, IA, WebSockets y despliegue cloud.|International end-to-end platform with backend, microservices, payments, AI, WebSockets and cloud deployment.|Piattaforma internazionale end-to-end con backend, microservizi, pagamenti, IA, WebSocket e distribuzione cloud.
Sistemas embedded, procesamiento de datos, computación de alto rendimiento e investigación industrial y aeroespacial.|Embedded systems, data processing, high-performance computing, and industrial and aerospace research.|Sistemi embedded, elaborazione dati, calcolo ad alte prestazioni e ricerca industriale e aerospaziale.
Ver experiencia visual|View visual experience|Vedi l’esperienza visiva
Los detalles y resultados específicos se comparten durante la conversación cuando las condiciones de confidencialidad lo permiten.|Specific details and results are shared during the conversation when confidentiality conditions allow.|Dettagli e risultati specifici vengono condivisi durante la conversazione quando le condizioni di riservatezza lo consentono.
JUSTIFICACIÓN DE LA INVERSIÓN|INVESTMENT RATIONALE|GIUSTIFICAZIONE DELL’INVESTIMENTO
Una mejora debe poder justificarse.|An improvement must be justifiable.|Un miglioramento deve poter essere giustificato.
Evaluamos horas recuperables, errores evitables, tiempos de respuesta, oportunidades perdidas, duplicación de datos, riesgos y capacidad liberada.|We evaluate recoverable hours, avoidable errors, response times, lost opportunities, duplicated data, risks and freed capacity.|Valutiamo ore recuperabili, errori evitabili, tempi di risposta, opportunità perse, duplicazione dei dati, rischi e capacità liberata.
semanales|per week|settimanali
son más de|amount to more than|sono più di
80 horas mensuales|80 hours per month|80 ore al mese
. Antes de automatizar, calculamos el costo actual, el esfuerzo y el tiempo estimado de recuperación.|. Before automating, we calculate the current cost, effort and estimated payback time.|. Prima di automatizzare, calcoliamo il costo attuale, l’impegno e il tempo stimato di recupero.
CONVERSACIÓN INICIAL · 30 MINUTOS|INITIAL CONVERSATION · 30 MINUTES|CONVERSAZIONE INIZIALE · 30 MINUTI
Identificaremos el proceso más costoso, los sistemas involucrados, la urgencia y el siguiente paso más razonable.|We will identify the most costly process, the systems involved, the urgency and the most reasonable next step.|Individueremo il processo più costoso, i sistemi coinvolti, l’urgenza e il passo successivo più ragionevole.
Hablar con DPIA por WhatsApp ↗|Talk to DPIA on WhatsApp ↗|Parla con DPIA su WhatsApp ↗
Italia / Unión Europea / Remoto|Italy / European Union / Remote|Italia / Unione Europea / Da remoto
Procesos · Tecnología · Comercialización|Processes · Technology · Commercialization|Processi · Tecnologia · Commercializzazione
Navegación|Navigation|Navigazione
Conversación inicial|Initial conversation|Conversazione iniziale
Equipo|Team|Team
Experiencia|Experience|Esperienza
APIs · reglas · tiempo real|APIs · rules · real time|API · regole · tempo reale
Dashboard · alertas · usuarios|Dashboard · alerts · users|Dashboard · avvisi · utenti
PLC · sensores · dispositivos|PLC · sensors · devices|PLC · sensori · dispositivi
SQL · históricos · analítica|SQL · history · analytics|SQL · dati storici · analisi
HTML/CSS/JavaScript, Python, Flask, Java, SQL, REST APIs, WebSockets, Docker y AWS.|HTML/CSS/JavaScript, Python, Flask, Java, SQL, REST APIs, WebSockets, Docker and AWS.|HTML/CSS/JavaScript, Python, Flask, Java, SQL, API REST, WebSocket, Docker e AWS.
Desde €1.500 + IVA|From €1,500 + VAT|Da €1.500 + IVA
Desde €4.000 + IVA|From €4,000 + VAT|Da €4.000 + IVA
Desde €5.000 + IVA|From €5,000 + VAT|Da €5.000 + IVA
Desde €3.000 + IVA / mes|From €3,000 + VAT / month|Da €3.000 + IVA / mese
`.trim().split('\n');
  const dictionaries = { en: Object.create(null), it: Object.create(null) };
  rows.forEach(function (row) {
    const parts = row.split('|');
    if (parts.length === 3) { dictionaries.en[parts[0]] = parts[1]; dictionaries.it[parts[0]] = parts[2]; }
  });
  const originals = new WeakMap();
  function apply(lang) {
    lang = ['es', 'it', 'en'].includes(lang) ? lang : 'es';
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      const parent = node.parentElement;
      if (!parent || ['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(parent.tagName) || parent.closest('[data-i18n]')) continue;
      if (!originals.has(node)) originals.set(node, node.nodeValue);
      const original = originals.get(node);
      const source = original.trim();
      if (!source) continue;
      const value = lang === 'es' ? source : dictionaries[lang][source];
      if (value) {
        node.nodeValue = original.replace(source, value);
        parent.dataset.i18nAuto = source;
      } else if (lang === 'es') node.nodeValue = original;
    }
  }
  document.addEventListener('dpia:languagechange', function (event) { apply(event.detail.lang); });
  function initialize() { apply((localStorage.getItem('dpia-language') || document.documentElement.lang || 'es').slice(0, 2)); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize); else initialize();
})();