window.DPIACampaniaCards = {
    endpointListado: "/admin/campania-telefonica/",
    endpointContactos: function (campaniaId) {
        return "/admin/campania-telefonica/" + campaniaId + "/contactos/";
    },
    endpointEstado: function (campaniaContactoId) {
        return "/admin/campania-telefonica/contacto/" + campaniaContactoId + "/estado/";
    },
    abrirSip: function (sipUri) {
        if (!sipUri) {
            return;
        }
        window.location.href = sipUri;
    },
    abrirWhatsapp: function (whatsappUri) {
        if (!whatsappUri) {
            return;
        }
        window.open(whatsappUri, '_blank', 'noopener');
    },
    abrirEmail: function (emailUri) {
        if (!emailUri) {
            return;
        }
        window.location.href = emailUri;
    },
    cerrarMenus: function () {
        document.querySelectorAll('.lead-card__menu.is-open').forEach(function (menuNode) {
            menuNode.classList.remove('is-open');
        });
    }
};

(function () {
    const state = {
        currentCampaignId: null,
        currentCampaignSummary: null,
        currentItems: [],
        currentPage: 1,
        pageSize: 20,
        totalItems: 0,
        hasNext: false,
        currentUserId: null
    };

    function getAccessToken() {
        try {
            if (!window.DPIACampaniaImportador || !window.DPIACampaniaImportador.accessTokenStorageKey) {
                return '';
            }

            return (window.localStorage.getItem(window.DPIACampaniaImportador.accessTokenStorageKey) || '').trim();
        } catch (error) {
            return '';
        }
    }

    function getStatusFilterStorageKey() {
        const accessToken = getAccessToken();
        if (!accessToken) {
            return '';
        }

        return 'dpia-campania-status-filter:' + accessToken;
    }

    function persistStatusFilterValue(value) {
        const storageKey = getStatusFilterStorageKey();
        if (!storageKey) {
            return;
        }

        try {
            window.localStorage.setItem(storageKey, value || '');
        } catch (error) {
            // noop
        }
    }

    function restoreStatusFilterValue() {
        const storageKey = getStatusFilterStorageKey();
        if (!storageKey) {
            return '';
        }

        try {
            return window.localStorage.getItem(storageKey) || '';
        } catch (error) {
            return '';
        }
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function renderEmptyState(grid) {
        grid.innerHTML = [
            '<article class="lead-card lead-card--empty">',
            '<h2>Sin contactos cargados</h2>',
            '<p>' + escapeHtml(grid.dataset.emptyMessage || 'No hay datos para mostrar.') + '</p>',
            '</article>'
        ].join("");
    }

    function renderAuthRequiredState(grid) {
        grid.innerHTML = [
            '<article class="lead-card lead-card--empty">',
            '<h2>Debes autenticarte</h2>',
            '<p>Valida el usuario importador para cargar solo las campanas y sheets de ese usuario.</p>',
            '</article>'
        ].join('');
    }

    function renderCampaignSummary(summaryNode, campaign) {
        if (!summaryNode || !campaign) {
            return;
        }

        summaryNode.innerHTML = [
            '<strong>Campana actual</strong>',
            '<span>' + escapeHtml(campaign.nombre || 'Campania telefonica') + ' · ' + escapeHtml(String(campaign.totalRegistros || 0)) + ' contactos</span>'
        ].join("");
    }

    function renderPagination() {
        const paginationNode = document.getElementById('campania-pagination');
        const summaryNode = document.getElementById('campania-pagination-summary');
        const statusNode = document.getElementById('campania-page-status');
        const prevButton = document.getElementById('campania-page-prev');
        const nextButton = document.getElementById('campania-page-next');
        const pageSizeSelect = document.getElementById('campania-page-size');

        if (!paginationNode || !summaryNode || !statusNode || !prevButton || !nextButton || !pageSizeSelect) {
            return;
        }

        const pageStart = state.totalItems ? ((state.currentPage - 1) * state.pageSize) + 1 : 0;
        const pageEnd = state.totalItems ? Math.min(state.totalItems, ((state.currentPage - 1) * state.pageSize) + state.currentItems.length) : 0;

        paginationNode.hidden = state.totalItems <= 0;
        summaryNode.textContent = 'Mostrando ' + pageStart + '-' + pageEnd + ' de ' + state.totalItems + ' contactos';
        statusNode.textContent = 'Pagina ' + state.currentPage;
        prevButton.disabled = state.currentPage <= 1;
        nextButton.disabled = !state.hasNext;
        pageSizeSelect.value = String(state.pageSize);
    }

    function renderCardsFromState() {
        const grid = document.getElementById('campania-cards-grid');
        if (!grid) {
            return;
        }

        renderCards(grid, state.currentItems || []);
        renderPagination();
    }

    function upsertCurrentItem(updatedItem) {
        const currentItems = Array.isArray(state.currentItems) ? state.currentItems.slice() : [];
        const targetIndex = currentItems.findIndex(function (item) {
            return String(item.id) === String(updatedItem.id);
        });

        if (targetIndex === -1) {
            currentItems.unshift(updatedItem);
        } else {
            currentItems[targetIndex] = updatedItem;
        }

        state.currentItems = currentItems;
    }

    function removeCurrentItem(campaniaContactoId) {
        state.currentItems = (state.currentItems || []).filter(function (item) {
            return String(item.id) !== String(campaniaContactoId);
        });
    }

    function getSelectedStatusFilter() {
        const statusFilter = document.getElementById('campania-status-filter');
        return statusFilter ? statusFilter.value : '';
    }

    function syncVisibleCardsWithSelectedFilter() {
        const selectedFilter = getSelectedStatusFilter();
        const grid = document.getElementById('campania-cards-grid');
        if (!grid || !selectedFilter) {
            return;
        }

        grid.querySelectorAll('.lead-card select[data-campania-contacto-id]').forEach(function (selectNode) {
            const card = selectNode.closest('.lead-card');
            const campaniaContactoId = selectNode.getAttribute('data-campania-contacto-id');

            if (!card || !campaniaContactoId) {
                return;
            }

            if (selectNode.value !== selectedFilter) {
                removeCurrentItem(campaniaContactoId);
                card.remove();
            }
        });

        if (!grid.querySelector('.lead-card select[data-campania-contacto-id]')) {
            renderCardsFromState();
        }
    }

    function buildEmailUri(email, empresa) {
        const normalizedEmail = String(email || '').trim();
        if (!normalizedEmail || normalizedEmail.indexOf('@') === -1) {
            return '';
        }

        const subject = encodeURIComponent('DPIA CRM · Contacto comercial');
        const body = encodeURIComponent(
            'Hola' + (empresa ? ' ' + empresa : '') + ',\n\nTe contacto desde DPIA CRM.\n'
        );

        return 'mailto:' + normalizedEmail + '?subject=' + subject + '&body=' + body;
    }

    function extractEmailFromUri(emailUri) {
        const normalizedUri = String(emailUri || '').trim();
        if (!normalizedUri.toLowerCase().startsWith('mailto:')) {
            return '';
        }

        const address = normalizedUri.slice(7).split('?')[0].trim();
        return address && address.indexOf('@') !== -1 ? decodeURIComponent(address) : '';
    }

    function extractBodyFromUri(emailUri) {
        const normalizedUri = String(emailUri || '').trim();
        const queryString = normalizedUri.split('?')[1] || '';
        const params = new URLSearchParams(queryString);
        return params.get('body') || '';
    }

    async function copyEmailToClipboard(emailAddress) {
        if (!emailAddress || !navigator.clipboard || typeof navigator.clipboard.writeText !== 'function') {
            return false;
        }

        try {
            await navigator.clipboard.writeText(emailAddress);
            return true;
        } catch (error) {
            return false;
        }
    }

    async function shareEmailAction(emailUri, emailAddress, empresa) {
        if (!navigator.share || !emailUri) {
            return false;
        }

        const body = extractBodyFromUri(emailUri);

        try {
            await navigator.share({
                title: 'DPIA CRM · Contacto comercial',
                text: [
                    empresa ? 'Contacto: ' + empresa : 'Contacto comercial',
                    emailAddress ? 'Email: ' + emailAddress : '',
                    body
                ].filter(Boolean).join('\n\n')
            });
            return true;
        } catch (error) {
            if (error && error.name === 'AbortError') {
                return true;
            }

            return false;
        }
    }

    function renderMenuOption(label, className, channel, uri) {
        const disabled = !uri;
        return [
            '<button class="lead-card__menu-option ' + className + ' btn-contact-action" type="button" data-channel="' + escapeHtml(channel) + '" data-uri="' + escapeHtml(uri || '') + '"' + (disabled ? ' disabled' : '') + '>',
            escapeHtml(label),
            '</button>'
        ].join('');
    }

    function renderCards(grid, items) {
        if (!items || !items.length) {
            renderEmptyState(grid);
            return;
        }

        grid.innerHTML = items.map(function (item) {
            const contacto = item.contacto || {};
            const acciones = item.acciones || {};
            const telefonoVisible = contacto.telefono_original || contacto.telefono_normalizado || "Sin telefono";
            const empresa = contacto.empresa || "Lead sin empresa";
            const ciudad = contacto.ciudad || "Ciudad no informada";
            const email = contacto.email || "Sin email";
            const nota = item.observacion || "";
            const emailUri = buildEmailUri(contacto.email, empresa);

            return [
                '<article class="lead-card" data-phone="' + escapeHtml(contacto.telefono_normalizado || "") + '" data-campania-contacto-id="' + escapeHtml(String(item.id || '')) + '" data-contacto-telefono="' + escapeHtml(telefonoVisible) + '" data-contacto-empresa="' + escapeHtml(empresa) + '" data-sip-uri="' + escapeHtml(acciones.sip_uri || '') + '" data-estado="' + escapeHtml(item.estado || '') + '">',
                '<div class="lead-card__header">',
                '<p class="lead-card__tag">Campania #' + escapeHtml(String(item.campania_id || "")) + '</p>',
                '<span class="lead-card__provider">' + escapeHtml(window.DPIACampaniaImportador.sipProvider) + '</span>',
                '</div>',
                '<h2>' + escapeHtml(empresa) + '</h2>',
                '<p class="lead-card__line">📞 ' + escapeHtml(telefonoVisible) + '</p>',
                '<p class="lead-card__line">📍 ' + escapeHtml(ciudad) + '</p>',
                '<p class="lead-card__line">✉️ ' + escapeHtml(email) + '</p>',
                '<div class="lead-card__actions">',
                '<div class="lead-card__menu-wrap">',
                '<button class="action-button action-button--call btn-llamar-menu" type="button" aria-expanded="false">Llamar</button>',
                '<div class="lead-card__menu" hidden>',
                renderMenuOption('VoIP', 'action-button--call', 'sip', acciones.sip_uri || ''),
                renderMenuOption('WhatsApp', 'action-button--wa', 'whatsapp', acciones.whatsapp_uri || ''),
                renderMenuOption('Enviar email', 'action-button--email', 'email', emailUri),
                '</div>',
                '</div>',
                '</div>',
                '<label class="lead-card__field">',
                '<span>Estado</span>',
                '<select data-campania-contacto-id="' + escapeHtml(String(item.id)) + '" data-previous-value="' + escapeHtml(item.estado || '') + '">',
                window.DPIACampaniaFiltros.estados.map(function (estado) {
                    const selected = estado === item.estado ? ' selected' : '';
                    return '<option value="' + escapeHtml(estado) + '"' + selected + '>' + escapeHtml(estado) + '</option>';
                }).join(''),
                '</select>',
                '</label>',
                '<label class="lead-card__field">',
                '<span>Notas</span>',
                '<textarea rows="3" data-campania-contacto-id="' + escapeHtml(String(item.id || '')) + '" data-previous-value="' + escapeHtml(nota) + '" placeholder="Registrar resultado de la llamada">' + escapeHtml(nota) + '</textarea>',
                '</label>',
                '</article>'
            ].join('');
        }).join('');
    }

    async function fetchJSON(url) {
        const accessToken = getAccessToken();
        const headers = {};
        if (accessToken) {
            headers.Authorization = 'Bearer ' + accessToken;
        }

        const response = await fetch(url, { headers: headers });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'No fue posible cargar los datos');
        }
        return data;
    }

    async function patchJSON(url, payload) {
        const accessToken = getAccessToken();
        const headers = {
            'Content-Type': 'application/json'
        };
        if (accessToken) {
            headers.Authorization = 'Bearer ' + accessToken;
        }

        const response = await fetch(url, {
            method: 'PATCH',
            headers: headers,
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'No fue posible actualizar el estado');
        }
        return data;
    }

    function buildContactsUrl(campaniaId) {
        const url = new URL(window.DPIACampaniaCards.endpointContactos(campaniaId), window.location.origin);
        const statusFilter = document.getElementById('campania-status-filter');
        const searchInput = document.getElementById('campania-search');

        url.searchParams.set('page', String(state.currentPage));
        url.searchParams.set('page_size', String(state.pageSize));

        if (statusFilter && statusFilter.value) {
            url.searchParams.set('estado', statusFilter.value);
        }

        if (searchInput && searchInput.value.trim()) {
            url.searchParams.set('q', searchInput.value.trim());
        }

        return url.toString();
    }

    async function loadCampaignContacts(campaniaId, summary) {
        const grid = document.getElementById('campania-cards-grid');
        if (!grid || !campaniaId) {
            return;
        }

        state.currentCampaignId = campaniaId;
        state.currentCampaignSummary = summary || state.currentCampaignSummary;

        grid.innerHTML = '<article class="lead-card lead-card--empty"><h2>Cargando contactos...</h2></article>';

        try {
            const data = await fetchJSON(buildContactsUrl(campaniaId));
            state.currentItems = data.items || [];
            state.currentPage = data.page || state.currentPage;
            state.pageSize = data.page_size || state.pageSize;
            state.totalItems = data.total || 0;
            state.hasNext = Boolean(data.has_next);
            renderCampaignSummary(document.getElementById('campania-actual-resumen'), state.currentCampaignSummary);
            renderCardsFromState();
        } catch (error) {
            state.currentItems = [];
            state.totalItems = 0;
            state.hasNext = false;
            grid.innerHTML = '<article class="lead-card lead-card--empty"><h2>Error cargando contactos</h2><p>' + escapeHtml(error.message) + '</p></article>';
            renderPagination();
        }
    }

    async function loadLatestCampaign() {
        const grid = document.getElementById('campania-cards-grid');
        const summaryNode = document.getElementById('campania-actual-resumen');
        if (!grid) {
            return;
        }

        if (!state.currentUserId) {
            state.currentCampaignId = null;
            state.currentCampaignSummary = null;
            state.currentItems = [];
            state.currentPage = 1;
            state.totalItems = 0;
            state.hasNext = false;
            renderCampaignSummary(summaryNode, {
                nombre: 'Sin campanas cargadas',
                totalRegistros: 0
            });
            renderAuthRequiredState(grid);
            renderPagination();
            return;
        }

        try {
            const url = new URL(window.DPIACampaniaCards.endpointListado, window.location.origin);
            url.searchParams.set('page', '1');
            url.searchParams.set('page_size', '1');

            const data = await fetchJSON(url.toString());
            const campaign = data.items && data.items[0];
            if (!campaign) {
                renderEmptyState(grid);
                renderCampaignSummary(summaryNode, {
                    nombre: state.currentUserId ? 'Sin campanas para este usuario' : 'Sin datos importados todavia.',
                    totalRegistros: 0
                });
                return;
            }
            await loadCampaignContacts(campaign.id, {
                nombre: campaign.nombre,
                totalRegistros: campaign.total_registros
            });
            renderCampaignSummary(summaryNode, state.currentCampaignSummary);
        } catch (error) {
            renderEmptyState(grid);
        }
    }

    let filterTimeoutId = null;

    function reloadCurrentCampaign() {
        if (!state.currentCampaignId) {
            return;
        }
        loadCampaignContacts(state.currentCampaignId, state.currentCampaignSummary);
    }

    async function saveContactNote(textarea) {
        const card = textarea.closest('.lead-card');
        const campaniaContactoId = textarea.getAttribute('data-campania-contacto-id');
        const previousValue = textarea.getAttribute('data-previous-value') || '';
        const nextValue = textarea.value;

        if (!campaniaContactoId || nextValue === previousValue) {
            return;
        }

        textarea.disabled = true;
        if (card) {
            card.classList.add('lead-card--saving');
        }

        try {
            const data = await patchJSON(window.DPIACampaniaCards.endpointEstado(campaniaContactoId), {
                nota: nextValue
            });

            const updatedItem = data && data.item
                ? data.item
                : (state.currentItems || []).find(function (item) {
                    return String(item.id) === String(campaniaContactoId);
                });

            if (updatedItem) {
                updatedItem.observacion = nextValue;
                upsertCurrentItem(updatedItem);
            }

            textarea.setAttribute('data-previous-value', nextValue);
        } catch (error) {
            textarea.value = previousValue;
            window.alert(error.message || 'No fue posible guardar la nota');
        } finally {
            textarea.disabled = false;
            if (card) {
                card.classList.remove('lead-card--saving');
            }
        }
    }

    async function updateContactStatus(selectNode) {
        const card = selectNode.closest('.lead-card');
        const textarea = card ? card.querySelector('textarea') : null;
        const campaniaContactoId = selectNode.getAttribute('data-campania-contacto-id');
        const previousValue = selectNode.getAttribute('data-previous-value') || '';
        const selectedFilter = getSelectedStatusFilter();
        const nextValue = selectNode.value;
        const shouldHideCard = Boolean(card && selectedFilter && nextValue !== selectedFilter);

        if (!campaniaContactoId) {
            return;
        }

        selectNode.disabled = true;
        if (card) {
            card.classList.add('lead-card--saving');
        }
        if (shouldHideCard && card) {
            card.style.display = 'none';
        }

        try {
            const data = await patchJSON(window.DPIACampaniaCards.endpointEstado(campaniaContactoId), {
                estado: nextValue,
                nota: textarea ? textarea.value : null
            });
            selectNode.setAttribute('data-previous-value', nextValue);

            const updatedItem = data && data.item
                ? data.item
                : (state.currentItems || []).find(function (item) {
                    return String(item.id) === String(campaniaContactoId);
                });

            if (updatedItem) {
                updatedItem.estado = nextValue;
                updatedItem.observacion = textarea ? textarea.value : updatedItem.observacion;
            }

            if (shouldHideCard) {
                removeCurrentItem(campaniaContactoId);
                state.totalItems = Math.max(0, state.totalItems - 1);
                if (card) {
                    card.remove();
                }

                if (!state.currentItems.length && state.currentPage > 1) {
                    state.currentPage -= 1;
                    reloadCurrentCampaign();
                    return;
                }
                renderCardsFromState();
                return;
            }

            if (updatedItem) {
                upsertCurrentItem(updatedItem);
                if (card) {
                    card.setAttribute('data-estado', nextValue);
                    card.style.display = '';
                }
            }

            syncVisibleCardsWithSelectedFilter();
        } catch (error) {
            selectNode.value = previousValue;
            if (card) {
                card.style.display = '';
            }
            window.alert(error.message || 'No fue posible actualizar el estado');
        } finally {
            selectNode.disabled = false;
            if (card) {
                card.classList.remove('lead-card--saving');
            }
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        const grid = document.getElementById('campania-cards-grid');
        const statusFilter = document.getElementById('campania-status-filter');
        const searchInput = document.getElementById('campania-search');
        const prevButton = document.getElementById('campania-page-prev');
        const nextButton = document.getElementById('campania-page-next');
        const pageSizeSelect = document.getElementById('campania-page-size');
        if (!grid) {
            return;
        }

        if (statusFilter) {
            statusFilter.value = restoreStatusFilterValue();
        }
        renderAuthRequiredState(grid);
        renderPagination();

        if (statusFilter) {
            statusFilter.addEventListener('change', function () {
                persistStatusFilterValue(statusFilter.value);
                state.currentPage = 1;
                reloadCurrentCampaign();
            });
        }

        if (searchInput) {
            searchInput.addEventListener('input', function () {
                window.clearTimeout(filterTimeoutId);
                filterTimeoutId = window.setTimeout(function () {
                    state.currentPage = 1;
                    reloadCurrentCampaign();
                }, 250);
            });
        }

        if (pageSizeSelect) {
            pageSizeSelect.addEventListener('change', function () {
                state.pageSize = Number(pageSizeSelect.value) || 20;
                state.currentPage = 1;
                reloadCurrentCampaign();
            });
        }

        if (prevButton) {
            prevButton.addEventListener('click', function () {
                if (state.currentPage <= 1) {
                    return;
                }
                state.currentPage -= 1;
                reloadCurrentCampaign();
            });
        }

        if (nextButton) {
            nextButton.addEventListener('click', function () {
                if (!state.hasNext) {
                    return;
                }
                state.currentPage += 1;
                reloadCurrentCampaign();
            });
        }

        grid.addEventListener('click', async function (event) {
            const menuToggle = event.target.closest('.btn-llamar-menu');
            if (menuToggle) {
                const wrapNode = menuToggle.closest('.lead-card__menu-wrap');
                const menuNode = wrapNode ? wrapNode.querySelector('.lead-card__menu') : null;
                const shouldOpen = Boolean(menuNode && menuNode.hidden);

                window.DPIACampaniaCards.cerrarMenus();

                if (menuNode) {
                    menuNode.hidden = !shouldOpen;
                    menuNode.classList.toggle('is-open', shouldOpen);
                }

                menuToggle.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
                return;
            }

            const button = event.target.closest('.btn-contact-action');
            if (!button) {
                return;
            }

            const channel = button.getAttribute('data-channel');
            const uri = button.getAttribute('data-uri');
            if (!uri) {
                return;
            }

            window.DPIACampaniaCards.cerrarMenus();

            if (channel === 'sip') {
                window.DPIACampaniaCards.abrirSip(uri);
                return;
            }

            if (channel === 'whatsapp') {
                window.DPIACampaniaCards.abrirWhatsapp(uri);
                return;
            }

            if (channel === 'email') {
                const card = button.closest('.lead-card');
                const empresa = card ? (card.getAttribute('data-contacto-empresa') || '') : '';
                const emailAddress = extractEmailFromUri(uri);

                await copyEmailToClipboard(emailAddress);

                const didShare = await shareEmailAction(uri, emailAddress, empresa);
                if (!didShare) {
                    window.DPIACampaniaCards.abrirEmail(uri);
                }
            }
        });

        document.addEventListener('click', function (event) {
            if (event.target.closest('.lead-card__menu-wrap')) {
                return;
            }

            window.DPIACampaniaCards.cerrarMenus();
            document.querySelectorAll('.btn-llamar-menu[aria-expanded="true"]').forEach(function (buttonNode) {
                buttonNode.setAttribute('aria-expanded', 'false');
            });
        });

        grid.addEventListener('change', function (event) {
            const selectNode = event.target.closest('select[data-campania-contacto-id]');
            if (!selectNode) {
                const textareaNode = event.target.closest('textarea[data-campania-contacto-id]');
                if (!textareaNode) {
                    return;
                }
                saveContactNote(textareaNode);
                return;
            }
            updateContactStatus(selectNode);
        });

        grid.addEventListener('focusout', function (event) {
            const textareaNode = event.target.closest('textarea[data-campania-contacto-id]');
            if (!textareaNode) {
                return;
            }
            saveContactNote(textareaNode);
        });
    });

    document.addEventListener('campania:importada', function (event) {
        const detail = event.detail || {};
        loadCampaignContacts(detail.campaniaId, {
            nombre: detail.nombre,
            totalRegistros: detail.totalRegistros
        });
    });

    document.addEventListener('campania:auth-user', function (event) {
        const detail = event.detail || {};
        const user = detail.user || null;
        state.currentUserId = user && user.id ? Number(user.id) : null;
        state.currentPage = 1;
        loadLatestCampaign();
    });

    document.addEventListener('campania:eliminada', function () {
        state.currentPage = 1;
        loadLatestCampaign();
    });
})();