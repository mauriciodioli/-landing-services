(function() {
  'use strict';

  const MAX_SIZE_MB = 30;
  const ALLOWED_TYPES = ['image/', 'video/'];
  const SUFFIX = 'camara-rapida-publicacion';
  const RECORDING_CLASS = 'cphq-recording-camara-rapida-publicacion';
  const DIRECT_PUBLISH_TARGETS = {
    personal_privado: {
      ambitoSlug: 'personal',
      categoriaSlug: 'privado',
    },
    noticias_nuevos: {
      ambitoSlug: 'noticias',
      categoriaSlug: 'nuevos',
    },
  };

  function t(key, fallback, vars = {}) {
    const base = typeof window.getI18nText === 'function'
      ? window.getI18nText(key, fallback)
      : fallback;

    return Object.keys(vars).reduce((acc, token) => {
      return acc.replaceAll(`{${token}}`, String(vars[token]));
    }, base);
  }

  const modal = document.getElementById(`cphq-modal-${SUFFIX}`);
  if (!modal) {
    return;
  }

  const video = document.getElementById(`cphq-camera-${SUFFIX}`);
  const emptyState = document.getElementById(`cphq-empty-state-${SUFFIX}`);
  const status = document.getElementById(`cphq-status-${SUFFIX}`);
  const fileInput = document.getElementById(`cphq-file-input-${SUFFIX}`);
  const photoInput = document.getElementById(`cphq-photo-input-${SUFFIX}`);
  const videoInput = document.getElementById(`cphq-video-input-${SUFFIX}`);
  const footerActions = document.getElementById(`cphq-footer-actions-${SUFFIX}`);
  const directOptions = document.getElementById(`cphq-direct-options-${SUFFIX}`);
  const previewTray = document.getElementById(`cphq-preview-tray-${SUFFIX}`);
  const previewList = document.getElementById(`cphq-preview-list-${SUFFIX}`);
  const footerPreview = document.getElementById(`cphq-footer-preview-${SUFFIX}`);
  const footerPreviewList = document.getElementById(`cphq-footer-preview-list-${SUFFIX}`);
  const card = modal.querySelector('.cphq-card-camara-rapida-publicacion');
  const closeBtn = document.getElementById(`cphq-close-${SUFFIX}`);
  const cancelBtn = document.getElementById(`cphq-cancel-${SUFFIX}`);
  const takePhotoBtn = document.getElementById(`cphq-take-photo-${SUFFIX}`);
  const recordBtn = document.getElementById(`cphq-record-video-${SUFFIX}`);
  const flipCameraBtn = document.getElementById(`cphq-flip-camera-${SUFFIX}`);
  const uploadBtn = document.getElementById(`cphq-upload-file-${SUFFIX}`);
  const continueBtn = document.getElementById(`cphq-continue-${SUFFIX}`);
  const directPublishBtn = document.getElementById(`cphq-direct-publish-${SUFFIX}`);
  const directBackBtn = document.getElementById(`cphq-direct-back-${SUFFIX}`);
  const directCloseBtn = document.getElementById(`cphq-direct-close-${SUFFIX}`);
  const directConfirmBtn = document.getElementById(`cphq-direct-confirm-${SUFFIX}`);
  const directPhoneChoice = document.getElementById(`cphq-direct-phone-choice-${SUFFIX}`);
  const directPhoneCloseBtn = document.getElementById(`cphq-direct-phone-close-${SUFFIX}`);
  const directAddPhoneBtn = document.getElementById(`cphq-direct-add-phone-${SUFFIX}`);
  const directContinueWithoutPhoneBtn = document.getElementById(`cphq-direct-continue-without-phone-${SUFFIX}`);
  const directTargetButtons = Array.from(modal.querySelectorAll('.cphq-direct-option-camara-rapida-publicacion'));
  const recordLabel = recordBtn.querySelector('.cphq-tool-label-camara-rapida-publicacion');

  function applyAriaTranslations() {
    modal.querySelectorAll('[data-i18n-aria-label]').forEach((node) => {
      const key = node.getAttribute('data-i18n-aria-label');
      const translated = t(key, node.getAttribute('aria-label') || '');
      if (translated) {
        node.setAttribute('aria-label', translated);
      }
    });
  }

  const state = {
    files: [],
    stream: null,
    recorder: null,
    chunks: [],
    recording: false,
    publishing: false,
    preferNativeCapture: false,
    directPublishTarget: '',
    cameraFacingMode: 'environment',
  };

  function revokePreviewUrl(file) {
    if (file && file.__cphqPreviewUrl) {
      URL.revokeObjectURL(file.__cphqPreviewUrl);
      delete file.__cphqPreviewUrl;
    }
  }

  function getPreviewUrl(file) {
    if (!file.__cphqPreviewUrl) {
      file.__cphqPreviewUrl = URL.createObjectURL(file);
    }
    return file.__cphqPreviewUrl;
  }

  function getCurrentLanguage() {
    return (localStorage.getItem('language') || localStorage.getItem('idioma') || window.currentLang || 'es').toLowerCase();
  }

  function getStoredPhone() {
    const userId = localStorage.getItem('usuario_id') || localStorage.getItem('usuario_id_micrositio') || '';
    if (userId) {
      const byUserKey = localStorage.getItem(`numTelefono:${userId}`);
      if (byUserKey) {
        return byUserKey;
      }
    }

    for (let index = 0; index < localStorage.length; index += 1) {
      const key = localStorage.key(index);
      if (key && key.startsWith('numTelefono:')) {
        const value = localStorage.getItem(key);
        if (value) {
          return value;
        }
      }
    }

    return '';
  }

  function isPhoneValid(phone) {
    return /^\+[1-9]\d{7,14}$/.test((phone || '').trim());
  }

  function isAndroidEmbeddedAppLike() {
    if (typeof window.isAndroidEmbeddedApp === 'function') {
      try {
        return !!window.isAndroidEmbeddedApp();
      } catch (_) {}
    }

    const userAgent = navigator.userAgent || '';
    return /Android/i.test(userAgent) && (/wv/i.test(userAgent) || window.__DPIA_ANDROID_APP__ === true);
  }

  function isMobileDevice() {
    return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || '');
  }

  function isIosDevice() {
    const userAgent = navigator.userAgent || '';
    const platform = navigator.platform || '';

    return /iPad|iPhone|iPod/i.test(userAgent) || (platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  }

  function shouldPreferNativeCapture() {
    return isAndroidEmbeddedAppLike() || isIosDevice();
  }

  function updateStatus(message) {
    status.textContent = message;
  }

  function updateFlipCameraUi() {
    if (!flipCameraBtn) {
      return;
    }

    const nextMode = state.cameraFacingMode === 'environment' ? 'user' : 'environment';
    const isFront = nextMode === 'user';
    const label = isFront
      ? t('camara_rapida_publicacion_selfie', 'Selfie')
      : t('camara_rapida_publicacion_rear_camera', 'Trasera');
    const ariaLabel = isFront
      ? t('camara_rapida_publicacion_switch_to_front_camera', 'Cambiar a camara frontal')
      : t('camara_rapida_publicacion_switch_to_rear_camera', 'Cambiar a camara trasera');

    const labelNode = flipCameraBtn.querySelector('.cphq-tool-label-camara-rapida-publicacion');
    if (labelNode) {
      labelNode.textContent = label;
    }
    flipCameraBtn.setAttribute('aria-label', ariaLabel);
    flipCameraBtn.disabled = state.recording;
  }

  function syncNativeCaptureInputs() {
    const captureMode = state.cameraFacingMode === 'user' ? 'user' : 'environment';
    photoInput.setAttribute('capture', captureMode);
    videoInput.setAttribute('capture', captureMode);
  }

  function updateFlowState() {
    const hasFiles = state.files.length > 0;
    const showingDirectOptions = !directOptions.classList.contains('is-hidden');
    footerActions.classList.toggle('is-hidden', !hasFiles || showingDirectOptions);

    if (previewTray && previewList) {
      previewTray.classList.toggle('is-hidden', !hasFiles);
    }

    if (footerPreview && footerPreviewList) {
      footerPreview.classList.toggle('is-hidden', !hasFiles);
    }

    if (!hasFiles) {
      updateStatus(t('camara_rapida_publicacion_status_need_media', 'Toma una foto, graba un video o sube un archivo para continuar.'));
      return;
    }

    updateStatus(t('camara_rapida_publicacion_status_ready', 'Archivos listos. Ya puedes continuar o publicar directo.'));
  }

  function removeFileAt(index) {
    const file = state.files[index];
    if (!file) {
      return;
    }

    revokePreviewUrl(file);
    state.files.splice(index, 1);
    renderPreviewList();
    updateFlowState();
  }

  function buildPreviewItem(file, index) {
    const item = document.createElement('div');
    item.className = 'cphq-preview-item-camara-rapida-publicacion';

    const previewUrl = getPreviewUrl(file);
    const isVideo = file.type.startsWith('video/');
    const media = document.createElement(isVideo ? 'video' : 'img');
    media.className = 'cphq-preview-media-camara-rapida-publicacion';
    media.src = previewUrl;

    if (isVideo) {
      media.muted = true;
      media.loop = true;
      media.playsInline = true;
      media.autoplay = true;
      media.preload = 'metadata';
    } else {
      media.alt = file.name || 'Vista previa';
    }

    const badge = document.createElement('span');
    badge.className = 'cphq-preview-badge-camara-rapida-publicacion';
    badge.textContent = isVideo ? 'Video' : 'Foto';

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'cphq-preview-remove-camara-rapida-publicacion';
    removeBtn.setAttribute('aria-label', t('camara_rapida_publicacion_remove_file', 'Eliminar archivo'));
    removeBtn.textContent = '×';
    removeBtn.addEventListener('click', () => removeFileAt(index));

    const meta = document.createElement('div');
    meta.className = 'cphq-preview-meta-camara-rapida-publicacion';

    const name = document.createElement('span');
    name.className = 'cphq-preview-name-camara-rapida-publicacion';
    name.textContent = file.name || (isVideo ? 'video' : 'imagen');

    const kind = document.createElement('span');
    kind.className = 'cphq-preview-kind-camara-rapida-publicacion';
    kind.textContent = isVideo
      ? t('camara_rapida_publicacion_video', 'Video')
      : t('camara_rapida_publicacion_take_photo', 'Foto');

    meta.appendChild(name);
    meta.appendChild(kind);
    item.appendChild(media);
    item.appendChild(badge);
    item.appendChild(removeBtn);
    item.appendChild(meta);

    return item;
  }

  function renderPreviewList() {
    if (!previewList && !footerPreviewList) {
      return;
    }

    if (previewList) {
      previewList.innerHTML = '';
    }
    if (footerPreviewList) {
      footerPreviewList.innerHTML = '';
    }

    state.files.forEach((file, index) => {
      if (previewList) {
        previewList.appendChild(buildPreviewItem(file, index));
      }
      if (footerPreviewList) {
        footerPreviewList.appendChild(buildPreviewItem(file, index));
      }
    });
  }

  function setDirectTarget(target) {
    state.directPublishTarget = target;
    directTargetButtons.forEach((button) => {
      button.classList.toggle('is-selected', button.dataset.target === target);
    });
    directConfirmBtn.disabled = !target || state.publishing;
  }

  function showDirectOptions() {
    if (!state.files.length) {
      updateStatus(t('camara_rapida_publicacion_need_file_direct', 'Agrega al menos un archivo antes de publicar directo.'));
      return;
    }

    directOptions.classList.remove('is-hidden');
    if (card) {
      card.classList.add('is-direct-options-open-camara-rapida-publicacion');
    }
    hideDirectPhoneChoice();
    footerActions.classList.add('is-hidden');
    setDirectTarget('');
    updateStatus(t('camara_rapida_publicacion_direct_options_status', 'Selecciona el destino para la publicación directa.'));
  }

  function hideDirectOptions() {
    if (state.publishing) {
      return;
    }
    directOptions.classList.add('is-hidden');
    if (card) {
      card.classList.remove('is-direct-options-open-camara-rapida-publicacion');
    }
    hideDirectPhoneChoice();
    setDirectTarget('');
    updateFlowState();
  }

  function showDirectPhoneChoice() {
    if (directPhoneChoice) {
      directPhoneChoice.classList.remove('is-hidden');
    }
    updateStatus(t('camara_rapida_publicacion_direct_phone_optional', 'No encontramos un telefono valido. Puedes agregarlo ahora o continuar sin telefono.'));
  }

  function hideDirectPhoneChoice() {
    if (directPhoneChoice) {
      directPhoneChoice.classList.add('is-hidden');
    }
  }

  function setPublishingState(isPublishing) {
    state.publishing = isPublishing;
    directConfirmBtn.disabled = isPublishing || !state.directPublishTarget;
    directBackBtn.disabled = isPublishing;
    directTargetButtons.forEach((button) => {
      button.disabled = isPublishing;
    });
    if (directAddPhoneBtn) {
      directAddPhoneBtn.disabled = isPublishing;
    }
    if (directContinueWithoutPhoneBtn) {
      directContinueWithoutPhoneBtn.disabled = isPublishing;
    }
    if (directPhoneCloseBtn) {
      directPhoneCloseBtn.disabled = isPublishing;
    }
  }

  function buildDirectPublishPayload() {
    const targetConfig = DIRECT_PUBLISH_TARGETS[state.directPublishTarget];
    if (!targetConfig) {
      return null;
    }

    const language = getCurrentLanguage();
    return {
      idioma: language,
      title: t('camara_rapida_publicacion_direct_default_title', 'Nuevo'),
      description: '',
      text: '',
      telefono: getStoredPhone(),
      ambitoSlug: targetConfig.ambitoSlug,
      categoriaSlug: targetConfig.categoriaSlug,
      files: state.files.slice(),
    };
  }

  function openCreateModalForPhone() {
    if (!window.CPHCreateModal || typeof window.CPHCreateModal.preloadFiles !== 'function' || typeof window.CPHCreateModal.open !== 'function') {
      updateStatus(t('camara_rapida_publicacion_missing_publish_modal', 'El modal de publicación no está disponible todavía.'));
      return;
    }

    const filesToTransfer = state.files.slice();
    closeModal();
    window.CPHCreateModal.preloadFiles(filesToTransfer);
    window.CPHCreateModal.open();
    window.setTimeout(() => {
      const phoneInput = document.getElementById('cph-telefono');
      phoneInput?.focus();
    }, 150);
  }

  function setCameraVisible(visible) {
    video.classList.toggle('is-visible', visible);
    emptyState.style.display = visible ? 'none' : 'grid';
  }

  function stopRecordingIfNeeded() {
    if (state.recorder && state.recording) {
      state.recorder.stop();
    }
  }

  function stopCamera() {
    stopRecordingIfNeeded();
    if (state.stream) {
      state.stream.getTracks().forEach((track) => track.stop());
      state.stream = null;
    }
    video.srcObject = null;
    setCameraVisible(false);
  }

  async function startCamera() {
    syncNativeCaptureInputs();

    if (state.preferNativeCapture) {
      setCameraVisible(false);
      if (state.cameraFacingMode === 'user') {
        updateStatus(t('camara_rapida_publicacion_status_native_ready_front', 'Modo selfie listo. Usa foto o video para abrir la camara frontal del dispositivo.'));
      } else {
        updateStatus(t('camara_rapida_publicacion_status_native_ready', 'Usa foto, video o subir para abrir la cámara o galería del dispositivo.'));
      }
      updateFlipCameraUi();
      return;
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      updateStatus(t('camara_rapida_publicacion_camera_unavailable', 'La cámara no está disponible. Puedes subir archivos manualmente.'));
      setCameraVisible(false);
      return;
    }

    try {
      stopCamera();
      state.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: state.cameraFacingMode } },
        audio: false,
      });
      video.srcObject = state.stream;
      if (typeof video.play === 'function') {
        await video.play();
      }
      setCameraVisible(true);
      if (state.cameraFacingMode === 'user') {
        updateStatus(t('camara_rapida_publicacion_camera_ready_front', 'Camara frontal lista. Puedes tomar una selfie o grabar un video.'));
      } else {
        updateStatus(t('camara_rapida_publicacion_camera_ready', 'Cámara lista. Puedes tomar una foto o grabar un video.'));
      }
      updateFlipCameraUi();
    } catch (error) {
      console.error('[CPHQ] No se pudo iniciar la cámara', error);
      if (!state.preferNativeCapture && state.cameraFacingMode === 'user') {
        try {
          state.cameraFacingMode = 'environment';
          await startCamera();
          updateStatus(t('camara_rapida_publicacion_camera_fallback_rear', 'La camara frontal no estuvo disponible. Se activo la trasera.'));
          return;
        } catch (_) {}
      }

      updateStatus(t('camara_rapida_publicacion_camera_denied', 'No se pudo acceder a la cámara. Continúa con subida manual.'));
      setCameraVisible(false);
      updateFlipCameraUi();
    }
  }

  async function toggleCameraFacingMode() {
    if (state.recording) {
      return;
    }

    state.cameraFacingMode = state.cameraFacingMode === 'environment' ? 'user' : 'environment';
    updateFlipCameraUi();
    await startCamera();
  }

  function validateFile(file) {
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      updateStatus(t('camara_rapida_publicacion_file_too_large', 'Archivo "{name}" demasiado pesado (máx {max}MB)', {
        name: file.name,
        max: MAX_SIZE_MB,
      }));
      return false;
    }
    if (!ALLOWED_TYPES.some((type) => file.type.startsWith(type))) {
      updateStatus(t('camara_rapida_publicacion_unsupported_type', 'Tipo no soportado: {name}', {
        name: file.name,
      }));
      return false;
    }
    return true;
  }

  function addFiles(files) {
    Array.from(files).forEach((file) => {
      if (validateFile(file)) {
        state.files.push(file);
      }
    });
    renderPreviewList();
    updateFlowState();
  }

  function makeTimestampedFile(blob, typePrefix, extension) {
    const stamp = Date.now();
    const mimeType = blob.type || `${typePrefix}/${extension}`;
    return new File([blob], `${typePrefix}-${stamp}.${extension}`, {
      type: mimeType,
      lastModified: Date.now(),
    });
  }

  function takePhoto() {
    if (state.preferNativeCapture) {
      photoInput.click();
      return;
    }

    if (!state.stream || !video.videoWidth || !video.videoHeight) {
      updateStatus(t('camara_rapida_publicacion_camera_not_ready', 'La cámara todavía no está lista.'));
      return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (!blob) {
        updateStatus(t('camara_rapida_publicacion_capture_failed', 'No se pudo capturar la foto.'));
        return;
      }
      addFiles([makeTimestampedFile(blob, 'captura', 'jpg')]);
      updateStatus(t('camara_rapida_publicacion_photo_added', 'Foto agregada. Puedes tomar otra o continuar.'));
    }, 'image/jpeg', 0.92);
  }

  function stopRecorderAndFinalize() {
    if (!state.recorder || !state.recording) {
      return;
    }
    state.recorder.stop();
  }

  function toggleRecording() {
    if (state.preferNativeCapture) {
      videoInput.click();
      return;
    }

    if (!state.stream) {
      updateStatus(t('camara_rapida_publicacion_need_camera_record', 'Necesitas la cámara activa para grabar.'));
      return;
    }
    if (!window.MediaRecorder) {
      updateStatus(t('camara_rapida_publicacion_record_unavailable', 'La grabación no está disponible aquí. Usa subida manual.'));
      return;
    }

    if (state.recording) {
      stopRecorderAndFinalize();
      return;
    }

    try {
      state.chunks = [];
      state.recorder = new MediaRecorder(state.stream, { mimeType: 'video/webm' });
      state.recorder.ondataavailable = (event) => {
        if (event.data && event.data.size) {
          state.chunks.push(event.data);
        }
      };
      state.recorder.onstop = () => {
        const blob = new Blob(state.chunks, { type: 'video/webm' });
        state.recording = false;
        recordBtn.classList.remove('is-recording');
        if (recordLabel) recordLabel.textContent = t('camara_rapida_publicacion_video', 'Video');
        recordBtn.setAttribute('aria-label', t('camara_rapida_publicacion_video', 'Grabar video'));
        modal.classList.remove(RECORDING_CLASS);
        if (blob.size) {
          addFiles([makeTimestampedFile(blob, 'grabacion', 'webm')]);
          updateStatus(t('camara_rapida_publicacion_video_added', 'Video agregado. Puedes grabar otro o continuar.'));
        }
      };
      state.recorder.start();
      state.recording = true;
      recordBtn.classList.add('is-recording');
      if (recordLabel) recordLabel.textContent = t('camara_rapida_publicacion_stop', 'Stop');
      recordBtn.setAttribute('aria-label', t('camara_rapida_publicacion_stop', 'Detener grabación'));
      modal.classList.add(RECORDING_CLASS);
      updateStatus(t('camara_rapida_publicacion_recording', 'Grabando video... pulsa de nuevo para detener.'));
    } catch (error) {
      console.error('[CPHQ] Error al grabar video', error);
      updateStatus(t('camara_rapida_publicacion_record_start_failed', 'No se pudo iniciar la grabación. Usa subida manual.'));
    }
  }

  function resetModalState() {
    stopCamera();
    state.files.forEach(revokePreviewUrl);
    state.files = [];
    state.recorder = null;
    state.chunks = [];
    state.recording = false;
    state.publishing = false;
    state.cameraFacingMode = 'environment';
    fileInput.value = '';
    photoInput.value = '';
    videoInput.value = '';
    recordBtn.classList.remove('is-recording');
    if (recordLabel) recordLabel.textContent = t('camara_rapida_publicacion_video', 'Video');
    recordBtn.setAttribute('aria-label', t('camara_rapida_publicacion_video', 'Grabar video'));
    modal.classList.remove(RECORDING_CLASS);
    footerActions.classList.add('is-hidden');
    directOptions.classList.add('is-hidden');
    hideDirectPhoneChoice();
    if (card) {
      card.classList.remove('is-direct-options-open-camara-rapida-publicacion');
    }
    setPublishingState(false);
    directConfirmBtn.disabled = true;
    state.directPublishTarget = '';
    if (previewList) {
      previewList.innerHTML = '';
    }
    if (footerPreviewList) {
      footerPreviewList.innerHTML = '';
    }
    if (previewTray) {
      previewTray.classList.add('is-hidden');
    }
    if (footerPreview) {
      footerPreview.classList.add('is-hidden');
    }
    updateStatus(t('camara_rapida_publicacion_status_preparing', 'Preparando cámara...'));
    updateFlipCameraUi();
  }

  function openModal() {
    state.preferNativeCapture = shouldPreferNativeCapture();
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    modal.classList.toggle('is-native-capture-camara-rapida-publicacion', state.preferNativeCapture);
    updateFlowState();
    const lang = localStorage.getItem('language') || window.currentLang || 'es';
    if (typeof window.refreshI18n === 'function') {
      window.refreshI18n(lang);
    }
    applyAriaTranslations();
    if (recordLabel) recordLabel.textContent = t('camara_rapida_publicacion_video', 'Video');
    updateFlipCameraUi();
    startCamera();
  }

  function closeModal() {
    resetModalState();
    modal.classList.remove('is-open');
    modal.classList.remove('is-native-capture-camara-rapida-publicacion');
    modal.setAttribute('aria-hidden', 'true');
  }

  function continueToContextualModal() {
    if (!state.files.length) {
      updateStatus(t('camara_rapida_publicacion_need_file_continue', 'Agrega al menos una foto o video para continuar.'));
      return;
    }
    if (!window.CPHCreateModal || typeof window.CPHCreateModal.preloadFiles !== 'function') {
      updateStatus(t('camara_rapida_publicacion_missing_publish_modal', 'El modal de publicación no está disponible todavía.'));
      return;
    }

    const filesToTransfer = state.files.slice();
    closeModal();
    window.CPHCreateModal.preloadFiles(filesToTransfer);
    window.CPHCreateModal.open();
  }

  async function directPublishStub() {
    if (!state.directPublishTarget) {
      updateStatus(t('camara_rapida_publicacion_direct_options_status', 'Selecciona el destino para la publicación directa.'));
      return;
    }

    if (!state.files.length) {
      updateStatus(t('camara_rapida_publicacion_need_file_direct', 'Agrega al menos un archivo antes de publicar directo.'));
      return;
    }

    if (!window.CPHCreateModal || typeof window.CPHCreateModal.directPublish !== 'function') {
      updateStatus(t('camara_rapida_publicacion_direct_missing_handler', 'La publicación directa no está disponible todavía.'));
      return;
    }

    const payload = buildDirectPublishPayload();
    if (!payload) {
      updateStatus(t('camara_rapida_publicacion_direct_options_status', 'Selecciona el destino para la publicación directa.'));
      return;
    }

    if (!isPhoneValid(payload.telefono)) {
      showDirectPhoneChoice();
      return;
    }

    try {
      setPublishingState(true);
      updateStatus(t('camara_rapida_publicacion_direct_publishing', 'Publicando directamente...'));
      await window.CPHCreateModal.directPublish(payload);
      closeModal();
    } catch (error) {
      console.error('[CPHQ] Error en publicación directa', error);
      const message = error && error.message
        ? t('camara_rapida_publicacion_direct_error_with_reason', 'No se pudo publicar directo: {reason}', { reason: error.message })
        : t('camara_rapida_publicacion_direct_error', 'No se pudo publicar directo.');
      updateStatus(message);
    } finally {
      setPublishingState(false);
    }
  }

  closeBtn.addEventListener('click', closeModal);
  cancelBtn.addEventListener('click', closeModal);
  modal.addEventListener('click', (event) => {
    if (event.target === modal) {
      closeModal();
    }
  });
  directPhoneChoice?.addEventListener('click', (event) => {
    if (event.target === directPhoneChoice && !state.publishing) {
      hideDirectPhoneChoice();
    }
  });
  takePhotoBtn.addEventListener('click', takePhoto);
  recordBtn.addEventListener('click', toggleRecording);
  flipCameraBtn?.addEventListener('click', () => {
    toggleCameraFacingMode().catch((error) => {
      console.error('[CPHQ] No se pudo cambiar la cámara', error);
      updateStatus(t('camara_rapida_publicacion_switch_camera_failed', 'No se pudo cambiar la camara.'));
    });
  });
  uploadBtn.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (event) => addFiles(event.target.files));
  photoInput.addEventListener('change', (event) => addFiles(event.target.files));
  videoInput.addEventListener('change', (event) => addFiles(event.target.files));
  continueBtn.addEventListener('click', continueToContextualModal);
  directPublishBtn.addEventListener('click', showDirectOptions);
  directBackBtn.addEventListener('click', hideDirectOptions);
  if (directCloseBtn) {
    directCloseBtn.addEventListener('click', hideDirectOptions);
  }
  if (directPhoneCloseBtn) {
    directPhoneCloseBtn.addEventListener('click', hideDirectPhoneChoice);
  }
  directAddPhoneBtn?.addEventListener('click', openCreateModalForPhone);
  directContinueWithoutPhoneBtn?.addEventListener('click', async () => {
    const payload = buildDirectPublishPayload();
    if (!payload) {
      return;
    }

    payload.telefono = '';
    hideDirectPhoneChoice();

    try {
      setPublishingState(true);
      updateStatus(t('camara_rapida_publicacion_direct_publishing', 'Publicando directamente...'));
      await window.CPHCreateModal.directPublish(payload);
      closeModal();
    } catch (error) {
      console.error('[CPHQ] Error en publicación directa', error);
      const message = error && error.message
        ? t('camara_rapida_publicacion_direct_error_with_reason', 'No se pudo publicar directo: {reason}', { reason: error.message })
        : t('camara_rapida_publicacion_direct_error', 'No se pudo publicar directo.');
      updateStatus(message);
    } finally {
      setPublishingState(false);
    }
  });
  directConfirmBtn.addEventListener('click', directPublishStub);
  directTargetButtons.forEach((button) => {
    button.addEventListener('click', () => setDirectTarget(button.dataset.target || ''));
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && modal.classList.contains('is-open')) {
      if (directPhoneChoice && !directPhoneChoice.classList.contains('is-hidden')) {
        hideDirectPhoneChoice();
        return;
      }
      closeModal();
    }
  });

  updateFlowState();
  applyAriaTranslations();
  window.CPHQuickCaptureModal = {
    open: openModal,
    close: closeModal,
  };
})();
