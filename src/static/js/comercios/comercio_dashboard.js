document.addEventListener('DOMContentLoaded', () => {
    cargarConfiguracionCuenta();
    // Intentar obtener geolocalización al cargar la página para tener lat/lon disponibles
    try{
        if(navigator && navigator.geolocation){
            navigator.geolocation.getCurrentPosition(pos=>{
                try{
                    const glat = pos.coords.latitude;
                    const glon = pos.coords.longitude;
                    localStorage.setItem('latitud', glat);
                    localStorage.setItem('longitud', glon);
                    console.log('Geoloc inicial guardada en localStorage', glat, glon);
                }catch(e){ console.warn('error guardando geoloc inicial', e); }
            }, err=>{ console.warn('geoloc inicial denegada o falló', err); }, {timeout:5000});
        }
    }catch(e){ console.warn('geoloc no disponible', e); }
    // Poblado inicial de KPIs desde localStorage (si existe)
    try{ populateKpisFromLocalStorage(); }catch(e){console.warn('populateKpisFromLocalStorage fallo', e);} 
    cargarDashboard();
    // When login modal is shown, request geolocation and store lat/lon in localStorage
    try{
        const loginModal = document.getElementById('modalLoginComercio');
        if(loginModal){
            loginModal.addEventListener('shown.bs.modal', ()=>{
                try{
                    if(navigator && navigator.geolocation){
                        navigator.geolocation.getCurrentPosition(pos=>{
                            try{
                                const glat = pos.coords.latitude;
                                const glon = pos.coords.longitude;
                                localStorage.setItem('latitud', glat);
                                localStorage.setItem('longitud', glon);
                                console.log('Geoloc (modal) guardada en localStorage', glat, glon);
                                // populate create/cfg inputs if present and empty
                                const clat = document.getElementById('create-lat');
                                const clon = document.getElementById('create-lon');
                                const flat = document.getElementById('cfg-lat');
                                const flon = document.getElementById('cfg-lon');
                                if(clat && (!clat.value || clat.value.trim()==='')) clat.value = glat;
                                if(clon && (!clon.value || clon.value.trim()==='')) clon.value = glon;
                                if(flat && (!flat.value || flat.value.trim()==='')) flat.value = glat;
                                if(flon && (!flon.value || flon.value.trim()==='')) flon.value = glon;
                            }catch(e){ console.warn('error saving modal geoloc', e); }
                        }, err=>{ console.warn('geoloc modal denied/failed', err); }, {timeout:5000});
                    } else {
                        console.warn('navigator.geolocation not available in this context (requires HTTPS)');
                    }
                }catch(e){ console.warn('modal geoloc handler', e); }
            });
        }
    }catch(e){ console.warn('no se pudo adjuntar modal geoloc listener', e); }
    // Nota: no cargar ámbitos ni categorías hasta que exista localStorage.codigoPostal

    // Evento del formulario de cuenta
    document.getElementById('form-cuenta-comercio').addEventListener('submit', (e) => {
        e.preventDefault();
        guardarConfiguracionCuenta();
    });

    // Cuando el usuario escribe/edita manualmente el código postal en el modal, validar y cargar ámbitos
    try {
        const inputCreateCod = document.getElementById('create-codpostal');
        if (inputCreateCod) {
            let createPostalTimeout = null;
            inputCreateCod.addEventListener('input', (e) => {
                const q = (e.target.value || '').trim();
                if (createPostalTimeout) clearTimeout(createPostalTimeout);
                if (!q) return;
                createPostalTimeout = setTimeout(() => {
                    fetch('/api/lookup/codigos?q=' + encodeURIComponent(q))
                        .then(r => r.json())
                        .then(data => {
                            if (data.success && data.items && data.items.length) {
                                // prefer exact match, otherwise first
                                let found = data.items.find(it => it.codigoPostal === q) || data.items[0];
                                if (found && found.codigoPostal) {
                                    localStorage.setItem('codigoPostal', found.codigoPostal);
                                    // recargar ambitos filtrados por este codigoPostal
                                    try { cargarAmbitosSelect(found.codigoPostal); } catch (err) { console.warn('cargarAmbitosSelect error', err); }
                                    try { setPostalCity(found.codigoPostal); } catch(e){}
                                }
                            } else {
                                // si no existe, vaciar select de ambitos
                                const sel = document.getElementById('create-ambito');
                                if (sel) sel.innerHTML = '';
                            }
                        }).catch(err => { console.warn('lookup codigos fallo', err); });
                }, 450);
            });
        }
    } catch (e) { console.warn('listener create-codpostal', e); }
});

// 1. CARGAR DATOS GENERALES
function cargarDashboard() {
    // aceptar params opcionales
    let params = {};
    if (arguments && arguments[0]) params = arguments[0];
    const qs = new URLSearchParams(params).toString();
    const url = '/api/comercio/datos_principales' + (qs ? ('?' + qs) : '');
    fetch(url)
        .then(res => res.json())
        .then(data => {
            if(data.success) {
                // Si el backend no devolvió comercio, mostrar modal de login
                if (!data.comercio) {
                    try {
                        const modalEl = document.getElementById('modalLoginComercio');
                        if (modalEl) new bootstrap.Modal(modalEl).show();
                    } catch (e) { console.warn('No se pudo mostrar modal login', e); }
                }
                // Renderizar Kpis
                document.getElementById('kpi-ventas').textContent = `$${data.metrics.ventas_hoy}`;
                document.getElementById('kpi-pedidos').textContent = data.metrics.pedidos_hoy;
                document.getElementById('kpi-promedio').textContent = `$${data.metrics.ticket_promedio}`;
                // Actualizar KPI de comercio (nombre/ambito/telefono/categoria) si viene comercio
                try{
                    if(data.comercio && data.comercio.id){
                        const nameEl = document.getElementById('kpi-comercio-name'); if(nameEl) nameEl.textContent = data.comercio.nombre || 'Gestión Operativa';
                        const ambEl = document.getElementById('kpi-comercio-ambito'); if(ambEl) ambEl.textContent = 'Ámbito: ' + (data.comercio.ambito || '-');
                        // fetch full comercio to get telefono and categoria
                        fetch('/api/comercio/' + encodeURIComponent(data.comercio.id)).then(r=>r.json()).then(cj=>{
                            if(cj && cj.success && cj.comercio){
                                const c = cj.comercio;
                                try{ const tel = document.getElementById('kpi-telefono'); if(tel) tel.textContent = 'Tel: ' + (c.telefono || 'N/A'); }catch(e){}
                                if(c.categoria_id){
                                    fetch('/api/lookup/categorias?id=' + encodeURIComponent(c.categoria_id)).then(r=>r.json()).then(catR=>{
                                        if(catR && catR.success && catR.items && catR.items.length){
                                            try{ const kpc = document.getElementById('kpi-categoria'); if(kpc) kpc.textContent = 'Categoria: ' + (catR.items[0].nombre || catR.items[0].valor || c.categoria_id); }catch(e){}
                                        }
                                    }).catch(()=>{});
                                }
                            }
                        }).catch(()=>{});
                    } else {
                        try{ const kti = document.getElementById('kpi-telefono'); if(kti) kti.textContent = 'Tel: -'; }catch(e){}
                        try{ const kpc = document.getElementById('kpi-categoria'); if(kpc) kpc.textContent = 'Categoria: -'; }catch(e){}
                        try{ const kname = document.getElementById('kpi-comercio-name'); if(kname) kname.textContent = 'Gestión Operativa'; }catch(e){}
                        try{ const kamb = document.getElementById('kpi-comercio-ambito'); if(kamb) kamb.textContent = 'Ámbito: -'; }catch(e){}
                    }
                }catch(e){console.warn('error actualizando KPI comercio', e);}
                // Mostrar información del comercio si está disponible
                if (data.comercio) {
                    const infoEl = document.getElementById('comercio-info');
                    infoEl.innerHTML = `<div class="card border-0 shadow-sm p-3 bg-white"><div class="d-flex justify-content-between align-items-center"><div><h6 class="mb-0 fw-bold small text-muted">Comercio</h6><div class="fw-semibold">${data.comercio.nombre} (ID: ${data.comercio.id})</div><div class="small text-muted">Email: ${data.comercio.email_usuario || 'N/A'}</div></div><div class="text-end small text-muted"><div>Ámbito: ${data.comercio.ambito || 'N/A'}</div><div id="comercio-categoria">Categoria: ${data.comercio.categoria_id || 'N/A'}</div><div id="comercio-telefono">Tel: -</div></div></div></div>`;
                    // fetch full comercio info to get telefono and confirmed fields
                    try{
                        if (data.comercio.id) {
                            fetch('/api/comercio/' + encodeURIComponent(data.comercio.id))
                                .then(r=>r.json())
                                .then(cj=>{
                                    if(cj && cj.success && cj.comercio){
                                        const c = cj.comercio;
                                        // telefono
                                        const telEl = document.getElementById('comercio-telefono');
                                        if(telEl) telEl.textContent = 'Tel: ' + (c.telefono || 'N/A');
                                        // categoria name if available
                                        if(c.categoria_id){
                                            fetch('/api/lookup/categorias?id=' + encodeURIComponent(c.categoria_id))
                                                .then(r=>r.json()).then(catR=>{
                                                    if(catR && catR.success && catR.items && catR.items.length){
                                                        const it = catR.items[0];
                                                        const catEl = document.getElementById('comercio-categoria');
                                                        if(catEl) catEl.textContent = 'Categoria: ' + (it.nombre || it.valor || c.categoria_id);
                                                    }
                                                }).catch(()=>{});
                                        }
                                        // update nombre if different
                                        try{ const nameDiv = infoEl.querySelector('.fw-semibold'); if(nameDiv && c.nombre) nameDiv.textContent = `${c.nombre} (ID: ${c.id})`; }catch(e){}
                                    }
                                }).catch(()=>{});
                        }
                    }catch(e){ console.warn('no se pudo cargar comercio full', e); }
                                // Si la respuesta trae info del comercio, autocompletar filtros
                        } else {
                            // no commerce -- clear KPI comercio fields
                            try{ const kti = document.getElementById('kpi-telefono'); if(kti) kti.textContent = 'Tel: -'; }catch(e){}
                            try{ const kpc = document.getElementById('kpi-categoria'); if(kpc) kpc.textContent = 'Categoria: -'; }catch(e){}
                                if (data.comercio) {
                                    try {
                                        if (data.comercio.id) document.getElementById('filtro-comercio-id').value = data.comercio.id;
                                        if (data.comercio.user_id) document.getElementById('filtro-user-id').value = data.comercio.user_id;
                                        if (data.comercio.ambito) document.getElementById('filtro-ambito').value = data.comercio.ambito;
                                        // Si hay categoria_id, obtener nombre y setear as id|name
                                        if (data.comercio.categoria_id) {
                                            fetch('/api/lookup/categorias?id=' + encodeURIComponent(data.comercio.categoria_id))
                                                .then(r=>r.json())
                                                .then(catRes=>{
                                                    if (catRes.success && catRes.items && catRes.items.length) {
                                                        const c = catRes.items[0];
                                                        document.getElementById('filtro-categoria').value = `${c.id}|${c.nombre}`;
                                                    }
                                                }).catch(()=>{});
                                        }
                                    } catch (e) {
                                        console.warn('Error autocompletando comercio:', e);
                                    }
                                }
                                // Auto-aplicar filtros si es carga inicial (no params)
                                try {
                                    if (!params || Object.keys(params).length === 0) {
                                        // esperar un momento para permitir que la categoría resuelta se coloque
                                        setTimeout(()=>{ try{ aplicarFiltros(); }catch(e){console.warn('auto aplicar filtros fallo',e);} }, 350);
                                    }
                                } catch(e) { /* ignore */ }
                }
                
                // Limpiar columnas Kanban
                const columnas = ['pendiente', 'preparacion', 'listo', 'enviado'];
                columnas.forEach(col => {
                    document.getElementById(`col-${col}`).innerHTML = '';
                    document.getElementById(`count-${col}`).textContent = '0';
                });

                // Contadores locales para el flujo
                let contadores = { pendiente: 0, preparacion: 0, listo: 0, enviado: 0 };

                // Inyectar tarjetas activas
                data.pedidos_activos.forEach(pedido => {
                    if(columnas.includes(pedido.estado)) {
                        contadores[pedido.estado]++;
                        inyectarTarjetaPedido(pedido);
                    }
                });

                // Actualizar números de cabecera Kanban
                columnas.forEach(col => {
                    document.getElementById(`count-${col}`).textContent = contadores[col];
                });

                // Renderizar historial en tabla
                renderizarHistorial(data.historial);
            }
        })
        .catch(err => console.error("Error cargando dashboard:", err));
}

function aplicarFiltros(){
    const comercioId = (document.getElementById('filtro-comercio-id') && document.getElementById('filtro-comercio-id').value) || (document.getElementById('filtro-comercio') && document.getElementById('filtro-comercio').value);
    const userId = document.getElementById('filtro-user-id').value;
    const ambito = (document.getElementById('filtro-ambito-select') && document.getElementById('filtro-ambito-select').value) || (document.getElementById('filtro-ambito') && document.getElementById('filtro-ambito').value);
    let categoria = document.getElementById('filtro-categoria').value;
    const codpostal = document.getElementById('filtro-codpostal').value;

    const params = {};
    if (comercioId) params['comercio_id'] = comercioId;
    if (userId) params['user_id'] = userId;
    if (ambito) params['ambito'] = ambito;
    if (categoria) {
        // soportar formato "id|nombre" que producimos en la datalist
        const m = categoria.match(/^(\d+)\|/);
        if (m) categoria = m[1];
        params['categoria_id'] = categoria;
    }
    if (codpostal) params['codigoPostal'] = codpostal;

    cargarDashboard(params);
}

// Load comercios for a given user id and populate filtro-comercio select
function fetchComerciosByUser(userId){
    const sel = document.getElementById('filtro-comercio');
    if(!sel) return;
    sel.innerHTML = '<option value="">-- Comercios (por User) --</option>';
    if(!userId) return;
    fetch('/api/comercios?user_id=' + encodeURIComponent(userId))
        .then(r=>r.json()).then(j=>{
            if(j && j.success && j.comercios){
                j.comercios.forEach(c=>{
                    const opt = document.createElement('option');
                    opt.value = c.id;
                    opt.text = `${c.id} — ${c.nombre}`;
                    sel.appendChild(opt);
                });
            }
        }).catch(err=>{ console.warn('fetchComerciosByUser error', err); });
}

// When a comercio is selected, set hidden id and load ambitos (general) then set ambito if comercio has one
function onComercioSelected(){
    try{
        const sel = document.getElementById('filtro-comercio');
        const hid = document.getElementById('filtro-comercio-id');
        if(!sel || !hid) return;
        const val = sel.value;
        hid.value = val;
        if(!val) return;
        fetch('/api/comercio/' + encodeURIComponent(val)).then(r=>r.json()).then(j=>{
            if(j && j.success && j.comercio){
                const c = j.comercio;
                // Load ambitos list (general) and try to set selected to c.ambito
                fetch('/api/lookup/ambitos').then(r=>r.json()).then(aR=>{
                    if(aR && aR.success && aR.items){
                        const ambSel = document.getElementById('filtro-ambito-select');
                        if(ambSel){
                            ambSel.innerHTML = '<option value="">-- Ámbito --</option>';
                            aR.items.forEach(it=>{
                                const o = document.createElement('option');
                                const label = it.nombre || it.valor || it.id;
                                o.value = it.valor || it.nombre || it.id;
                                o.text = label;
                                ambSel.appendChild(o);
                            });
                            if(c.ambito){
                                // try to find matching option by text or value
                                for(const opt of ambSel.options){
                                    if(opt.value === c.ambito || opt.text === c.ambito){ opt.selected = true; break; }
                                }
                            }
                        }
                    }
                }).catch(()=>{});
            }
        }).catch(()=>{});
    }catch(e){ console.warn('onComercioSelected', e); }
}

// attach user email input listener (debounced)
try{
    const userInput = document.getElementById('filtro-user-email');
    if(userInput){
        let to = null;
        userInput.addEventListener('input', (e)=>{
            if(to) clearTimeout(to);
            to = setTimeout(()=>{ fetchComerciosByEmail((e.target.value||'').trim()); }, 350);
        });
    }
}catch(e){}

try{
    const comerSel = document.getElementById('filtro-comercio');
    if(comerSel) comerSel.addEventListener('change', onComercioSelected);
}catch(e){}

// fetch comercios by email and populate select
function fetchComerciosByEmail(email){
    const sel = document.getElementById('filtro-comercio');
    if(!sel) return;
    sel.innerHTML = '<option value="">-- Comercios (por User) --</option>';
    if(!email) return;
    fetch('/api/comercios/by_email?email=' + encodeURIComponent(email))
        .then(r=>r.json()).then(j=>{
            if(j && j.success && j.comercios){
                j.comercios.forEach(c=>{
                    const opt = document.createElement('option');
                    opt.value = c.id;
                    opt.text = `${c.id} — ${c.nombre}`;
                    sel.appendChild(opt);
                });
            }
        }).catch(err=>{ console.warn('fetchComerciosByEmail error', err); });
}

function limpiarFiltros(){
    document.getElementById('form-filtros-comercio').reset();
    cargarDashboard();
}

// =========================
// Autocomplete helpers
// =========================
function cargarAmbitos(){
    fetch('/api/lookup/ambitos')
        .then(r=>r.json())
        .then(data=>{
            if(data.success){
                const dl = document.getElementById('datalist-ambitos');
                dl.innerHTML = '';
                data.items.forEach(it=>{
                    const opt = document.createElement('option');
                    opt.value = it.valor || it.nombre;
                    opt.text = it.nombre;
                    dl.appendChild(opt);
                });
            }
        }).catch(()=>{});
}

function cargarCategorias(){
    fetch('/api/lookup/categorias')
        .then(r=>r.json())
        .then(data=>{
            if(data.success){
                const dl = document.getElementById('datalist-categorias');
                dl.innerHTML = '';
                data.items.forEach(it=>{
                    const opt = document.createElement('option');
                    opt.value = `${it.id}|${it.nombre}`; // value contains id and name
                    opt.dataset.nombre = it.nombre;
                    dl.appendChild(opt);
                });
            }
        }).catch(()=>{});
}

// Rellena los KPI superiores con valores guardados en localStorage
function populateKpisFromLocalStorage(){
    try{
        const name = localStorage.getItem('nombreComercio') || localStorage.getItem('correo_electronico') || 'Gestión Operativa';
        const ambito = localStorage.getItem('ambito') || localStorage.getItem('ambito_nombre') || localStorage.getItem('ambito_id') || '-';
        const telefono = localStorage.getItem('numTelefono') || '';
        const categoria = localStorage.getItem('categoria_nombre') || localStorage.getItem('categoria') || localStorage.getItem('categoria_id') || '';

        const nameEl = document.getElementById('kpi-comercio-name'); if(nameEl) nameEl.textContent = name;
        const ambEl = document.getElementById('kpi-comercio-ambito'); if(ambEl) ambEl.textContent = 'Ámbito: ' + (ambito || '-');
        const telEl = document.getElementById('kpi-telefono'); if(telEl) telEl.textContent = 'Tel: ' + (telefono ? telefono : '-');
        const catEl = document.getElementById('kpi-categoria'); if(catEl) catEl.textContent = 'Categoria: ' + (categoria ? categoria : '-');
    }catch(e){ console.warn('populateKpisFromLocalStorage error', e); }
}

// Codigo postal suggestions
let codigoTimeout = null;
const inputCodigo = document.getElementById('filtro-codpostal');
if(inputCodigo){
    inputCodigo.addEventListener('input', (e)=>{
        const q = e.target.value;
        const box = document.getElementById('suggest-codigos');
        if(codigoTimeout) clearTimeout(codigoTimeout);
        if(!q){ box.style.display='none'; return; }
        codigoTimeout = setTimeout(()=>{
            fetch('/api/lookup/codigos?q=' + encodeURIComponent(q))
                .then(r=>r.json())
                .then(data=>{
                    box.innerHTML = '';
                    if(data.success && data.items.length){
                        data.items.forEach(it=>{
                            const div = document.createElement('div');
                            div.className = 'px-2 py-1 suggestion-item';
                            div.style.cursor='pointer';
                            div.textContent = it.codigoPostal + (it.ciudad ? (' — ' + it.ciudad) : '');
                            div.addEventListener('click', ()=>{
                                inputCodigo.value = it.codigoPostal;
                                box.style.display='none';
                            });
                            box.appendChild(div);
                        });
                        box.style.display='block';
                    } else {
                        box.style.display='none';
                    }
                }).catch(()=>{ box.style.display='none'; });
        }, 250);
    });
    // hide on blur
    inputCodigo.addEventListener('blur', ()=>{ setTimeout(()=>{ const box=document.getElementById('suggest-codigos'); if(box) box.style.display='none'; }, 200); });
}

// 2. INYECTAR PEDIDOS KANBAN DINÁMICAMENTE
function inyectarTarjetaPedido(pedido) {
    const contenedor = document.getElementById(`col-${pedido.estado}`);
    
    let botonAccion = '';
    if (pedido.estado === 'pendiente') {
        botonAccion = `<button class="btn btn-sm btn-outline-danger w-100 mt-2" onclick="cambiarEstadoPedido(${pedido.id}, 'preparacion')">Aceptar y Preparar <i class="bi bi-chevron-right"></i></button>`;
    } else if (pedido.estado === 'preparacion') {
        botonAccion = `<button class="btn btn-sm btn-outline-warning w-100 text-dark mt-2" onclick="cambiarEstadoPedido(${pedido.id}, 'listo')">¡Pedido Listo! <i class="bi bi-check2-circle"></i></button>`;
    } else if (pedido.estado === 'listo') {
        // Ejecuta tu lógica inteligente existente de asignación
        botonAccion = `<button class="btn btn-sm btn-success w-100 mt-2" onclick="dispararAsignacionRepartidor(${pedido.id})">Asignar Repartidor <i class="bi bi-bicycle"></i></button>`;
    } else if (pedido.estado === 'enviado') {
        botonAccion = `<span class="badge bg-success-subtle text-success w-100 text-center p-2 mt-2 d-block"><i class="bi bi-truck"></i> En Reparto</span>`;
    }

    const cardHtml = `
        <div class="card card-pedido mb-2 border-0 shadow-sm bg-white">
            <div class="card-body p-2">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="fw-bold text-dark small">Pedido #${pedido.id}</span>
                    <span class="text-primary fw-bold small">$${pedido.precio_venta}</span>
                </div>
                <p class="mb-1 text-muted text-truncate" style="font-size: 0.85rem;"><i class="bi bi-geo-alt"></i> ${pedido.lugar_entrega}</p>
                <p class="mb-0 text-dark fw-semibold" style="font-size: 0.85rem;"><i class="bi bi-person"></i> ${pedido.nombre_cliente}</p>
                ${botonAccion}
            </div>
        </div>
    `;
    contenedor.insertAdjacentHTML('beforeend', cardHtml);
}

// 3. ACTUALIZACIONES DE ESTADO
function cambiarEstadoPedido(pedidoId, nuevoEstado) {
    // Movimiento optimista en UI: mover la tarjeta al nuevo estado inmediatamente
    function findCardByPedidoId(id) {
        const cards = document.querySelectorAll('.card-pedido');
        for (const c of cards) {
            const span = c.querySelector('.card-body .fw-bold');
            if (span && span.textContent && span.textContent.includes(`#${id}`)) return c;
        }
        return null;
    }

    const cardEl = findCardByPedidoId(pedidoId);
    let rollbackData = null;
    if (cardEl) {
        // Determinar estado origen por el contenedor padre
        const parent = cardEl.closest('[id^="col-"]');
        const origen = parent ? parent.id.replace('col-', '') : null;

        // Extraer datos básicos para reinyectar si hace falta
        const precioEl = cardEl.querySelector('.text-primary');
        const lugarEl = cardEl.querySelector('.text-muted');
        const nombreEl = cardEl.querySelector('.fw-semibold');

        const precio = precioEl ? precioEl.textContent.replace(/[^0-9.,]/g,'') : '';
        const lugar = lugarEl ? lugarEl.textContent.trim() : '';
        const nombre = nombreEl ? nombreEl.textContent.trim() : '';

        rollbackData = { origen, html: cardEl.outerHTML };

        // Remover tarjeta del DOM
        cardEl.remove();

        // Actualizar contadores
        if (origen) {
            const counterEl = document.getElementById(`count-${origen}`);
            if (counterEl) counterEl.textContent = Math.max(0, parseInt(counterEl.textContent || '0') - 1);
        }

        // Reinyectar en columna destino con un objeto mínimo
        const pedidoObj = {
            id: pedidoId,
            precio_venta: precio || 0,
            lugar_entrega: lugar || '',
            nombre_cliente: nombre || '',
            estado: nuevoEstado
        };
        inyectarTarjetaPedido(pedidoObj);
        const destCounter = document.getElementById(`count-${nuevoEstado}`);
        if (destCounter) destCounter.textContent = (parseInt(destCounter.textContent || '0') + 1);
    }

    // Llamada al backend para persistir el cambio
    fetch('/api/comercio/actualizar_estado', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pedido_id: pedidoId, estado: nuevoEstado })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) {
            // rollback si hubo error
            alert(data.message || 'Error actualizando estado en servidor');
            if (rollbackData) {
                // quitar de destino
                const destCol = document.getElementById(`col-${nuevoEstado}`);
                if (destCol) {
                    const inserted = Array.from(destCol.querySelectorAll('.card-pedido')).find(c => c.querySelector('.fw-bold') && c.querySelector('.fw-bold').textContent.includes(`#${pedidoId}`));
                    if (inserted) inserted.remove();
                }
                // reinsertar original
                if (rollbackData.origen) {
                    const origenCol = document.getElementById(`col-${rollbackData.origen}`);
                    if (origenCol) origenCol.insertAdjacentHTML('afterbegin', rollbackData.html);
                }
                // ajustar contadores
                if (rollbackData.origen) {
                    const counterEl = document.getElementById(`count-${rollbackData.origen}`);
                    if (counterEl) counterEl.textContent = (parseInt(counterEl.textContent || '0') + 1);
                }
                const destCounter = document.getElementById(`count-${nuevoEstado}`);
                if (destCounter) destCounter.textContent = Math.max(0, parseInt(destCounter.textContent || '0') - 1);
            }
        }
    })
    .catch(err => {
        console.error('Error comunicándose con el servidor:', err);
        alert('Error comunicándose con el servidor');
        // rollback idéntico al anterior
        if (rollbackData) {
            const destCol = document.getElementById(`col-${nuevoEstado}`);
            if (destCol) {
                const inserted = Array.from(destCol.querySelectorAll('.card-pedido')).find(c => c.querySelector('.fw-bold') && c.querySelector('.fw-bold').textContent.includes(`#${pedidoId}`));
                if (inserted) inserted.remove();
            }
            if (rollbackData.origen) {
                const origenCol = document.getElementById(`col-${rollbackData.origen}`);
                if (origenCol) origenCol.insertAdjacentHTML('afterbegin', rollbackData.html);
            }
            if (rollbackData.origen) {
                const counterEl = document.getElementById(`count-${rollbackData.origen}`);
                if (counterEl) counterEl.textContent = (parseInt(counterEl.textContent || '0') + 1);
            }
            const destCounter = document.getElementById(`count-${nuevoEstado}`);
            if (destCounter) destCounter.textContent = Math.max(0, parseInt(destCounter.textContent || '0') - 1);
        }
    });
}

// CONEXIÓN DIRECTA CON TU REPARTO INTELIGENTE EXISTENTE
function dispararAsignacionRepartidor(pedidoId) {
    const config = obtenerConfig();
    
    // El payload exacto que consume tu backend actual
    const payload = {
        pedido_id: pedidoId,
        comercio_lat: config.lat,
        comercio_lon: config.lon,
        direccion_local: config.direccion,
        cliente_lat: 42.7400, // Estos datos idealmente vendrían embebidos en el pedido
        cliente_lon: 12.7450
    };

    fetch('/productosComerciales_pedidos_repartos_enviar_pedido/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if(data.success) {
            alert('¡Repartidor óptimo calculado con éxito! Abriendo despacho...');
            if(data.whatsapp_url) {
                window.open(data.whatsapp_url, '_blank');
            }
            cargarDashboard();
        } else {
            alert(data.message || 'Error en asignación');
        }
    });
}

// 4. RENDER HISTORIAL TRADICIONAL
function renderizarHistorial(historial) {
    const tbody = document.getElementById('tabla-historial');
    tbody.innerHTML = '';
    
    if(historial.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-3">No hay registros históricos.</td></tr>`;
        return;
    }

    historial.forEach(p => {
        const badgeColor = p.estado === 'entregado' ? 'bg-success' : 'bg-danger';
        const row = `
            <tr>
                <td class="fw-bold">#${p.id}</td>
                <td class="small text-muted">${p.fecha ? p.fecha.split('T')[0] : 'N/A'}</td>
                <td class="text-truncate" style="max-width: 250px;">${p.lugar_entrega}</td>
                <td class="fw-bold text-dark">$${p.precio_venta}</td>
                <td><span class="badge ${badgeColor}">${p.estado}</span></td>
            </tr>
        `;
        tbody.insertAdjacentHTML('beforeend', row);
    });
}

// --- Creación de comercio desde el modal ---
function showCreateComercioPanel(prefillEmail){
    try{
        const panel = document.getElementById('create-comercio-panel');
        const loginForm = document.getElementById('form-login-comercio');
        if (panel) panel.style.display = 'block';
        if (loginForm) loginForm.style.display = 'none';
        // Prioridad: valores top-level en localStorage, luego comercio_cuenta_config, luego prefillEmail
        const ls = localStorage;
        const cfg = (function(){ try { return JSON.parse(ls.getItem('comercio_cuenta_config')||'{}') } catch(e){ return {}; }})();

        const emailLS = (ls.getItem('correo_electronico') || '').trim();
        const telLS = (ls.getItem('numTelefono') || '').trim();
        const postalLS = (ls.getItem('codigoPostal') || '').trim();
        const latLS = (ls.getItem('latitud') || ls.getItem('lat') || cfg.lat || '').toString();
        const lonLS = (ls.getItem('longitud') || ls.getItem('lon') || cfg.lon || '').toString();

        // Email
        const elEmail = document.getElementById('create-email');
        if (emailLS) elEmail.value = emailLS;
        else if (prefillEmail) elEmail.value = prefillEmail;
        else if (elEmail && !elEmail.value && cfg.email) elEmail.value = cfg.email;

        // Telefono
        const elTel = document.getElementById('create-telefono');
        if (telLS) elTel.value = telLS;
        else if (cfg.telefono) elTel.value = cfg.telefono;

        // Direccion / postal
        const elDir = document.getElementById('create-direccion');
        if (cfg.direccion && (!elDir.value || elDir.value.trim()==='')) elDir.value = cfg.direccion;
        const elPostal = document.getElementById('create-codpostal');
        if (postalLS) elPostal.value = postalLS;
        else if (cfg.codigoPostal) elPostal.value = cfg.codigoPostal;

        // Lat / Lon: intentar siempre obtener ubicación actual del navegador y usarla; si falla, usar localStorage/cfg
        const elLat = document.getElementById('create-lat');
        const elLon = document.getElementById('create-lon');
        // fallback values
        if (latLS && (!elLat.value || elLat.value.trim()==='')) elLat.value = latLS;
        if (lonLS && (!elLon.value || elLon.value.trim()==='')) elLon.value = lonLS;
        // request current position and override fields when available
        try {
                if (navigator && navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(pos=>{
                    try{
                        if (elLat) elLat.value = pos.coords.latitude;
                        if (elLon) elLon.value = pos.coords.longitude;
                        console.log('Geolocalización obtenida:', pos.coords.latitude, pos.coords.longitude);
                        // Reverse geocode via Nominatim to obtain postal code
                        try {
                            const rlat = pos.coords.latitude;
                            const rlon = pos.coords.longitude;
                            const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${encodeURIComponent(rlat)}&lon=${encodeURIComponent(rlon)}`;
                            fetch(url, { headers: { 'Accept': 'application/json' } })
                                .then(r=>r.json())
                                .then(j=>{
                                    const postcode = (j && j.address && (j.address.postcode || j.address.postal_code)) ? (j.address.postcode || j.address.postal_code) : (j && j.extratags && j.extratags.postcode ? j.extratags.postcode : null);
                                    if (postcode) {
                                        // verify postcode exists in our table
                                        fetch('/api/lookup/codigos?q=' + encodeURIComponent(postcode))
                                            .then(r=>r.json())
                                            .then(res=>{
                                                if (res.success && res.items && res.items.length) {
                                                    if (elPostal) elPostal.value = postcode;
                                                    localStorage.setItem('codigoPostal', postcode);
                                                    console.log('Código postal verificado y aplicado:', postcode);
                                                    // ahora que el codigo postal existe, cargar ámbitos filtrados
                                                    try { cargarAmbitosSelect(postcode); } catch(e) { console.warn('No se pudo cargar ambitos tras verificar CP', e); }
                                                        try { setPostalCity(postcode); } catch(e) {}
                                                } else {
                                                    console.log('Código postal obtenido por geoloc no está en la tabla:', postcode);
                                                }
                                            }).catch(()=>{ /* ignore */ });
                                    }
                                }).catch(()=>{});
                        } catch(e) { console.warn('reverse geocode failed', e); }
                    }catch(e){}
                }, err=>{
                    console.warn('Geolocalización no disponible o denegada', err);
                }, {timeout:5000});
            }
        } catch(e) { console.warn('geoloc call failed', e); }

        // Load ambitos only if codigoPostal already exists; categorias se cargan solo al seleccionar un ambito
        const postal = (postalLS || cfg.codigoPostal || '').trim();
        if (postal) {
            cargarAmbitosSelect(postal);
            try { setPostalCity(postal); } catch(e){}
        }
    } catch(e){ console.warn('showCreateComercioPanel', e); }
}

function hideCreateComercioPanel(){
    try{
        const panel = document.getElementById('create-comercio-panel');
        const loginForm = document.getElementById('form-login-comercio');
        if (panel) panel.style.display = 'none';
        if (loginForm) loginForm.style.display = 'block';
    } catch(e){ console.warn('hideCreateComercioPanel', e); }
}

function handleCreateComercio(){
    const nombre = document.getElementById('create-nombre').value;
    let email = document.getElementById('create-email').value;
    let telefono = document.getElementById('create-telefono').value;
    const direccion = document.getElementById('create-direccion').value;
    let lat = document.getElementById('create-lat').value;
    let lon = document.getElementById('create-lon').value;
    let codigoPostal = document.getElementById('create-codpostal').value;
    const ambito = document.getElementById('create-ambito').value;
    const categoria_val = document.getElementById('create-categoria').value;
    const categoria_id = (categoria_val && categoria_val.split('|')[0]) ? categoria_val.split('|')[0] : categoria_val;

    // Priorizar localStorage values
    const ls = localStorage;
    if ((!email || email.trim()==='') && ls.getItem('correo_electronico')) email = ls.getItem('correo_electronico');
    if ((!telefono || telefono.trim()==='') && ls.getItem('numTelefono')) telefono = ls.getItem('numTelefono');
    if ((!codigoPostal || codigoPostal.trim()==='') && ls.getItem('codigoPostal')) codigoPostal = ls.getItem('codigoPostal');

    // Si faltan, pedir al usuario (prioridad baja; solo si no hay localStorage ni valor en campos)
    if (!email || email.trim()==='') {
        const resp = prompt('Ingrese su email para crear el comercio:', '');
        if (resp) { email = resp; document.getElementById('create-email').value = resp; }
    }
    if (!telefono || telefono.trim()==='') {
        const resp = prompt('Ingrese su teléfono (ej. +5491122334455):', '');
        if (resp) { telefono = resp; document.getElementById('create-telefono').value = resp; }
    }
    if (!codigoPostal || codigoPostal.trim()==='') {
        const resp = prompt('Ingrese el código postal:', '');
        if (resp) { codigoPostal = resp; document.getElementById('create-codpostal').value = resp; }
    }

    if (!nombre || !email) { alert('Nombre y email son requeridos'); return; }

    const sendPayload = (finalLat, finalLon) => {
        const payload = { nombre, email, telefono, direccion, lat: finalLat, lon: finalLon, ambito, categoria_id };
        if (codigoPostal) payload.codigoPostal = codigoPostal;
        fetch('/api/comercio/register', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify(payload)
        }).then(r=>r.json()).then(j=>{
            if (j.success) {
                // Guardar datos relevantes en localStorage para autocompletar en el futuro
                try {
                    // correo/telefono
                    if (email) localStorage.setItem('correo_electronico', email);
                    if (telefono) { localStorage.setItem('numTelefono', telefono); }

                    // ambito_id: extraer id si el campo ambito viene en formato id|valor
                    let ambitoIdToStore = '';
                    try {
                        const ambitoVal = (ambito || '').toString();
                        const parts = ambitoVal.split('|');
                        ambitoIdToStore = parts[0] || '';
                        if (ambitoIdToStore && !isNaN(parseInt(ambitoIdToStore))) {
                            localStorage.setItem('ambito_id', ambitoIdToStore);
                        }
                    } catch(e){}

                    // categoria_id
                    if (categoria_id) localStorage.setItem('categoria_id', categoria_id);

                    // lat/lon
                    if (finalLat !== undefined && finalLat !== null) localStorage.setItem('latitud', finalLat);
                    if (finalLon !== undefined && finalLon !== null) localStorage.setItem('longitud', finalLon);

                    // nombre y direccion
                    if (nombre) localStorage.setItem('nombreComercio', nombre);
                    if (direccion) localStorage.setItem('direccionComercio', direccion);

                    // codigo postal (usar clave existente)
                    if (codigoPostal) localStorage.setItem('codigoPostal', codigoPostal);
                } catch(e) { console.warn('No se pudo guardar en localStorage', e); }

                location.reload();
            } else {
                alert(j.message || 'Error creando comercio');
            }
        }).catch(e=>{ console.error(e); alert('Error comunicando con el servidor'); });
    };

    // Si lat/lon ya existen en campos o en localStorage, usarlos
    const latLS = ls.getItem('latitud') || ls.getItem('lat') || '';
    const lonLS = ls.getItem('longitud') || ls.getItem('lon') || '';
    const finalLat = (lat && lat.trim()!=='') ? lat : (latLS || '');
    const finalLon = (lon && lon.trim()!=='') ? lon : (lonLS || '');

    if (finalLat && finalLon) {
        sendPayload(finalLat, finalLon);
        return;
    }

    // Intentar geolocalización si no hay lat/lon
    if (navigator && navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(pos=>{
            const gLat = pos.coords.latitude;
            const gLon = pos.coords.longitude;
            // rellenar campos visualmente
            try{ document.getElementById('create-lat').value = gLat; document.getElementById('create-lon').value = gLon; }catch(e){}
            sendPayload(gLat, gLon);
        }, err=>{
            console.warn('Geoloc falló o denegada', err);
            // enviar sin lat/lon (backend puede aceptar nulls) o pedir manualmente
            const respLat = prompt('No se pudo obtener la ubicación automáticamente. Ingrese latitud (opcional):','');
            const respLon = prompt('Ingrese longitud (opcional):','');
            sendPayload(respLat || '', respLon || '');
        }, {timeout:5000});
    } else {
        // No hay geolocalización disponible
        const respLat = prompt('Geolocalización no disponible. Ingrese latitud (opcional):','');
        const respLon = prompt('Ingrese longitud (opcional):','');
        sendPayload(respLat || '', respLon || '');
    }
}

function cargarAmbitosSelect(postal){
    // Ensure we only load ambitos when a postal code is present (either param or localStorage)
    const ls = localStorage;
    if(!postal) postal = (ls.getItem('codigoPostal') || '').trim();
    if(!postal) {
        console.log('cargarAmbitosSelect: no hay codigoPostal en param ni en localStorage — abortando carga');
        return;
    }
    // Build params: only codigoPostal (no idioma filter)
    const params = [];
    if (postal) params.push('codigoPostal=' + encodeURIComponent(postal));
    const url = '/api/lookup/ambitos' + (params.length ? ('?' + params.join('&')) : '');
    console.log('cargarAmbitosSelect() -> requesting', { url, postal });
    fetch(url)
        .then(r=>r.json())
        .then(data=>{
            console.log('cargarAmbitosSelect() -> response', data);
            if(data.success){
                const sel = document.getElementById('create-ambito');
                if(!sel) return;
                sel.innerHTML = '';
                data.items.forEach(it=>{
                    const opt = document.createElement('option');
                    // value: id|valor to keep id available
                    opt.value = `${it.id}|${it.valor || it.nombre}`;
                    opt.dataset.ambitoId = it.id;
                    opt.textContent = it.nombre;
                    sel.appendChild(opt);
                });
                // attach change handler: when ambito selected, load categorias for that ambito
                sel.onchange = ()=>{
                    try{
                        const v = sel.value || '';
                        const parts = v.split('|');
                        const ambitoId = parts[0] || '';
                        if (ambitoId) cargarCategoriasSelect(null, ambitoId);
                    }catch(e){console.warn('error carga categorias por ambito', e);} 
                };
            }
        }).catch(()=>{});
}

function cargarCategoriasSelect(q, ambito_id){
    let url = '/api/lookup/categorias';
    const params = [];
    if (q) params.push('q=' + encodeURIComponent(q));
    if (ambito_id) params.push('ambito_id=' + encodeURIComponent(ambito_id));
    if (params.length) url += ('?' + params.join('&'));
    console.log('cargarCategoriasSelect() -> requesting', { url, ambito_id, q });
    fetch(url).then(r=>r.json()).then(data=>{
        console.log('cargarCategoriasSelect() -> response', data);
        if(data.success){
            const sel = document.getElementById('create-categoria');
            if(!sel) return;
            sel.innerHTML = '';
            data.items.forEach(it=>{
                const opt = document.createElement('option');
                opt.value = `${it.id}|${it.nombre}`;
                opt.textContent = it.nombre;
                sel.appendChild(opt);
            });
        }
    }).catch(()=>{});
}

document.addEventListener('DOMContentLoaded', ()=>{
    const btnShow = document.getElementById('btn-show-create');
    if (btnShow) btnShow.addEventListener('click', ()=> showCreateComercioPanel(document.getElementById('login-email') ? document.getElementById('login-email').value : ''));
    const btnCancel = document.getElementById('btn-cancel-create');
    if (btnCancel) btnCancel.addEventListener('click', ()=> hideCreateComercioPanel());
    // cargar configuración guardada local y preparar modal para cargar datos del comercio cuando se abra
    cargarConfiguracionCuenta();
    const modalCuentaEl = document.getElementById('modalCuenta');
    if(modalCuentaEl) {
        modalCuentaEl.addEventListener('show.bs.modal', function(){
            // cargar desde localStorage primero
            cargarConfiguracionCuenta();
            // set codigo postal from localStorage if present
            try{
                const postalLS = (localStorage.getItem('codigoPostal')||'').trim();
                if(postalLS) document.getElementById('cfg-codpostal').value = postalLS;
            }catch(e){}
            // cargar datos del comercio desde servidor (si existe)
            loadComercioConfigFromServer();
            // solicitar geolocalización del navegador y usarla (sobrescribe valores previos)
            try{
                if(navigator && navigator.geolocation){
                    navigator.geolocation.getCurrentPosition(pos=>{
                        try{
                            const latEl = document.getElementById('cfg-lat');
                            const lonEl = document.getElementById('cfg-lon');
                            if(latEl) latEl.value = pos.coords.latitude;
                            if(lonEl) lonEl.value = pos.coords.longitude;
                        }catch(e){console.warn('error writing geoloc to modal', e);}    
                    }, err=>{ console.warn('geoloc denied or failed', err); }, {timeout:5000});
                }
            }catch(e){ console.warn('geoloc not available', e); }
        });
    }
    // Logout button handler
    try{
        const btnLogout = document.getElementById('btn-logout-comercio');
        if(btnLogout) btnLogout.addEventListener('click', ()=>{
            handleLogoutComercio();
        });
    }catch(e){}
});

function handleLogoutComercio(){
    try{
        // clear all localStorage as requested
        localStorage.clear();
    }catch(e){ console.warn('no se pudo limpiar localStorage', e); }
    // notify server
    fetch('/api/comercio/logout', { method: 'POST' }).then(()=>{
        location.reload();
    }).catch(()=>{ location.reload(); });
}

function syncLocalStorageFromServerAfterLogin(loginEmail){
    // Return a Promise that resolves when localStorage has been synchronized
    return new Promise((resolve, reject)=>{
        fetch('/api/comercio/datos_principales')
            .then(r=>r.json())
            .then(data=>{
                if(!(data && data.success && data.comercio && data.comercio.id)) return resolve();
                const cid = data.comercio.id;
                fetch('/api/comercio/' + encodeURIComponent(cid))
                    .then(r=>r.json()).then(cdata=>{
                        if(!(cdata && cdata.success && cdata.comercio)) return resolve();
                        const c = cdata.comercio;
                        try{
                            if(c.nombre) localStorage.setItem('nombreComercio', c.nombre);
                            if(loginEmail) localStorage.setItem('correo_electronico', loginEmail);
                            if(c.telefono) localStorage.setItem('numTelefono', c.telefono);
                            if(c.direccion) localStorage.setItem('direccionComercio', c.direccion);
                            if(c.latitud || c.lat) localStorage.setItem('latitud', (c.latitud||c.lat));
                            if(c.longitud || c.lon) localStorage.setItem('longitud', (c.longitud||c.lon));
                            if(c.categoria_id) localStorage.setItem('categoria_id', c.categoria_id);
                            if(c.ambito) localStorage.setItem('ambito', c.ambito);
                            // codigo postal may be present under different keys
                            const codigoPostal = c.codigoPostal || c.codigo_postal || c.codpostal || c.codigo_postal_id || null;
                            if(codigoPostal) {
                                localStorage.setItem('codigoPostal', codigoPostal);
                                // try to fetch city for postal code
                                fetch('/api/lookup/codigos?q=' + encodeURIComponent(codigoPostal)).then(r=>r.json()).then(cpR=>{
                                    try{
                                        if(cpR && cpR.success && cpR.items && cpR.items.length){
                                            const found = cpR.items.find(it=>it.codigoPostal==codigoPostal) || cpR.items[0];
                                            if(found && found.ciudad) localStorage.setItem('codigoPostalCiudad', found.ciudad);
                                        }
                                    }catch(e){}
                                }).catch(()=>{});
                            }
                            // save minimal comercio_cuenta_config
                            try{
                                const cfg = { direccion: c.direccion||'', lat: c.latitud||c.lat||'', lon: c.longitud||c.lon||'', telefono: c.telefono||'' };
                                localStorage.setItem('comercio_cuenta_config', JSON.stringify(cfg));
                            }catch(e){}
                        }catch(e){ console.warn('syncLocalStorageFromServerAfterLogin error', e); }
                        return resolve();
                    }).catch(err=>{ console.warn('syncLocalStorageFromServerAfterLogin fetch comercio failed', err); return resolve(); });
            }).catch(err=>{ console.warn('syncLocalStorageFromServerAfterLogin fetch datos_principales failed', err); return resolve(); });
    });
}

// 5. MÓDULO GESTIÓN DE CONFIGURACIÓN CUENTA LOCAL (PERSISTENCIA)
function guardarConfiguracionCuenta() {
    const cuenta = {
        nombre: document.getElementById('cfg-nombre').value,
        email: document.getElementById('cfg-email').value,
        direccion: document.getElementById('cfg-direccion').value,
        // fallback to localStorage latitud/longitud when inputs are empty
        lat: (document.getElementById('cfg-lat').value) || localStorage.getItem('latitud') || localStorage.getItem('lat') || '',
        lon: (document.getElementById('cfg-lon').value) || localStorage.getItem('longitud') || localStorage.getItem('lon') || '',
        telefono: document.getElementById('cfg-telefono').value,
        codigoPostal: document.getElementById('cfg-codpostal').value,
        ambito: document.getElementById('cfg-ambito').value,
        categoria: document.getElementById('cfg-categoria').value,
        activo: document.getElementById('cfg-activo').checked
    };
    // Siempre guardar configuración local mínima
    localStorage.setItem('comercio_cuenta_config', JSON.stringify({direccion: cuenta.direccion, lat: cuenta.lat, lon: cuenta.lon, telefono: cuenta.telefono}));

    // Si existe comercio en sesión (cfg-comercio-id), enviar PUT a la API para actualizar
    const comercioId = document.getElementById('cfg-comercio-id').value;
    if (comercioId) {
        const payload = {
            nombre: cuenta.nombre,
            email: cuenta.email,
            telefono: cuenta.telefono,
            direccion: cuenta.direccion,
            latitud: cuenta.lat,
            longitud: cuenta.lon,
            ambito: cuenta.ambito,
            categoria_id: (cuenta.categoria && cuenta.categoria.split('|')[0]) ? parseInt(cuenta.categoria.split('|')[0]) : null,
            activo: cuenta.activo
        };
        fetch('/api/comercio/' + encodeURIComponent(comercioId), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(r=>r.json()).then(resp=>{
            if(resp && resp.success){
                // Sobrescribir localStorage con los valores guardados
                try{
                    if(cuenta.nombre) localStorage.setItem('nombreComercio', cuenta.nombre);
                    if(cuenta.email) localStorage.setItem('correo_electronico', cuenta.email);
                    if(cuenta.telefono) localStorage.setItem('numTelefono', cuenta.telefono);
                    if(cuenta.direccion) localStorage.setItem('direccionComercio', cuenta.direccion);
                    if(cuenta.codigoPostal) localStorage.setItem('codigoPostal', cuenta.codigoPostal);
                    if(cuenta.lat) localStorage.setItem('latitud', cuenta.lat);
                    if(cuenta.lon) localStorage.setItem('longitud', cuenta.lon);
                    // ambito -> intentar extraer id
                    try{
                        const a = (cuenta.ambito || '').toString();
                        const partsA = a.split('|');
                        const aid = partsA[0] || '';
                        if(aid && !isNaN(parseInt(aid))) localStorage.setItem('ambito_id', aid);
                    }catch(e){}
                    // categoria
                    try{
                        const cval = (cuenta.categoria || '').toString();
                        const partsC = cval.split('|');
                        const cid = partsC[0] || '';
                        if(cid && !isNaN(parseInt(cid))) localStorage.setItem('categoria_id', cid);
                    }catch(e){}
                }catch(e){ console.warn('no se pudo escribir localStorage tras guardar', e); }
                const modal = bootstrap.Modal.getInstance(document.getElementById('modalCuenta'));
                if(modal) modal.hide();
                cargarDashboard();
            } else {
                alert('Error actualizando comercio: ' + (resp && resp.message ? resp.message : 'Respuesta inválida'));
            }
        }).catch(err=>{ console.error('PUT /api/comercio error', err); alert('Error actualizando comercio'); });
    } else {
        // No hay comercio en servidor; solo persistir en localStorage las variables y cerrar
        try{
            if(cuenta.nombre) localStorage.setItem('nombreComercio', cuenta.nombre);
            if(cuenta.email) localStorage.setItem('correo_electronico', cuenta.email);
            if(cuenta.telefono) localStorage.setItem('numTelefono', cuenta.telefono);
            if(cuenta.direccion) localStorage.setItem('direccionComercio', cuenta.direccion);
            if(cuenta.codigoPostal) localStorage.setItem('codigoPostal', cuenta.codigoPostal);
            if(cuenta.lat) localStorage.setItem('latitud', cuenta.lat);
            if(cuenta.lon) localStorage.setItem('longitud', cuenta.lon);
            try{
                const a = (cuenta.ambito || '').toString();
                const partsA = a.split('|');
                const aid = partsA[0] || '';
                if(aid && !isNaN(parseInt(aid))) localStorage.setItem('ambito_id', aid);
            }catch(e){}
            try{
                const cval = (cuenta.categoria || '').toString();
                const partsC = cval.split('|');
                const cid = partsC[0] || '';
                if(cid && !isNaN(parseInt(cid))) localStorage.setItem('categoria_id', cid);
            }catch(e){}
        }catch(e){ console.warn('no se pudo escribir localStorage tras guardar local', e); }
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalCuenta'));
        if(modal) modal.hide();
        cargarDashboard();
    }
}

function loadComercioConfigFromServer(){
    fetch('/api/comercio/datos_principales')
        .then(r=>r.json())
        .then(data=>{
            if(data && data.success && data.comercio && data.comercio.id){
                const cid = data.comercio.id;
                fetch('/api/comercio/' + encodeURIComponent(cid))
                    .then(r=>r.json())
                    .then(cdata=>{
                        if(cdata && cdata.success && cdata.comercio){
                            const c = cdata.comercio;
                            try{
                                document.getElementById('cfg-comercio-id').value = c.id;
                                document.getElementById('cfg-nombre').value = c.nombre || '';
                                document.getElementById('cfg-email').value = c.email || '';
                                document.getElementById('cfg-telefono').value = c.telefono || '';
                                document.getElementById('cfg-direccion').value = c.direccion || '';
                                // Only set lat/lon from server if server provides them; do not overwrite existing client geolocation
                                try{
                                    if(c.latitud !== undefined && c.latitud !== null && c.latitud !== '') {
                                        document.getElementById('cfg-lat').value = c.latitud;
                                    }
                                    if(c.longitud !== undefined && c.longitud !== null && c.longitud !== '') {
                                        document.getElementById('cfg-lon').value = c.longitud;
                                    }
                                }catch(e){}
                                document.getElementById('cfg-ambito').value = c.ambito || '';
                                if(c.categoria_id) {
                                    // try to fetch categoria name
                                    fetch('/api/lookup/categorias?id=' + encodeURIComponent(c.categoria_id)).then(r=>r.json()).then(catR=>{
                                        if(catR && catR.success && catR.items && catR.items.length){
                                            const it = catR.items[0];
                                            document.getElementById('cfg-categoria').value = `${it.id}|${it.nombre}`;
                                        }
                                    }).catch(()=>{});
                                }
                            }catch(e){ console.warn('error poblando modal comercio', e); }
                        }
                    }).catch(()=>{});
            }
        }).catch(()=>{});
}

function cargarConfiguracionCuenta() {
    try{
        const saved = localStorage.getItem('comercio_cuenta_config');
        if(saved) {
            const cuenta = JSON.parse(saved);
            if(document.getElementById('cfg-direccion')) document.getElementById('cfg-direccion').value = cuenta.direccion || '';
            if(document.getElementById('cfg-lat')) document.getElementById('cfg-lat').value = cuenta.lat || '';
            if(document.getElementById('cfg-lon')) document.getElementById('cfg-lon').value = cuenta.lon || '';
            if(document.getElementById('cfg-telefono')) document.getElementById('cfg-telefono').value = cuenta.telefono || '';
        }
        // cargar nombre/email/número desde localStorage si están disponibles
        const nombreLS = (localStorage.getItem('nombreComercio') || '').trim();
        const emailLS = (localStorage.getItem('correo_electronico') || '').trim();
        const telLS = (localStorage.getItem('numTelefono') || '').trim();
        if(nombreLS && document.getElementById('cfg-nombre')) document.getElementById('cfg-nombre').value = nombreLS;
        if(emailLS && document.getElementById('cfg-email')) document.getElementById('cfg-email').value = emailLS;
        if(telLS && document.getElementById('cfg-telefono')) document.getElementById('cfg-telefono').value = telLS;
    }catch(e){ console.warn('cargarConfiguracionCuenta error', e); }
}


function obtenerConfig() {
    return JSON.parse(localStorage.getItem('comercio_cuenta_config')) || {
        direccion: "Via Roma 12, Spoleto",
        lat: 42.7345,
        lon: 12.7388,
        telefono: "+39074312345"
    };
}

function generarDatosPrueba() {
    if (confirm("¿Quieres generar 12 nuevos pedidos de prueba en la base de datos?")) {
        fetch('/api/comercio/cargar_mock', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    cargarDashboard(); // Recarga el flujo Kanban y KPIs automáticamente
                } else {
                    alert("Error al cargar mocks: " + data.error);
                }
            })
            .catch(err => console.error("Error:", err));
    }
}

function setPostalCity(postal){
    try{
        const elCity = document.getElementById('create-codpostal-city');
        if(!postal) { if(elCity) elCity.textContent=''; return; }
        fetch('/api/lookup/codigos?q=' + encodeURIComponent(postal))
            .then(r=>r.json())
            .then(data=>{
                if(data.success && data.items && data.items.length){
                    // prefer exact match
                    let match = data.items.find(it=>it.codigoPostal === postal) || data.items[0];
                    if(match && match.ciudad){
                        if(elCity) elCity.textContent = 'Ciudad: ' + match.ciudad;
                        localStorage.setItem('codigoPostalCiudad', match.ciudad);
                    } else {
                        if(elCity) elCity.textContent = '';
                    }
                } else {
                    if(elCity) elCity.textContent = '';
                }
            }).catch(()=>{ if(elCity) elCity.textContent = ''; });
    }catch(e){ console.warn('setPostalCity error', e); }
}