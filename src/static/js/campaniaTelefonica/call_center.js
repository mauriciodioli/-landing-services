(function () {
    const dialerState = {
        queue: [],
        index: 0,
        active: false
    };

    function getVisibleCards() {
        return Array.from(document.querySelectorAll('#campania-cards-grid .lead-card'))
            .filter(function (card) {
                return !card.classList.contains('lead-card--empty') && card.dataset.sipUri;
            });
    }

    function collectQueue() {
        dialerState.queue = getVisibleCards().map(function (card) {
            return {
                node: card,
                id: card.dataset.campaniaContactoId,
                sipUri: card.dataset.sipUri,
                telefono: card.dataset.contactoTelefono,
                empresa: card.dataset.contactoEmpresa,
                estado: card.dataset.estado
            };
        });
        dialerState.index = 0;
    }

    function getStatusNode() {
        return document.getElementById('campaign-dialer-status');
    }

    function renderStatus(message) {
        const node = getStatusNode();
        if (node) {
            node.textContent = message;
        }
    }

    function clearHighlights() {
        document.querySelectorAll('#campania-cards-grid .lead-card.is-dialer-current').forEach(function (card) {
            card.classList.remove('is-dialer-current');
        });
    }

    function highlightCurrent(item) {
        clearHighlights();
        if (item && item.node) {
            item.node.classList.add('is-dialer-current');
            item.node.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    async function markAsCalled(item) {
        if (!item || !item.id || !window.DPIACampaniaCards || !window.DPIACampaniaCards.endpointEstado) {
            return;
        }

        try {
            await fetch(window.DPIACampaniaCards.endpointEstado(item.id), {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    estado: 'LLAMADO',
                    nota: 'Llamada iniciada desde modo call center'
                })
            });
        } catch (error) {
            console.error('No fue posible marcar el contacto como LLAMADO', error);
        }
    }

    async function callNext() {
        if (!dialerState.active) {
            renderStatus('Activa el modo call center para iniciar la marcacion secuencial.');
            return;
        }

        if (dialerState.index >= dialerState.queue.length) {
            renderStatus('La cola de llamadas termino. Recarga la cola o cierra el modo call center.');
            clearHighlights();
            return;
        }

        const item = dialerState.queue[dialerState.index];
        highlightCurrent(item);
        renderStatus(
            'Llamando ' + (item.empresa || 'lead sin empresa') + ' · ' + (item.telefono || 'sin telefono') +
            ' (' + String(dialerState.index + 1) + ' de ' + String(dialerState.queue.length) + ')'
        );

        await markAsCalled(item);

        if (window.DPIACampaniaCards && typeof window.DPIACampaniaCards.abrirSip === 'function') {
            window.DPIACampaniaCards.abrirSip(item.sipUri);
        } else {
            window.location.href = item.sipUri;
        }

        dialerState.index += 1;
    }

    function openDialer() {
        const panel = document.getElementById('campaign-dialer-panel');
        if (!panel) {
            return;
        }

        collectQueue();
        dialerState.active = true;
        panel.hidden = false;

        if (!dialerState.queue.length) {
            renderStatus('No hay contactos visibles con SIP para marcar. Ajusta filtros o importa una campana.');
            return;
        }

        renderStatus('Cola lista con ' + String(dialerState.queue.length) + ' contactos visibles. Pulsa "Llamar siguiente" para iniciar.');
    }

    function closeDialer() {
        const panel = document.getElementById('campaign-dialer-panel');
        dialerState.active = false;
        dialerState.queue = [];
        dialerState.index = 0;
        clearHighlights();
        if (panel) {
            panel.hidden = true;
        }
    }

    function refreshQueue() {
        collectQueue();
        if (!dialerState.queue.length) {
            renderStatus('No hay contactos visibles con SIP para marcar.');
            return;
        }
        renderStatus('Cola recargada con ' + String(dialerState.queue.length) + ' contactos visibles.');
    }

    document.addEventListener('DOMContentLoaded', function () {
        const openButton = document.getElementById('campania-auto-call-toggle');
        const nextButton = document.getElementById('campaign-dialer-next');
        const stopButton = document.getElementById('campaign-dialer-stop');
        const refreshButton = document.getElementById('campaign-dialer-refresh');

        if (openButton) {
            openButton.addEventListener('click', openDialer);
        }
        if (nextButton) {
            nextButton.addEventListener('click', callNext);
        }
        if (stopButton) {
            stopButton.addEventListener('click', closeDialer);
        }
        if (refreshButton) {
            refreshButton.addEventListener('click', refreshQueue);
        }

        document.addEventListener('campania:importada', function () {
            if (dialerState.active) {
                refreshQueue();
            }
        });
    });
})();