"""Administration of web enquiries, separate from course participants."""
import uuid
from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from models.web_lead import Lead
from services.web_landing.lead_service import validate, InvalidLead
from services.web_landing.content import CONTENT
from utils.db_session import get_db_session
from utils.admin_access import require_admin_roles

web_leads_admin = Blueprint('web_leads_admin', __name__)
restricted = require_admin_roles('administrador', 'moderador')

def serialize(lead):
    result = {column.name: getattr(lead, column.name) for column in Lead.__table__.columns}
    result['created_at'] = lead.created_at.isoformat()+'Z' if lead.created_at else None
    return result

@web_leads_admin.after_request
def private_headers(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return response

@web_leads_admin.get('/admin')
def hub():
    return render_template('admin/index.html')

@web_leads_admin.get('/admin/solicitudes-web')
def page():
    return render_template('admin/web_leads.html', c=CONTENT['es'])

@web_leads_admin.get('/admin/api/access')
@require_admin_roles('administrador', 'moderador', 'avanzado')
def access():
    from flask import g
    return jsonify(ok=True, permissions={'web_leads': str(g.admin_user.get('roll', '')).strip().lower() in {'administrador', 'moderador'}})

@web_leads_admin.get('/admin/api/web-leads')
@restricted
def listing():
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(100, max(1, int(request.args.get('per_page', 25))))
    except (ValueError, TypeError):
        return jsonify(error='Paginación inválida'), 400
    q = request.args.get('q', '').strip()[:200]
    business = request.args.get('business', '')
    solution = request.args.get('solution', '')
    with get_db_session() as session:
        query = session.query(Lead)
        if q:
            query = query.filter(or_(*(column.contains(q, autoescape=True) for column in (Lead.name, Lead.email, Lead.description, Lead.features, Lead.integration_details))))
        if business: query = query.filter(Lead.business_type == business)
        if solution: query = query.filter(Lead.solution_type == solution)
        total = query.count()
        rows = query.order_by(Lead.created_at.desc(), Lead.id.desc()).offset((page-1)*per_page).limit(per_page).all()
        result = [serialize(row) for row in rows]
    return jsonify(items=result, total=total, page=page, per_page=per_page)

@web_leads_admin.get('/admin/api/web-leads/<lead_id>')
@restricted
def detail(lead_id):
    with get_db_session() as session:
        lead = session.get(Lead, lead_id)
        if not lead: return jsonify(error='Solicitud no encontrada'), 404
        result = serialize(lead)
    return jsonify(item=result)

def payload():
    if request.content_length is not None and request.content_length > 32768:
        return None, (jsonify(error='Solicitud demasiado grande'), 413)
    data = request.get_json(silent=True)
    if not isinstance(data, dict): return None, (jsonify(error='Datos inválidos'), 400)
    return data, None

@web_leads_admin.post('/admin/api/web-leads')
@restricted
def create():
    data, error = payload()
    if error: return error
    try:
        values = validate(data)
        lead_id = str(uuid.uuid4())
        with get_db_session() as session:
            session.add(Lead(id=lead_id, **values))
        return jsonify(ok=True, id=lead_id), 201
    except InvalidLead as exc:
        return jsonify(error='Revisa los campos obligatorios y el consentimiento', code=str(exc)), 400

@web_leads_admin.patch('/admin/api/web-leads/<lead_id>')
@restricted
def edit(lead_id):
    data, error = payload()
    if error: return error
    allowed = {'name','email','lang','business_type','solution_type','features','online_payments','ai','integration','integration_details','description'}
    if set(data)-allowed: return jsonify(error='Hay campos que no se pueden modificar'), 400
    try:
        with get_db_session() as session:
            lead = session.get(Lead, lead_id)
            if not lead: return jsonify(error='Solicitud no encontrada'), 404
            merged = serialize(lead)
            merged['lang'] = merged.pop('language')
            merged['privacy_consent'] = True  # Preserve the consent already recorded; never rewrite its version.
            merged.update(data)
            values = validate(merged)
            for key, value in values.items(): setattr(lead, key, value)
        return jsonify(ok=True)
    except InvalidLead as exc:
        return jsonify(error='Datos inválidos', code=str(exc)), 400

@web_leads_admin.delete('/admin/api/web-leads/<lead_id>')
@restricted
def remove(lead_id):
    with get_db_session() as session:
        lead = session.get(Lead, lead_id)
        if not lead: return jsonify(error='Solicitud no encontrada'), 404
        session.delete(lead)
    return jsonify(ok=True)

@web_leads_admin.errorhandler(SQLAlchemyError)
def database_error(_):
    return jsonify(error='No se pudo completar la operación. Intenta nuevamente.'), 503
