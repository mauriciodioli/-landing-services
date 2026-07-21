(function () {
    const rootNode = document.getElementById("campania-telefonica-app");
    let currentAuthenticatedUser = null;
    const runtimeConfig = {
        sipProvider: rootNode ? rootNode.dataset.sipProvider : "Proveedor SIP",
        sipSoftphone: rootNode ? rootNode.dataset.sipSoftphone : "Zoiper",
        sipServer: rootNode ? rootNode.dataset.sipServer : ""
    };

    window.DPIACampaniaImportador = {
    endpointAuth: "/admin/campania-telefonica/auth-importador/",
    endpointAuthSession: "/admin/campania-telefonica/auth-importador/",
    endpointAnalizar: "/admin/campania-telefonica/analizar/",
    endpointImportar: "/admin/campania-telefonica/importar/",
    endpointHistorial: "/admin/campania-telefonica/historial/",
    endpointEliminarCampania: function (campaniaId) {
        return "/admin/campania-telefonica/" + campaniaId + "/";
    },
    endpointUI: "/admin/campania-telefonica/ui/",
    endpointGuiaSip: "/admin/campania-telefonica/guia-sip/",
    endpointSip: "/campaniaTelefonica/generarSipLink/",
    sipSoftphone: runtimeConfig.sipSoftphone || "Zoiper",
    sipProvider: runtimeConfig.sipProvider || "Proveedor SIP",
    storageKey: "dpia-campania-sheet-history",
    accessTokenStorageKey: "access_token"
};

    function getAccessToken() {
        try {
            return (window.localStorage.getItem(window.DPIACampaniaImportador.accessTokenStorageKey) || "").trim();
        } catch (error) {
            return "";
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

    function serializeForm(form) {
        const formData = new FormData(form);
        const payload = {};

        formData.forEach(function (value, key) {
            if (value === "") {
                return;
            }
            payload[key] = value;
        });

        if (payload.cantidad_registros) {
            payload.cantidad_registros = Number(payload.cantidad_registros);
        }
        if (payload.usuario_creador_id) {
            payload.usuario_creador_id = Number(payload.usuario_creador_id);
        }

        return payload;
    }

    function sanitizeHistoryPayload(payload) {
        return {
            campania_id: payload.campania_id || "",
            sheet_id: payload.sheet_id || "",
            sheet_name: payload.sheet_name || "",
            sheet_tab: payload.sheet_tab || "",
            nombre: payload.nombre || "",
            cantidad_registros: payload.cantidad_registros || "",
            usuario_creador_id: payload.usuario_creador_id || ""
        };
    }

    async function postJSON(url, payload) {
        const accessToken = getAccessToken();
        const headers = {
            "Content-Type": "application/json"
        };

        if (accessToken) {
            headers.Authorization = "Bearer " + accessToken;
        }

        const response = await fetch(url, {
            method: "POST",
            headers: headers,
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "No fue posible completar la operacion");
        }

        return data;
    }

    async function deleteJSON(url) {
        const accessToken = getAccessToken();
        const headers = {};

        if (accessToken) {
            headers.Authorization = "Bearer " + accessToken;
        }

        const response = await fetch(url, {
            method: "DELETE",
            headers: headers
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "No fue posible eliminar la campania");
        }

        return data;
    }

    function setResult(resultNode, payload) {
        resultNode.hidden = false;
        resultNode.textContent = JSON.stringify(payload, null, 2);
    }

    async function getJSON(url) {
        const accessToken = getAccessToken();
        const headers = {};

        if (accessToken) {
            headers.Authorization = "Bearer " + accessToken;
        }

        const response = await fetch(url, {
            method: "GET",
            headers: headers
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "No fue posible completar la operacion");
        }

        return data;
    }

    function fillForm(form, payload) {
        Object.keys(payload).forEach(function (key) {
            const field = form.elements.namedItem(key);
            if (!field) {
                return;
            }
            field.value = payload[key];
        });
    }

    async function fetchHistory() {
        const data = await getJSON(window.DPIACampaniaImportador.endpointHistorial + '?limit=20');
        const items = Array.isArray(data.items) ? data.items : [];
        return items.map(function (item) {
            return {
                campania_id: item.id,
                sheet_id: item.sheet_id || '',
                sheet_name: item.sheet_name || '',
                sheet_tab: item.sheet_tab || '',
                nombre: item.nombre || '',
                cantidad_registros: item.total_registros || '',
                usuario_creador_id: item.usuario_creador_id || '',
                fecha_creacion: item.fecha_creacion || ''
            };
        });
    }

    function renderHistory(historyNode, items) {
        if (!items.length) {
            historyNode.innerHTML = [
                '<article class="campania-history-item campania-history-item--empty">',
                '<h4>Sin historial guardado</h4>',
                '<p>Analiza o importa una sheet y aparecera aqui para reutilizarla rapido.</p>',
                '</article>'
            ].join("");
            return;
        }

        historyNode.innerHTML = items.map(function (item, index) {
            const canDeleteCampaign = Boolean(item.campania_id);
            return [
                '<article class="campania-history-item">',
                '<div>',
                '<h4>' + escapeHtml(item.nombre || item.sheet_tab || item.sheet_name || 'Sheet guardada') + '</h4>',
                '<p><strong>Campania ID:</strong> ' + escapeHtml(String(item.campania_id || 'No registrada')) + '</p>',
                '<p><strong>Sheet ID:</strong> ' + escapeHtml(item.sheet_id) + '</p>',
                '<p><strong>Tab:</strong> ' + escapeHtml(item.sheet_tab) + '</p>',
                '<p><strong>Sheet:</strong> ' + escapeHtml(item.sheet_name) + '</p>',
                '<p><strong>Registros:</strong> ' + escapeHtml(String(item.cantidad_registros || '')) + '</p>',
                '</div>',
                '<div class="campania-history-item__actions">',
                '<button class="primary-button" type="button" data-history-open-index="' + index + '"' + (canDeleteCampaign ? '' : ' disabled') + '>Abrir campana</button>',
                '<button class="secondary-button" type="button" data-history-reimport-index="' + index + '">Reimportar sheet</button>',
                '<button class="ghost-button campania-history-delete-button" type="button" data-history-delete-key="' + escapeHtml(item.history_key || '') + '" data-history-delete-index="' + index + '"' + (canDeleteCampaign ? '' : ' disabled') + '><span class="button-spinner" aria-hidden="true"></span><span class="button-label">Eliminar</span></button>',
                '</div>',
                '</article>'
            ].join('');
        }).join('');
    }

    document.addEventListener("DOMContentLoaded", function () {
        const modal = document.getElementById("campania-telefonica-modal-importar");
        const form = document.getElementById("campania-importador-form");
        const resultNode = document.getElementById("campania-importador-resultado");
        const authStatusNode = document.getElementById("campania-importador-auth-status");
        const activeUserNode = document.getElementById("campania-usuario-activo");
        const historyModal = document.getElementById("campania-history-modal");
        const historyNode = document.getElementById("campania-history-list");
        const openButton = document.querySelector('[data-action="abrir-importador"]');
        const closeButtons = document.querySelectorAll('[data-action="cerrar-importador"]');
        const authButton = document.querySelector('[data-action="autenticar-importador"]');
        const analyzeButton = document.querySelector('[data-action="analizar-sheet"]');
        const submitButton = document.querySelector('[data-action="submit-importar-sheet"]');
        const openHistoryButton = document.querySelector('[data-action="abrir-historial-sheet"]');
        const closeHistoryButton = document.querySelector('[data-action="cerrar-historial-sheet"]');
        const togglePasswordButton = document.querySelector('[data-action="toggle-password-visibility"]');
        const emailInput = form ? form.elements.namedItem("correo_electronico") : null;
        const passwordInput = form ? form.elements.namedItem("password") : null;
        const userIdInput = form ? form.elements.namedItem("usuario_creador_id") : null;

        if (!modal || !form || !resultNode || !openButton) {
            return;
        }

        function setAuthStatus(message, isError) {
            if (!authStatusNode) {
                return;
            }

            authStatusNode.textContent = message;
            authStatusNode.classList.toggle("is-error", Boolean(isError));
            authStatusNode.classList.toggle("is-success", Boolean(message && !isError));
        }

        function setImportActionsEnabled(enabled) {
            if (analyzeButton) {
                analyzeButton.disabled = !enabled;
            }

            if (submitButton) {
                submitButton.disabled = !enabled;
            }

            if (openHistoryButton) {
                openHistoryButton.disabled = !enabled;
                openHistoryButton.setAttribute("aria-disabled", enabled ? "false" : "true");
                openHistoryButton.title = enabled
                    ? "Abrir historial de sheets"
                    : "Debes iniciar sesion para usar el historial de sheets";
            }

            if (authButton) {
                authButton.hidden = Boolean(enabled);
            }
        }

        function clearAuthenticationState() {
            currentAuthenticatedUser = null;
            if (activeUserNode) {
                activeUserNode.innerHTML = '<strong>Usuario activo</strong><span>No autenticado</span>';
            }
            if (userIdInput) {
                userIdInput.value = "";
            }
            if (emailInput) {
                emailInput.readOnly = false;
            }
            if (passwordInput) {
                passwordInput.required = true;
                passwordInput.disabled = false;
            }
            setImportActionsEnabled(false);
            setAuthStatus("No existe access_token. Debes logearte antes de analizar o importar la hoja.", false);
            document.dispatchEvent(new CustomEvent('campania:auth-user', {
                detail: { user: null }
            }));
        }

        function applyAuthenticatedUser(user) {
            currentAuthenticatedUser = user || null;
            if (activeUserNode) {
                activeUserNode.innerHTML = user && user.id
                    ? '<strong>Usuario activo</strong><span>' + escapeHtml(user.correo_electronico || 'usuario') + ' · ID ' + escapeHtml(String(user.id)) + '</span>'
                    : '<strong>Usuario activo</strong><span>No autenticado</span>';
            }
            if (userIdInput) {
                userIdInput.value = user && user.id ? String(user.id) : "";
            }

            if (emailInput && user && user.correo_electronico) {
                emailInput.value = user.correo_electronico;
                emailInput.readOnly = true;
            }

            if (passwordInput) {
                passwordInput.value = "";
                passwordInput.required = false;
                passwordInput.disabled = true;
            }

            setImportActionsEnabled(Boolean(user && user.id));
            if (user && user.id) {
                setAuthStatus("Autenticado como " + (user.correo_electronico || "usuario") + " · ID " + user.id, false);
                document.dispatchEvent(new CustomEvent('campania:auth-user', {
                    detail: { user: user }
                }));
            } else {
                clearAuthenticationState();
            }
        }

        async function authenticateImporter() {
            const payload = serializeForm(form);
            const data = await postJSON(window.DPIACampaniaImportador.endpointAuth, {
                correo_electronico: payload.correo_electronico,
                password: payload.password
            });

            applyAuthenticatedUser(data.user || null);
            return data;
        }

        async function restoreAuthenticationFromStorage() {
            const accessToken = getAccessToken();
            if (!accessToken) {
                clearAuthenticationState();
                return null;
            }

            setAuthStatus("Restaurando sesion desde access_token...", false);
            const data = await getJSON(window.DPIACampaniaImportador.endpointAuthSession);
            applyAuthenticatedUser(data.user || null);
            return data;
        }

        function openModal() {
            modal.hidden = false;
        }

        function closeModal() {
            modal.hidden = true;
        }

        function closeAllImportModals() {
            closeHistoryModal();
            closeModal();
        }

        async function openHistoryModal() {
            if (!historyModal || !historyNode) {
                return;
            }
            historyNode.innerHTML = '<article class="campania-history-item campania-history-item--empty"><h4>Cargando historial...</h4></article>';
            historyModal.hidden = false;
            try {
                renderHistory(historyNode, await fetchHistory());
            } catch (error) {
                historyNode.innerHTML = '<article class="campania-history-item campania-history-item--empty"><h4>Error cargando historial</h4><p>' + escapeHtml(error.message || 'No fue posible obtener el historial del usuario.') + '</p></article>';
            }
        }

        function closeHistoryModal() {
            if (historyModal) {
                historyModal.hidden = true;
            }
        }

        function setImportLoading(isLoading) {
            if (!submitButton) {
                return;
            }

            submitButton.disabled = isLoading || !userIdInput || !userIdInput.value;
            submitButton.classList.toggle('is-loading', isLoading);
        }

        clearAuthenticationState();

        restoreAuthenticationFromStorage().catch(function () {
            clearAuthenticationState();
        });

        openButton.addEventListener("click", openModal);
        closeButtons.forEach(function (button) {
            button.addEventListener("click", closeModal);
        });
        if (authButton) {
            authButton.addEventListener("click", async function () {
                authButton.disabled = true;
                setAuthStatus("Validando acceso...", false);

                try {
                    await authenticateImporter();
                } catch (error) {
                    clearAuthenticationState();
                    setAuthStatus(error.message || "No fue posible autenticar el usuario", true);
                } finally {
                    authButton.disabled = false;
                }
            });
        }
        if (openHistoryButton) {
            openHistoryButton.addEventListener("click", function () {
                if (openHistoryButton.disabled) {
                    return;
                }
                openHistoryModal();
            });
        }
        if (togglePasswordButton && passwordInput) {
            togglePasswordButton.addEventListener('click', function () {
                const isHidden = passwordInput.type === 'password';
                passwordInput.type = isHidden ? 'text' : 'password';
                togglePasswordButton.textContent = isHidden ? 'Ocultar' : 'Mostrar';
                togglePasswordButton.setAttribute('aria-pressed', isHidden ? 'true' : 'false');
            });
        }
        if (closeHistoryButton) {
            closeHistoryButton.addEventListener("click", closeHistoryModal);
        }

        [emailInput, passwordInput].forEach(function (input) {
            if (!input) {
                return;
            }

            input.addEventListener("input", function () {
                if (input === emailInput || (passwordInput && !passwordInput.disabled)) {
                    if (authButton) {
                        authButton.hidden = false;
                    }
                }
                clearAuthenticationState();
            });
        });

        if (historyNode) {
            historyNode.addEventListener('click', async function (event) {
                const deleteButton = event.target.closest('[data-history-delete-index]');
                if (deleteButton) {
                    const index = Number(deleteButton.getAttribute('data-history-delete-index'));
                    const items = await fetchHistory();
                    const item = items[index];
                    if (!item) {
                        return;
                    }

                    if (!window.confirm('Se eliminara la campania importada y su historial relacionado.')) {
                        return;
                    }

                    deleteButton.disabled = true;
                    deleteButton.classList.add('is-loading');
                    const labelNode = deleteButton.querySelector('.button-label');
                    if (labelNode) {
                        labelNode.textContent = 'Eliminando...';
                    }
                    deleteJSON(window.DPIACampaniaImportador.endpointEliminarCampania(item.campania_id))
                        .then(async function () {
                            renderHistory(historyNode, await fetchHistory());
                            document.dispatchEvent(new CustomEvent('campania:eliminada', {
                                detail: {
                                    campaniaId: item.campania_id
                                }
                            }));
                        })
                        .catch(function (error) {
                            window.alert(error.message || 'No fue posible eliminar la campania');
                            deleteButton.disabled = false;
                            deleteButton.classList.remove('is-loading');
                            if (labelNode) {
                                labelNode.textContent = 'Eliminar';
                            }
                        });
                    return;
                }

                const openButton = event.target.closest('[data-history-open-index]');
                const reimportButton = event.target.closest('[data-history-reimport-index]');
                if (!openButton && !reimportButton) {
                    return;
                }

                const items = await fetchHistory();
                const index = openButton
                    ? Number(openButton.getAttribute('data-history-open-index'))
                    : Number(reimportButton.getAttribute('data-history-reimport-index'));
                const item = items[index];
                if (!item) {
                    return;
                }

                fillForm(form, item);
                closeAllImportModals();

                if ((openButton || reimportButton) && item.campania_id) {
                    document.dispatchEvent(new CustomEvent('campania:importada', {
                        detail: {
                            campaniaId: item.campania_id,
                            nombre: item.nombre || item.sheet_tab || 'Campania telefonica',
                            totalRegistros: Number(item.cantidad_registros) || 0
                        }
                    }));
                }
            });
        }

        analyzeButton.addEventListener("click", async function () {
            try {
                const payload = serializeForm(form);
                const data = await postJSON(window.DPIACampaniaImportador.endpointAnalizar, payload);
                if (data.user) {
                    applyAuthenticatedUser(data.user);
                }
                setResult(resultNode, data);
            } catch (error) {
                setResult(resultNode, { ok: false, error: error.message });
            }
        });

        form.addEventListener("submit", async function (event) {
            event.preventDefault();
            setImportLoading(true);

            try {
                const payload = serializeForm(form);
                const data = await postJSON(window.DPIACampaniaImportador.endpointImportar, payload);
                if (data.user) {
                    applyAuthenticatedUser(data.user);
                }
                setResult(resultNode, data);
                document.dispatchEvent(new CustomEvent("campania:importada", {
                    detail: {
                        campaniaId: data.campania_id,
                        nombre: payload.nombre || payload.sheet_tab || "Campania telefonica",
                        sheetName: payload.sheet_name || payload.sheet_id || "",
                        sheetTab: payload.sheet_tab || "",
                        totalRegistros: data.total_registros || 0
                    }
                }));
                closeModal();
            } catch (error) {
                setResult(resultNode, { ok: false, error: error.message });
            } finally {
                setImportLoading(false);
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && historyModal && !historyModal.hidden) {
                closeHistoryModal();
                return;
            }
            if (event.key === "Escape" && !modal.hidden) {
                closeModal();
            }
        });
    });
})();