import re
from typing import Any, Dict

from flask import current_app

from config import SIP_CALLER_ID, SIP_PASSWORD, SIP_PROVIDER, SIP_SERVER, SIP_USER


class SipService:
    REQUIRED_ENV_VARS = {
        'provider': 'SIP_PROVIDER',
        'server': 'SIP_SERVER',
        'user': 'SIP_USER',
        'password': 'SIP_PASSWORD',
        'caller_id': 'SIP_CALLER_ID',
    }

    @classmethod
    def get_sip_config(cls) -> Dict[str, str]:
        cls._validar_configuracion()
        return {
            'provider': SIP_PROVIDER,
            'server': SIP_SERVER,
            'user': SIP_USER,
            'caller_id': SIP_CALLER_ID,
        }

    @classmethod
    def get_provider_label(cls) -> str:
        provider = (SIP_PROVIDER or '').strip().lower()
        provider_labels = {
            'zadarma': 'Zadarma',
            'voipms': 'VoIP.ms',
            'voip.ms': 'VoIP.ms',
            'telnyx': 'Telnyx',
            'twilio': 'Twilio',
        }
        return provider_labels.get(provider, SIP_PROVIDER or 'Proveedor SIP')

    @staticmethod
    def normalizar_telefono(numero: Any) -> str:
        if numero is None:
            raise ValueError('El telefono es obligatorio')

        normalized = re.sub(r'[^0-9+]+', '', str(numero).strip())
        if not normalized:
            raise ValueError('El telefono es obligatorio')

        if normalized.count('+') > 1 or ('+' in normalized and not normalized.startswith('+')):
            raise ValueError('El telefono no tiene formato internacional valido')

        if normalized.startswith('00'):
            normalized = f'+{normalized[2:]}'

        if not normalized.startswith('+'):
            digits_only = re.sub(r'[^0-9]+', '', normalized)
            if len(digits_only) == 9:
                normalized = f'+34{digits_only}'
            elif len(digits_only) > 9:
                normalized = f'+{digits_only}'
            else:
                raise ValueError('El telefono no tiene formato internacional valido')

        digits_only = re.sub(r'[^0-9]+', '', normalized)
        if len(digits_only) < 10:
            raise ValueError('El telefono no tiene formato internacional valido')

        return f'+{digits_only}'

    @classmethod
    def generar_sip_link(cls, numero: Any) -> str:
        telefono = cls.normalizar_telefono(numero)
        current_app.logger.info('SIP link generado para %s', telefono)
        return f'sip:{telefono}'

    @classmethod
    def registrar_log_llamada(cls, *, telefono: str, usuario_id: Any = None, campania_id: Any = None) -> None:
        current_app.logger.info(
            'SIP click-to-call generado telefono=%s usuario_id=%s campania_id=%s caller_id=%s proveedor=%s',
            telefono,
            usuario_id,
            campania_id,
            SIP_CALLER_ID,
            SIP_PROVIDER,
        )

    @classmethod
    def registrar_log_error(cls, *, telefono: Any, error: Exception, usuario_id: Any = None, campania_id: Any = None) -> None:
        current_app.logger.error(
            'Error generando SIP telefono=%s usuario_id=%s campania_id=%s error=%s',
            telefono,
            usuario_id,
            campania_id,
            error,
        )

    @classmethod
    def _validar_configuracion(cls) -> None:
        config_values = {
            'provider': SIP_PROVIDER,
            'server': SIP_SERVER,
            'user': SIP_USER,
            'password': SIP_PASSWORD,
            'caller_id': SIP_CALLER_ID,
        }

        missing = [cls.REQUIRED_ENV_VARS[key] for key, value in config_values.items() if not value]
        if missing:
            raise RuntimeError(f'Faltan variables SIP requeridas: {", ".join(missing)}')