// ============================================
// dashboard.js - DPIA Repartidores
// ============================================

console.log('🚀 dashboard.js cargado correctamente');

// ============================================
// VARIABLES GLOBALES
// ============================================
window.authModal = null;
window.repartidorAutenticado = null;
window.pedidosMock = [];
window.isLoggedIn = false;
window.configModal = null;

// ============================================
// ACTUALIZAR UI DEL USUARIO (GLOBAL)
// ============================================
window.actualizarUIUsuario = function() {
    console.log('🔄 actualizarUIUsuario() ejecutándose');
    console.log('📌 repartidorAutenticado:', window.repartidorAutenticado);
    
    const authText = document.getElementById('authText');
    const btnAuth = document.getElementById('btnAuth');
    const btnLogout = document.getElementById('btnLogout');
    const navCuenta = document.getElementById('navCuenta');
    const tituloBienvenida = document.querySelector('.section-title span');
    const subtituloBienvenida = document.querySelector('.section-title + p');
    
    console.log('📌 navCuenta:', navCuenta);
    
    if (window.repartidorAutenticado) {
        const nombreCompleto = `${window.repartidorAutenticado.nombre} ${window.repartidorAutenticado.apellido || ''}`.trim();
        
        if (authText) authText.textContent = ` ${nombreCompleto}`;
        if (btnAuth) {
            btnAuth.className = 'btn btn-dpia-outline btn-sm';
            btnAuth.href = '#';
        }
        if (btnLogout) btnLogout.style.display = 'block';
        if (navCuenta) {
            navCuenta.style.display = 'block';
            navCuenta.style.visibility = 'visible';
            console.log('✅ Botón Cuenta VISIBLE');
        }
        if (tituloBienvenida) {
            tituloBienvenida.textContent = `Bienvenido, ${nombreCompleto}`;
        }
        if (subtituloBienvenida) {
            subtituloBienvenida.innerHTML = `Has iniciado sesión como <strong>${window.repartidorAutenticado.email}</strong>`;
        }
        window.isLoggedIn = true;
    } else {
        if (authText) authText.textContent = 'Iniciar Sesión';
        if (btnAuth) {
            btnAuth.className = 'btn btn-dpia-primary btn-sm';
        }
        if (btnLogout) btnLogout.style.display = 'none';
        if (navCuenta) {
            navCuenta.style.display = 'none';
            navCuenta.style.visibility = 'hidden';
        }
        if (tituloBienvenida) {
            tituloBienvenida.textContent = 'Bienvenido, Repartidor';
        }
        if (subtituloBienvenida) {
            subtituloBienvenida.textContent = 'Inicia sesión para gestionar tus pedidos, visualizar tu rendimiento y comisiones.';
        }
        window.isLoggedIn = false;
    }
};

// ============================================
// FORZAR MOSTRAR CUENTA
// ============================================
window.forzarMostrarCuenta = function() {
    console.log('🔧 Forzando mostrar botón Cuenta...');
    const navCuenta = document.getElementById('navCuenta');
    if (navCuenta) {
        navCuenta.style.display = 'block';
        navCuenta.style.visibility = 'visible';
        navCuenta.style.opacity = '1';
        console.log('✅ Botón Cuenta forzado a VISIBLE');
    } else {
        console.error('❌ navCuenta NO EXISTE');
    }
};



// ============================================
// VERIFICAR SESIÓN
// ============================================
window.verificarSesion = async function() {
    console.log('🔍 Verificando sesión...');
    try {
        const response = await fetch('/api/repartidor/verificar_sesion');
        const data = await response.json();
        console.log('📡 Respuesta:', data);
        
        if (data.success && data.repartidor) {
            window.repartidorAutenticado = data.repartidor;
            window.isLoggedIn = true;
            window.actualizarUIUsuario();
            await window.cargarDatosReales();
            window.actualizarDashboard();
            console.log('✅ Sesión verificada:', window.repartidorAutenticado.nombre);
        } else {
            console.log('ℹ️ No hay sesión activa');
            window.repartidorAutenticado = null;
            window.isLoggedIn = false;
            window.actualizarUIUsuario();
        }
    } catch (error) {
        console.error('❌ Error verificando sesión:', error);
        window.repartidorAutenticado = null;
        window.isLoggedIn = false;
        window.actualizarUIUsuario();
    }
};

// ============================================
// NAVEGACIÓN ENTRE SECCIONES
// ============================================
window.showSection = function(section) {
    const sections = ['dashboard', 'historial', 'analisis'];
    sections.forEach(s => {
        const el = document.getElementById('seccion-' + s);
        if (el) el.style.display = 'none';
    });

    const selected = document.getElementById('seccion-' + section);
    if (selected) selected.style.display = 'block';

    document.querySelectorAll('.nav-link').forEach(el => el.classList.remove('active'));
    const navLink = document.querySelector(`.nav-link[onclick*="${section}"]`);
    if (navLink) navLink.classList.add('active');

    if (window.repartidorAutenticado) {
        if (section === 'historial') window.actualizarHistorial();
        if (section === 'analisis') window.actualizarAnalisis();
    }
};

// ============================================
// AUTENTICACIÓN - MODAL
// ============================================
window.abrirModalAuth = function() {
    const loginForm = document.getElementById('formLogin');
    const registroForm = document.getElementById('formRegistro');
    const authStatus = document.getElementById('authStatus');
    
    if (loginForm) loginForm.style.display = 'block';
    if (registroForm) registroForm.style.display = 'none';
    if (authStatus) authStatus.classList.add('d-none');
    
    if (window.authModal) window.authModal.show();
};

window.toggleRegistro = function() {
    const login = document.getElementById('formLogin');
    const registro = document.getElementById('formRegistro');
    
    if (login && registro) {
        if (login.style.display === 'none') {
            login.style.display = 'block';
            registro.style.display = 'none';
        } else {
            login.style.display = 'none';
            registro.style.display = 'block';
        }
    }
};

window.mostrarAuthStatus = function(mensaje, tipo = 'info') {
    const status = document.getElementById('authStatus');
    const text = document.getElementById('authStatusText');
    
    if (status && text) {
        status.className = `alert alert-${tipo}`;
        text.textContent = mensaje;
        status.classList.remove('d-none');
    }
};

// ============================================
// LOGIN CON BACKEND REAL
// ============================================
window.loginRepartidor = async function(event) {
    event.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    window.mostrarAuthStatus('Verificando credenciales...', 'info');

    try {
        const response = await fetch('/api/repartidor/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (data.success) {
            window.repartidorAutenticado = data.repartidor;
            window.actualizarUIUsuario();
            if (window.authModal) window.authModal.hide();
            
            await window.cargarDatosReales();
            window.actualizarDashboard();
            
            window.mostrarNotificacion('✅ ¡Bienvenido ' + window.repartidorAutenticado.nombre + '!', 'success');
        } else {
            window.mostrarAuthStatus(data.message || 'Error al iniciar sesión', 'danger');
        }
    } catch (error) {
        window.mostrarAuthStatus('Error: ' + error.message, 'danger');
    }
};

// ============================================
// REGISTRO CON BACKEND REAL
// ============================================
window.registrarRepartidor = async function(event) {
    event.preventDefault();
    const nombre = document.getElementById('regNombre').value;
    const apellido = document.getElementById('regApellido').value;
    const telefono = document.getElementById('regTelefono').value;
    const email = document.getElementById('regEmail').value;
    const password = document.getElementById('regPassword').value;

    window.mostrarAuthStatus('Registrando usuario...', 'info');

    try {
        const response = await fetch('/api/repartidor/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ nombre, apellido, telefono, email, password })
        });

        const data = await response.json();

        if (data.success) {
            window.repartidorAutenticado = data.repartidor;
            window.actualizarUIUsuario();
            if (window.authModal) window.authModal.hide();
            
            await window.cargarDatosReales();
            window.actualizarDashboard();
            
            window.mostrarNotificacion('✅ ¡Registro exitoso! Bienvenido ' + window.repartidorAutenticado.nombre, 'success');
        } else {
            window.mostrarAuthStatus(data.message || 'Error al registrarse', 'danger');
        }
    } catch (error) {
        window.mostrarAuthStatus('Error: ' + error.message, 'danger');
    }
};

// ============================================
// CERRAR SESIÓN
// ============================================
window.logout = async function() {
    if (!confirm('¿Estás seguro que deseas cerrar sesión?')) return;
    
    try {
        const response = await fetch('/api/repartidor/logout', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            window.repartidorAutenticado = null;
            window.pedidosMock = [];
            window.isLoggedIn = false;
            window.actualizarUIUsuario();
            window.actualizarDashboard();
            window.mostrarNotificacion('Sesión cerrada correctamente', 'info');
            
            setTimeout(() => {
                window.location.href = '/repartidores/login';
            }, 1500);
        }
    } catch (error) {
        console.error('Error al cerrar sesión:', error);
        window.mostrarNotificacion('Error al cerrar sesión', 'danger');
    }
};

// ============================================
// CARGAR DATOS DEL BACKEND
// ============================================
window.cargarDatosReales = async function() {
    if (!window.repartidorAutenticado) return;
    
    try {
        const pedidosResponse = await fetch('/api/repartidor/pedidos');
        const pedidosData = await pedidosResponse.json();
        
        if (pedidosData.success) {
            window.pedidosMock = pedidosData.pedidos || [];
        }

        const statsResponse = await fetch('/api/repartidor/estadisticas');
        const statsData = await statsResponse.json();
        
        if (statsData.success) {
            const stats = statsData.estadisticas || {};
            document.getElementById('totalPedidos').textContent = stats.total_pedidos || 0;
            document.getElementById('pedidosHoy').textContent = stats.pedidos_hoy || 0;
            document.getElementById('comisiones').textContent = '$' + (stats.comisiones || 0).toLocaleString();
            document.getElementById('rating').textContent = '⭐ ' + (stats.rating || 5.0);
            document.getElementById('pedidosActivosCount').textContent = (stats.pedidos_activos || 0) + ' activos';
            
            if (document.getElementById('seccion-analisis').style.display !== 'none') {
                window.actualizarAnalisis();
            }
        }
    } catch (error) {
        console.error('Error cargando datos:', error);
    }
};

// ============================================
// DATOS MOCK (FALLBACK)
// ============================================
window.cargarDatosMock = function() {
    window.pedidosMock = [
        { id: 1001, cliente: 'María López', fecha: '2026-06-30', total: 45000, comision: 4500, estado: 'completado' },
        { id: 1002, cliente: 'Carlos Gómez', fecha: '2026-06-30', total: 32000, comision: 3200, estado: 'completado' },
        { id: 1003, cliente: 'Ana Martínez', fecha: '2026-06-29', total: 28000, comision: 2800, estado: 'completado' },
        { id: 1004, cliente: 'Roberto Sánchez', fecha: '2026-06-29', total: 51000, comision: 5100, estado: 'en_curso' },
        { id: 1005, cliente: 'Laura Fernández', fecha: '2026-06-28', total: 19000, comision: 1900, estado: 'completado' },
    ];
};

// ============================================
// ACTUALIZAR DASHBOARD
// ============================================
window.actualizarDashboard = function() {
    if (!window.repartidorAutenticado) {
        document.getElementById('totalPedidos').textContent = '0';
        document.getElementById('pedidosHoy').textContent = '0';
        document.getElementById('comisiones').textContent = '$0';
        document.getElementById('rating').textContent = '⭐ 5.0';
        document.getElementById('pedidosActivosCount').textContent = '0 activos';
        
        const container = document.getElementById('pedidosActivosList');
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-box-open"></i>
                    <p>No hay pedidos activos en este momento</p>
                </div>
            `;
        }
        return;
    }

    const completados = window.pedidosMock.filter(p => p.estado === 'completado');
    const hoy = window.pedidosMock.filter(p => p.fecha === new Date().toISOString().split('T')[0]);
    const totalComisiones = completados.reduce((sum, p) => sum + (p.comision || 0), 0);
    const activos = window.pedidosMock.filter(p => p.estado === 'en_curso');

    document.getElementById('totalPedidos').textContent = window.pedidosMock.length;
    document.getElementById('pedidosHoy').textContent = hoy.length;
    document.getElementById('comisiones').textContent = '$' + totalComisiones.toLocaleString();
    document.getElementById('rating').textContent = '⭐ ' + (window.repartidorAutenticado.rating || 5.0);
    document.getElementById('pedidosActivosCount').textContent = activos.length + ' activos';

    const container = document.getElementById('pedidosActivosList');
    if (container) {
        if (activos.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-box-open"></i>
                    <p>No hay pedidos activos en este momento</p>
                </div>
            `;
        } else {
            container.innerHTML = activos.map(p => {
                const estado = (p.estado || '').toLowerCase();
                return `
                <div class="d-flex justify-content-between align-items-center p-3 mb-2" 
                     style="background: rgba(108, 43, 217, 0.1); border-radius: 12px; border-left: 4px solid var(--dpia-secondary);">
                    <div>
                        <strong>#${p.id}</strong> - ${p.cliente}
                        <br>
                        <small class="text-muted">$${p.total.toLocaleString()}</small>
                    </div>
                    <div class="d-flex align-items-center">
                        <span class="badge-warning-dpia me-2"><i class="fas fa-spinner fa-spin me-1"></i>${estado === 'enviado' || estado === 'en_curso' ? 'En curso' : estado}</span>
                        <button class="btn btn-sm btn-outline-light me-1" onclick="abrirComentario(${p.id})"><i class="fas fa-comment me-1"></i>Comentar</button>
                        <button class="btn btn-sm btn-success ms-1" onclick="marcarPedido(${p.id}, 'entregado')">Marcar entregado</button>
                        <button class="btn btn-sm btn-danger ms-1" onclick="marcarNoCorresponde(${p.id})">No corresponde</button>
                    </div>
                </div>
            `}).join('');
        }
    }
};

// =========================
// FILTROS DE PEDIDOS
// =========================
window.filtroActual = 'todos';
document.addEventListener('click', function(e) {
    const btn = e.target.closest('#filtrosPedidos button');
    if (!btn) return;
    document.querySelectorAll('#filtrosPedidos button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    window.filtroActual = btn.getAttribute('data-filter') || 'todos';
    window.renderizarPedidosFiltrados();
});

window.renderizarPedidosFiltrados = function() {
    const filtro = window.filtroActual;
    let lista = window.pedidosMock.slice();
    if (filtro !== 'todos') {
        lista = lista.filter(p => {
            const estado = (p.estado || '').toString().toLowerCase();
            if (filtro === 'completado') return ['completado', 'entregado', 'terminado'].includes(estado);
            if (filtro === 'pendiente') return ['pendiente', 'pendiente_pago', 'por_asignar'].includes(estado);
            if (filtro === 'en_curso') return ['en_curso', 'enviado', 'procesando', 'en_transito'].includes(estado);
            return estado === filtro;
        });
    }

    // Actualizar contadores y lista principal (reutiliza lógica de actualizarDashboard pero con lista filtrada)
    const activos = lista.filter(p => p.estado === 'en_curso');
    const container = document.getElementById('pedidosActivosList');
    document.getElementById('totalPedidos').textContent = window.pedidosMock.length;
    document.getElementById('pedidosActivosCount').textContent = activos.length + ' activos';

    if (container) {
        if (lista.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-box-open"></i>
                    <p>No hay pedidos que coincidan</p>
                </div>
            `;
            return;
        }

        container.innerHTML = lista.map(p => {
            const estado = (p.estado || '').toLowerCase();
            const badge = ['completado','entregado','terminado'].includes(estado)
                ? '<span class="badge-success-dpia"><i class="fas fa-check me-1"></i>Entregado</span>'
                : '<span class="badge-warning-dpia"><i class="fas fa-spinner fa-spin me-1"></i>En curso</span>';
            return `
            <div class="d-flex justify-content-between align-items-center p-3 mb-2" 
                 style="background: rgba(108, 43, 217, 0.1); border-radius: 12px; border-left: 4px solid var(--dpia-secondary);">
                <div>
                    <strong>#${p.id}</strong> - ${p.cliente}
                    <br>
                    <small class="text-muted">$${p.total.toLocaleString()}</small>
                </div>
                <div class="d-flex align-items-center">
                    ${badge}
                    <button class="btn btn-sm btn-outline-light ms-3" onclick="abrirComentario(${p.id})"><i class="fas fa-comment me-1"></i>Comentar</button>
                    ${estado === 'pendiente' ? '<button class="btn btn-sm btn-primary ms-2" onclick="aceptarPedido('+p.id+')">Aceptar</button>' : ''}
                    ${['enviado','en_curso','en_transito'].includes(estado) ? '<button class="btn btn-sm btn-success ms-2" onclick="marcarPedido('+p.id+', \"entregado\")">Marcar entregado</button><button class="btn btn-sm btn-danger ms-2" onclick="marcarNoCorresponde('+p.id+')">No corresponde</button>' : ''}
                </div>
            </div>
        `}).join('');
    }
};


// ACEPTAR PEDIDO
window.aceptarPedido = async function(pedidoId) {
    if (!confirm('¿Deseas aceptar este pedido?')) return;
    try {
        const resp = await fetch(`/api/repartidor/pedidos/${pedidoId}/aceptar`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            const pedido = window.pedidosMock.find(p => p.id == pedidoId);
            if (pedido) pedido.estado = 'enviado';
            window.mostrarNotificacion('Pedido aceptado', 'success');
            window.renderizarPedidosFiltrados();
        } else {
            window.mostrarNotificacion(data.message || 'Error al aceptar pedido', 'danger');
        }
    } catch (err) {
        console.error('Error aceptando pedido:', err);
        window.mostrarNotificacion('Error al aceptar pedido', 'danger');
    }
};

// MARCAR PEDIDO (entregado)
window.marcarPedido = async function(pedidoId, action) {
    if (action === 'entregado' && !confirm('Confirmar que el pedido fue entregado?')) return;
    try {
        const resp = await fetch(`/api/repartidor/pedidos/${pedidoId}/marcar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });
        const data = await resp.json();
        if (data.success) {
            const pedido = window.pedidosMock.find(p => p.id == pedidoId);
            if (pedido) pedido.estado = (action === 'entregado') ? 'completado' : pedido.estado;
            window.mostrarNotificacion('Estado actualizado', 'success');
            window.renderizarPedidosFiltrados();
        } else {
            window.mostrarNotificacion(data.message || 'Error actualizando estado', 'danger');
        }
    } catch (err) {
        console.error('Error actualizando estado:', err);
        window.mostrarNotificacion('Error actualizando estado', 'danger');
    }
};

// No corresponde: abrir prompt para comentario obligatorio
window.marcarNoCorresponde = function(pedidoId) {
    const razon = prompt('Indica por favor el motivo por el que este pedido no te corresponde:');
    if (!razon) {
        window.mostrarNotificacion('Comentario requerido', 'warning');
        return;
    }
    (async () => {
        try {
            const resp = await fetch(`/api/repartidor/pedidos/${pedidoId}/marcar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'no_corresponde', comentario: razon })
            });
            const data = await resp.json();
            if (data.success) {
                const pedido = window.pedidosMock.find(p => p.id == pedidoId);
                if (pedido) pedido.estado = 'no_corresponde';
                window.mostrarNotificacion('Pedido marcado como no_corresponde', 'success');
                window.renderizarPedidosFiltrados();
            } else {
                window.mostrarNotificacion(data.message || 'Error actualizando', 'danger');
            }
        } catch (err) {
            console.error('Error marcando no_corresponde:', err);
            window.mostrarNotificacion('Error actualizando', 'danger');
        }
    })();
};
// =========================
// MODAL DE COMENTARIO
// =========================
window.abrirComentario = function(pedidoId) {
    const textarea = document.getElementById('delivery-modal-comentario-text');
    const hidden = document.getElementById('delivery-modal-comentario-pedido-id');
    const tituloEl = document.getElementById('delivery-modal-comentario-titulo');
    const repartidorEl = document.getElementById('delivery-modal-comentario-repartidor-id');
    const pedidoVisibleEl = document.getElementById('delivery-modal-comentario-pedido-id-visible');

    const pedido = window.pedidosMock.find(p => p.id === pedidoId);
    if (pedido && textarea) textarea.value = pedido.comentarioCliente || '';
    if (hidden) hidden.value = pedidoId;

    // Título del modal: usar título del pedido si existe
    if (tituloEl) tituloEl.textContent = pedido && pedido.titulo ? pedido.titulo : `Pedido ${pedidoId}`;
    // Repartidor: tomar del objeto de sesión si está disponible
    if (repartidorEl) repartidorEl.textContent = (window.repartidorAutenticado && window.repartidorAutenticado.id) ? window.repartidorAutenticado.id : (pedido ? (pedido.asignado_a || '-') : '-');
    if (pedidoVisibleEl) pedidoVisibleEl.textContent = pedidoId;

    const modalEl = document.getElementById('delivery-modal-comentario');
    window.deliveryComentarioModal = window.deliveryComentarioModal || new bootstrap.Modal(modalEl);
    window.deliveryComentarioModal.show();
};

const guardarBtn = document.getElementById('delivery-modal-comentario-guardar');
if (guardarBtn) {
    guardarBtn.addEventListener('click', async function() {
        const pedidoId = document.getElementById('delivery-modal-comentario-pedido-id').value;
        const texto = document.getElementById('delivery-modal-comentario-text').value;
        if (!pedidoId) return;

        try {
            const resp = await fetch(`/api/repartidor/pedidos/${pedidoId}/comentario`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ comentario: texto })
            });
            const data = await resp.json();
            if (data.success) {
                const pedido = window.pedidosMock.find(p => p.id == pedidoId);
                if (pedido) pedido.comentarioCliente = texto;
                window.mostrarNotificacion('Comentario guardado', 'success');
                if (window.deliveryComentarioModal) window.deliveryComentarioModal.hide();
                window.renderizarPedidosFiltrados();
            } else {
                window.mostrarNotificacion(data.message || 'Error guardando comentario', 'danger');
            }
        } catch (err) {
            console.error('Error guardando comentario:', err);
            window.mostrarNotificacion('Error guardando comentario', 'danger');
        }
    });
} else {
    console.warn('Botón de guardar comentario no encontrado en DOM');
}

// ============================================
// ACTUALIZAR HISTORIAL
// ============================================
window.actualizarHistorial = function() {
    const tbody = document.getElementById('historialPedidos');
    if (!tbody) return;
    
    if (window.pedidosMock.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted py-4">
                    <i class="fas fa-inbox me-2"></i>No hay pedidos en el historial
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = window.pedidosMock.map(p => {
        const estadoBadge = p.estado === 'completado' 
            ? '<span class="badge-success-dpia"><i class="fas fa-check me-1"></i>Completado</span>'
            : '<span class="badge-warning-dpia"><i class="fas fa-spinner fa-spin me-1"></i>En curso</span>';
        return `
            <tr>
                <td><strong>#${p.id}</strong></td>
                <td>${p.cliente}</td>
                <td>${p.fecha}</td>
                <td>$${p.total.toLocaleString()}</td>
                <td>$${(p.comision || 0).toLocaleString()}</td>
                <td>${estadoBadge}</td>
            </tr>
        `;
    }).join('');
};

// ============================================
// ACTUALIZAR ANÁLISIS
// ============================================
window.actualizarAnalisis = function() {
    const completados = window.pedidosMock.filter(p => p.estado === 'completado');
    const totalGanado = completados.reduce((sum, p) => sum + (p.comision || 0), 0);
    const promedio = completados.length > 0 ? totalGanado / completados.length : 0;
    const tasaExito = window.pedidosMock.length > 0 ? Math.round((completados.length / window.pedidosMock.length) * 100) : 0;

    document.getElementById('totalGanado').textContent = '$' + totalGanado.toLocaleString();
    document.getElementById('promedioPedido').textContent = '$' + promedio.toFixed(0);
    document.getElementById('pedidosCompletados').textContent = completados.length;
    document.getElementById('tasaExito').textContent = tasaExito + '%';

    const meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'];
    const comisionesMes = [12000, 18000, 15000, 22000, 19000, 25000];
    const comisionesContainer = document.getElementById('comisionesMes');
    if (comisionesContainer) {
        comisionesContainer.innerHTML = `
            <div class="row g-2">
                ${meses.map((mes, i) => `
                    <div class="col-4 col-md-2 text-center">
                        <div class="p-2" style="background: rgba(108, 43, 217, 0.1); border-radius: 8px;">
                            <div class="text-muted small">${mes}</div>
                            <div class="fw-bold text-white">$${comisionesMes[i].toLocaleString()}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    const pedidosPorDia = [3, 2, 4, 1, 3, 2, 4];
    const rendimientoContainer = document.getElementById('rendimientoStats');
    if (rendimientoContainer) {
        rendimientoContainer.innerHTML = `
            <div class="row g-2">
                <div class="col-12">
                    <div class="d-flex justify-content-between mb-1">
                        <span class="text-muted">Pedidos por día</span>
                        <span class="text-white">${pedidosPorDia.reduce((a,b) => a+b, 0)} total</span>
                    </div>
                    <div class="d-flex gap-1">
                        ${pedidosPorDia.map(p => `
                            <div class="flex-grow-1" style="height: 30px; background: rgba(108, 43, 217, 0.2); border-radius: 4px; position: relative;">
                                <div style="height: 100%; width: ${(p / Math.max(...pedidosPorDia)) * 100}%; background: var(--dpia-gradient); border-radius: 4px;"></div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }
};

// ============================================
// NOTIFICACIONES
// ============================================
window.mostrarNotificacion = function(mensaje, tipo = 'info') {
    const notificacion = document.createElement('div');
    notificacion.className = `alert alert-${tipo} alert-dismissible fade show`;
    notificacion.style.position = 'fixed';
    notificacion.style.top = '20px';
    notificacion.style.right = '20px';
    notificacion.style.zIndex = '9999';
    notificacion.style.maxWidth = '400px';
    notificacion.style.borderRadius = '12px';
    notificacion.style.boxShadow = '0 8px 30px rgba(0,0,0,0.3)';
    notificacion.innerHTML = `
        ${mensaje}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(notificacion);
    
    setTimeout(() => {
        if (notificacion.parentNode) {
            notificacion.remove();
        }
    }, 5000);
};

// ============================================
// CONFIGURACIÓN DE CUENTA
// ============================================
window.abrirConfiguracion = function() {
    if (!window.repartidorAutenticado) {
        window.mostrarNotificacion('Debes iniciar sesión primero', 'warning');
        return;
    }
    
    document.getElementById('configLoading').style.display = 'block';
    document.getElementById('formConfiguracion').style.display = 'none';
    
    if (window.configModal) window.configModal.show();
    
    window.cargarDatosConfiguracion();
};

window.cargarDatosConfiguracion = async function() {
    try {
        const response = await fetch('/api/repartidor/configuracion');
        const data = await response.json();
        
        if (data.success) {
            const config = data.configuracion;
            
            document.getElementById('configNombre').value = config.nombre || '';
            document.getElementById('configApellido').value = config.apellido || '';
            document.getElementById('configEmail').value = config.email || '';
            document.getElementById('configTelefono').value = config.telefono || '';
            document.getElementById('configVehiculo').value = config.vehiculo || '';
            document.getElementById('configPatente').value = config.patente || '';
            document.getElementById('configRadio').value = config.radio_trabajo_km || 10;
            document.getElementById('configPuntuacionDisplay').textContent = config.puntuacion || 5.0;
            document.getElementById('configDisponible').checked = config.disponible || false;
            document.getElementById('configActivo').checked = config.activo || false;
            
            document.getElementById('configLoading').style.display = 'none';
            document.getElementById('formConfiguracion').style.display = 'block';
        } else {
            window.mostrarAlertaConfig(data.message || 'Error al cargar datos', 'danger');
        }
    } catch (error) {
        console.error('Error cargando configuración:', error);
        window.mostrarAlertaConfig('Error de conexión: ' + error.message, 'danger');
    }
};

window.guardarConfiguracion = async function(event) {
    event.preventDefault();
    
    const data = {
        nombre: document.getElementById('configNombre').value,
        apellido: document.getElementById('configApellido').value,
        email: document.getElementById('configEmail').value,
        telefono: document.getElementById('configTelefono').value,
        vehiculo: document.getElementById('configVehiculo').value,
        patente: document.getElementById('configPatente').value,
        radio_trabajo_km: parseFloat(document.getElementById('configRadio').value) || 10,
        disponible: document.getElementById('configDisponible').checked,
        activo: document.getElementById('configActivo').checked
    };
    
    const btnSubmit = document.querySelector('#formConfiguracion button[type="submit"]');
    const textoOriginal = btnSubmit.innerHTML;
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';
    
    try {
        const response = await fetch('/api/repartidor/configuracion', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            window.repartidorAutenticado = result.repartidor;
            window.actualizarUIUsuario();
            window.mostrarAlertaConfig('✅ Configuración guardada correctamente', 'success');
            
            setTimeout(() => {
                if (window.configModal) window.configModal.hide();
            }, 1500);
        } else {
            window.mostrarAlertaConfig(result.message || 'Error al guardar', 'danger');
        }
    } catch (error) {
        console.error('Error guardando configuración:', error);
        window.mostrarAlertaConfig('Error de conexión: ' + error.message, 'danger');
    } finally {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = textoOriginal;
    }
};

window.mostrarAlertaConfig = function(mensaje, tipo = 'info') {
    const alert = document.getElementById('configAlert');
    const text = document.getElementById('configAlertText');
    
    alert.className = `mt-3 alert alert-${tipo}`;
    text.textContent = mensaje;
    alert.classList.remove('d-none');
    
    clearTimeout(window.configAlertTimeout);
    window.configAlertTimeout = setTimeout(() => {
        alert.classList.add('d-none');
    }, 5000);
};

// ============================================
// INICIALIZACIÓN
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM cargado - Inicializando dashboard...');
    
    // Inicializar modal de autenticación
    const modalElement = document.getElementById('modalAuth');
    if (modalElement) {
        window.authModal = new bootstrap.Modal(modalElement);
    }
    
    // Inicializar modal de configuración
    const configModalElement = document.getElementById('modalConfiguracion');
    if (configModalElement) {
        window.configModal = new bootstrap.Modal(configModalElement);
    }
    
    // Cargar datos mock
    window.cargarDatosMock();
    window.actualizarDashboard();
    
    // Verificar sesión
    window.verificarSesion();
    
    // Ejecutar test manual después de 3 segundos
    setTimeout(() => {
        console.log('⏰ Ejecutando test manual automático...');
        window.testManual();
    }, 3000);
});

console.log('✅ dashboard.js inicializado correctamente');
console.log('📌 Funciones disponibles:');
console.log('  - testManual()');
console.log('  - forzarMostrarCuenta()');
console.log('  - actualizarUIUsuario()');
console.log('  - verificarSesion()');