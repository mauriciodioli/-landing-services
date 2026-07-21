import json

import gspread
from oauth2client.service_account import ServiceAccountCredentials

class GoogleSheetManager:
    def __init__(self, credentials_path):
        self.credentials_path = credentials_path
        self.client = None  # El cliente se inicializará al autenticar

    def get_service_account_email(self):
        try:
            with open(self.credentials_path, 'r', encoding='utf-8') as fh:
                payload = json.load(fh)
            return payload.get('client_email')
        except Exception:
            return None

    def autenticar(self):
        try:
            scope = ['https://spreadsheets.google.com/feeds', 
                     'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_path, scope)
            self.client = gspread.authorize(creds)
            return True
        except Exception as e:
            print(f"Ocurrió un error al autenticar: {e}")
            return False

    def abrir_sheet(self, sheetId, sheet_name):
        if not self.client:
            raise RuntimeError("El cliente no esta autenticado. Debes autenticar primero.")

        try:
            sheet = self.client.open_by_key(sheetId).worksheet(sheet_name)
            return sheet
        except gspread.exceptions.SpreadsheetNotFound as e:
            service_email = self.get_service_account_email()
            if service_email:
                raise RuntimeError(
                    f"La cuenta de servicio {service_email} no tiene acceso a la sheet {sheetId}. "
                    "Comparte la Google Sheet con ese correo y vuelve a intentar."
                ) from e
            raise RuntimeError(
                f"La cuenta de servicio no tiene acceso a la sheet {sheetId}. "
                "Comparte la Google Sheet con la cuenta usada por el backend y vuelve a intentar."
            ) from e
        except gspread.exceptions.WorksheetNotFound as e:
            raise RuntimeError(
                f"La pestana '{sheet_name}' no existe dentro de la sheet {sheetId}."
            ) from e
        except gspread.exceptions.APIError as e:
            service_email = self.get_service_account_email()
            message = getattr(e, 'response', None)
            status_code = getattr(message, 'status_code', None)
            if status_code == 403:
                if service_email:
                    raise RuntimeError(
                        f"Google Sheets rechazo el acceso. Comparte la sheet {sheetId} con {service_email}."
                    ) from e
                raise RuntimeError(
                    f"Google Sheets rechazo el acceso a la sheet {sheetId}. Revisa permisos de la cuenta de servicio."
                ) from e
            raise RuntimeError(f"No fue posible abrir la hoja en Google Sheets: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Ocurrio un error al abrir la hoja: {e}") from e
