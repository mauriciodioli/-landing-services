import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from unidecode import unidecode

from controllers.conexionesSheet.datosSheet import autenticar_y_abrir_sheet
from extensions import db
from models.campania_contacto import CampaniaContacto
from models.campania_telefonica import CampaniaEstado, CampaniaTelefonica
from models.contacto_telefonico import ContactoTelefonico
from models.historial_contacto import HistorialContacto


PHONE_HEADERS = {
    "telefono",
    "telefono1",
    "telefono2",
    "telefono3",
    "telefonocontacto",
    "telefonoprincipal",
    "tel",
    "telf",
    "tlf",
    "mobile",
    "movil",
    "celular",
    "cell",
    "cellphone",
    "phone",
    "phone1",
    "phone2",
    "contactnumber",
    "numerotelefono",
    "whatsapp",
    "whatsappnumber",
    "telefone",
    "telemovel",
    "telemobile",
    "numero",
    "numerochiamata",
    "cellulare",
}

BUSINESS_HEADERS = {
    "negocio",
    "empresa",
    "company",
    "business",
    "razonsocial",
    "nombrecomercial",
    "local",
    "cliente",
    "organizacion",
    "organization",
    "brand",
    "azienda",
    "impresa",
    "negozio",
    "empresa_nome",
    "companhia",
}

CITY_HEADERS = {
    "ciudad",
    "poblacion",
    "localidad",
    "municipio",
    "city",
    "town",
    "village",
    "provincecity",
    "cidade",
    "comune",
    "citta",
    "freguesia",
}

EMAIL_HEADERS = {
    "email",
    "correo",
    "correoelectronico",
    "mail",
    "e-mail",
    "emailaddress",
    "contactemail",
    "correio",
    "correoeletronico",
    "postaelettronica",
    "mailcontatto",
}

WEB_HEADERS = {
    "web",
    "website",
    "sitio",
    "sitoweb",
    "paginaweb",
    "url",
    "link",
    "homepage",
    "domain",
    "sito",
    "sitoweb",
    "pagina",
    "paginaonline",
    "site",
}

ADDRESS_HEADERS = {
    "direccion",
    "domicilio",
    "address",
    "street",
    "calle",
    "ubicacion",
    "location",
}

POSTAL_CODE_HEADERS = {
    "cp",
    "codigopostal",
    "postalcode",
    "zipcode",
    "zip",
}

WHATSAPP_HEADERS = {
    "whatsapp",
    "whatsappnumber",
    "wa",
}


HEADER_EQUIVALENCES = {
    "telefono": PHONE_HEADERS,
    "negocio": BUSINESS_HEADERS,
    "ciudad": CITY_HEADERS,
    "email": EMAIL_HEADERS,
    "web": WEB_HEADERS,
    "direccion": ADDRESS_HEADERS,
    "codigo_postal": POSTAL_CODE_HEADERS,
    "whatsapp": WHATSAPP_HEADERS,
}


class ImportadorSheetService:
    def __init__(self, header_equivalences: Optional[Dict[str, Iterable[str]]] = None):
        equivalences = header_equivalences or HEADER_EQUIVALENCES
        self.header_equivalences = {
            canonical: {self.normalizar_texto(alias) for alias in aliases}
            for canonical, aliases in equivalences.items()
        }
        self.alias_to_canonical = self._build_alias_index(self.header_equivalences)

    @staticmethod
    def normalizar_texto(value: Any) -> str:
        if value is None:
            return ""

        normalized = unidecode(str(value)).lower().strip()
        normalized = re.sub(r"[^a-z0-9]+", "", normalized)
        return normalized

    def detectar_equivalencia(self, header: Any) -> Optional[str]:
        normalized_header = self.normalizar_texto(header)
        if not normalized_header:
            return None
        return self.alias_to_canonical.get(normalized_header)

    def analizar_headers(self, headers: Iterable[Any]) -> Dict[str, Any]:
        headers_list = list(headers)
        mapping: Dict[str, Optional[str]] = {}
        canonical_headers: Dict[str, str] = {}
        unknown_headers: List[str] = []

        for header in headers_list:
            canonical = self.detectar_equivalencia(header)
            header_name = "" if header is None else str(header)
            mapping[header_name] = canonical
            if canonical and canonical not in canonical_headers:
                canonical_headers[canonical] = header_name
            if canonical is None and header_name:
                unknown_headers.append(header_name)

        return {
            "headers_originales": headers_list,
            "headers_normalizados": {
                "" if header is None else str(header): self.normalizar_texto(header)
                for header in headers_list
            },
            "equivalencias_detectadas": mapping,
            "columnas_canonicas": canonical_headers,
            "columnas_desconocidas": unknown_headers,
        }

    def normalizar_fila(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized_row: Dict[str, Any] = {}

        for header, value in row_data.items():
            canonical = self.detectar_equivalencia(header)
            if canonical and canonical not in normalized_row:
                normalized_row[canonical] = value

        return normalized_row

    def preparar_registro(self, row_data: Dict[str, Any], row_number: Optional[int] = None) -> Dict[str, Any]:
        normalized_row = self.normalizar_fila(row_data)

        return {
            "row_number": row_number,
            "telefono": normalized_row.get("telefono"),
            "telefono_normalizado": self.normalizar_telefono(normalized_row.get("telefono")),
            "empresa": normalized_row.get("negocio"),
            "email": normalized_row.get("email"),
            "ciudad": normalized_row.get("ciudad"),
            "web": normalized_row.get("web"),
            "estado": CampaniaEstado.NUEVO.value,
            "json_data": row_data,
            "datos_normalizados": normalized_row,
        }

    @staticmethod
    def normalizar_telefono(value: Any) -> str:
        if value is None:
            return ""

        normalized = re.sub(r"[^0-9]+", "", str(value))
        return normalized

    @staticmethod
    def normalizar_telefono_discado(value: Any, default_country_code: str = "34") -> str:
        normalized = ImportadorSheetService.normalizar_telefono(value)
        if not normalized:
            return ""

        if normalized.startswith("00"):
            normalized = normalized[2:]

        if normalized.startswith(default_country_code):
            return normalized

        if len(normalized) == 9:
            return f"{default_country_code}{normalized}"

        return normalized

    @classmethod
    def construir_sip_uri(cls, value: Any) -> str:
        dial_number = cls.normalizar_telefono_discado(value)
        return f"sip:+{dial_number}" if dial_number else ""

    @classmethod
    def construir_whatsapp_uri(cls, value: Any) -> str:
        dial_number = cls.normalizar_telefono_discado(value)
        return f"https://wa.me/{dial_number}" if dial_number else ""

    @classmethod
    def construir_sms_uri(cls, value: Any) -> str:
        dial_number = cls.normalizar_telefono_discado(value)
        return f"sms:+{dial_number}" if dial_number else ""

    def identificar_columnas_clave(self, headers: Iterable[Any]) -> Dict[str, Optional[str]]:
        analysis = self.analizar_headers(headers)
        return {
            "telefono": analysis["columnas_canonicas"].get("telefono"),
            "negocio": analysis["columnas_canonicas"].get("negocio"),
            "email": analysis["columnas_canonicas"].get("email"),
            "ciudad": analysis["columnas_canonicas"].get("ciudad"),
            "web": analysis["columnas_canonicas"].get("web"),
        }

    def leer_sheet(self, sheet_id: str, sheet_tab: str, credentials_path: Optional[str] = None):
        del credentials_path

        sheet = autenticar_y_abrir_sheet(sheet_id, sheet_tab)
        if sheet is None:
            raise RuntimeError(
                "No fue posible abrir la hoja solicitada con la cuenta compartida "
                "cuenta-sheet-python@pruebasheetpython.iam.gserviceaccount.com"
            )

        return sheet

    def importar_desde_sheet(
        self,
        *,
        sheet_id: str,
        sheet_name: str,
        sheet_tab: str,
        nombre_campania: str,
        usuario_creador_id: Optional[int] = None,
        cantidad_registros: Optional[int] = None,
        credentials_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        session = db.session

        try:
            sheet = self.leer_sheet(sheet_id, sheet_tab, credentials_path)
            headers = sheet.row_values(1)
            rows = sheet.get_all_values()[1:]

            if cantidad_registros:
                rows = rows[:cantidad_registros]

            campaign = CampaniaTelefonica(
                usuario_creador_id=usuario_creador_id,
                nombre=nombre_campania,
                sheet_id=sheet_id,
                sheet_name=sheet_name,
                sheet_tab=sheet_tab,
                estado=CampaniaEstado.NUEVO.value,
                total_registros=0,
            )
            session.add(campaign)
            session.flush()

            imported_count = 0
            reused_count = 0
            skipped_count = 0

            for row_index, row in enumerate(rows, start=2):
                row_data = dict(zip(headers, row))
                prepared_row = self.preparar_registro(row_data, row_number=row_index)
                normalized_phone = prepared_row["telefono_normalizado"]

                if not normalized_phone:
                    skipped_count += 1
                    continue

                contact = (
                    session.query(ContactoTelefonico)
                    .filter(ContactoTelefonico.telefono_normalizado == normalized_phone)
                    .first()
                )

                if contact is None:
                    contact = ContactoTelefonico(
                        telefono_normalizado=normalized_phone,
                        telefono_original=prepared_row.get("telefono"),
                        empresa=prepared_row.get("empresa"),
                        ciudad=prepared_row.get("ciudad"),
                        email=prepared_row.get("email"),
                        web=prepared_row.get("web"),
                        json_data=prepared_row["json_data"],
                        estado_global=CampaniaEstado.NUEVO.value,
                    )
                    session.add(contact)
                    session.flush()
                    imported_count += 1
                else:
                    reused_count += 1

                existing_relation = (
                    session.query(CampaniaContacto)
                    .filter(
                        CampaniaContacto.campania_id == campaign.id,
                        CampaniaContacto.contacto_id == contact.id,
                    )
                    .first()
                )
                if existing_relation:
                    continue

                campaign_contact = CampaniaContacto(
                    campania_id=campaign.id,
                    contacto_id=contact.id,
                    usuario_asignado_id=usuario_creador_id,
                    estado=CampaniaEstado.NUEVO.value,
                    cantidad_intentos=0,
                    fecha_ultimo_contacto=None,
                    observacion=None,
                    eliminado=False,
                    exitoso=False,
                )
                session.add(campaign_contact)
                session.flush()

                history = HistorialContacto(
                    campania_contacto_id=campaign_contact.id,
                    usuario_id=usuario_creador_id,
                    accion="IMPORTADO",
                    estado_anterior=None,
                    estado_nuevo=CampaniaEstado.NUEVO.value,
                    nota=f"Registro importado desde fila {row_index}",
                    fecha=datetime.utcnow(),
                )
                session.add(history)

            campaign.total_registros = (
                session.query(CampaniaContacto)
                .filter(CampaniaContacto.campania_id == campaign.id)
                .count()
            )

            session.commit()

            return {
                "campania_id": campaign.id,
                "total_registros": campaign.total_registros,
                "contactos_nuevos": imported_count,
                "contactos_reutilizados": reused_count,
                "registros_descartados": skipped_count,
                "analisis_headers": self.analizar_headers(headers),
            }
        except Exception:
            session.rollback()
            raise
        finally:
            try:
                db.session.close()
            except Exception:
                pass
            try:
                db.session.remove()
            except Exception:
                pass

    def analizar_sheet(
        self,
        *,
        sheet_id: str,
        sheet_tab: str,
        cantidad_registros: Optional[int] = None,
        credentials_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        sheet = self.leer_sheet(sheet_id, sheet_tab, credentials_path)
        headers = sheet.row_values(1)
        rows = sheet.get_all_values()[1:]
        if cantidad_registros:
            rows = rows[:cantidad_registros]

        preview = []
        for row_index, row in enumerate(rows, start=2):
            row_data = dict(zip(headers, row))
            preview.append(self.preparar_registro(row_data, row_number=row_index))

        return {
            "headers": self.analizar_headers(headers),
            "columnas_clave": self.identificar_columnas_clave(headers),
            "preview": preview,
            "total_preview": len(preview),
        }

    def actualizar_estado_campania_contacto(
        self,
        *,
        campania_contacto_id: int,
        estado_nuevo: Optional[str] = None,
        usuario_id: Optional[int] = None,
        nota: Optional[str] = None,
    ) -> CampaniaContacto:
        session = db.session

        try:
            relation = session.get(CampaniaContacto, campania_contacto_id)
            if relation is None:
                raise ValueError("La relación de campaña no existe")

            estado_anterior = relation.estado
            nota_anterior = relation.observacion
            estado_cambia = estado_nuevo is not None and estado_nuevo != relation.estado
            nota_cambia = nota is not None and nota != relation.observacion

            if not estado_cambia and not nota_cambia:
                session.refresh(relation)
                return relation

            if estado_cambia:
                relation.estado = estado_nuevo
                relation.fecha_ultimo_contacto = datetime.utcnow()
                relation.cantidad_intentos = (relation.cantidad_intentos or 0) + 1
                relation.exitoso = estado_nuevo == CampaniaEstado.EXITOSO.value
                relation.eliminado = estado_nuevo == CampaniaEstado.ELIMINADO.value

            if nota is not None:
                relation.observacion = nota

            history = HistorialContacto(
                campania_contacto_id=relation.id,
                usuario_id=usuario_id,
                accion="ACTUALIZACION_ESTADO" if estado_cambia else "ACTUALIZACION_NOTA",
                estado_anterior=estado_anterior if estado_cambia else relation.estado,
                estado_nuevo=relation.estado,
                nota=relation.observacion if nota is not None else nota_anterior,
                fecha=datetime.utcnow(),
            )
            session.add(history)
            session.commit()
            session.refresh(relation)
            return relation
        except Exception:
            session.rollback()
            raise
        finally:
            try:
                db.session.close()
            except Exception:
                pass
            try:
                db.session.remove()
            except Exception:
                pass

    @staticmethod
    def _build_alias_index(
        header_equivalences: Dict[str, Iterable[str]]
    ) -> Dict[str, str]:
        alias_to_canonical: Dict[str, str] = {}

        for canonical, aliases in header_equivalences.items():
            normalized_canonical = ImportadorSheetService.normalizar_texto(canonical)
            alias_to_canonical[normalized_canonical] = canonical
            for alias in aliases:
                normalized_alias = ImportadorSheetService.normalizar_texto(alias)
                if normalized_alias:
                    alias_to_canonical[normalized_alias] = canonical

        return alias_to_canonical