from flask import Blueprint, request, jsonify
from utils.db_session import get_db_session
from models.publicaciones.ambitos import Ambitos
from models.publicaciones.ambitoCategoria import AmbitoCategoria
from models.codigoPostal import CodigoPostal

lookup = Blueprint('comercio_lookup', __name__)


@lookup.route('/api/lookup/ambitos', methods=['GET'])
def api_lookup_ambitos():
    q = (request.args.get('q') or '').strip()
    codigo_postal = (request.args.get('codigoPostal') or '').strip()
    idioma = (request.args.get('idioma') or '').strip()
    with get_db_session() as db_session:
        # Si se proporciona un código postal, obtener ámbitos asociados desde ambito_codigo_postal
        if codigo_postal:
            # Buscar el registro de CodigoPostal
            cp = db_session.query(CodigoPostal).filter(CodigoPostal.codigoPostal == codigo_postal).first()
            if cp:
                # Importar aquí para evitar import cycles
                from models.publicaciones.ambito_codigo_postal import AmbitoCodigoPostal
                # obtener ambito_ids asociados
                ambito_ids = db_session.query(AmbitoCodigoPostal.ambito_id).filter(AmbitoCodigoPostal.codigo_postal_id == cp.id).distinct().all()
                ambito_ids = [a[0] for a in ambito_ids]
                if ambito_ids:
                    items = db_session.query(Ambitos).filter(Ambitos.id.in_(ambito_ids)).order_by(Ambitos.nombre).all()
                    # si se solicitó idioma, filtrar por traducciones disponibles
                    if idioma:
                        from models.publicaciones.ambito_general import AmbitoTraduccion
                        trads = db_session.query(AmbitoTraduccion.valor).filter(AmbitoTraduccion.idioma == idioma).all()
                        trad_set = set([t[0] for t in trads])
                        items = [a for a in items if (a.idioma == idioma) or (a.valor and a.valor in trad_set)]
                    return jsonify({'success': True, 'items': [{'id': a.id, 'nombre': a.nombre, 'valor': a.valor} for a in items]})
            # si no se encontró o no hay asociaciones, caer al comportamiento por defecto
        query = db_session.query(Ambitos)
        if q:
            query = query.filter(Ambitos.nombre.ilike(f"%{q}%") | Ambitos.valor.ilike(f"%{q}%"))
        items = query.order_by(Ambitos.nombre).limit(50).all()
        if idioma:
            from models.publicaciones.ambito_general import AmbitoTraduccion
            trads = db_session.query(AmbitoTraduccion.valor).filter(AmbitoTraduccion.idioma == idioma).all()
            trad_set = set([t[0] for t in trads])
            items = [a for a in items if (a.idioma == idioma) or (a.valor and a.valor in trad_set)]
        return jsonify({'success': True, 'items': [{'id': a.id, 'nombre': a.nombre, 'valor': a.valor} for a in items]})


@lookup.route('/api/lookup/categorias', methods=['GET'])
def api_lookup_categorias():
    q = (request.args.get('q') or '').strip()
    id_param = request.args.get('id')
    ambito_id = request.args.get('ambito_id')
    with get_db_session() as db_session:
        # Si se pasa ambito_id, buscar relaciones en ambitoCategoriaRelation
        if ambito_id:
            try:
                from models.publicaciones.ambitoCategoriaRelation import AmbitoCategoriaRelation
                rels = db_session.query(AmbitoCategoriaRelation).filter(AmbitoCategoriaRelation.ambito_id == int(ambito_id)).all()
                cat_ids = [r.ambitoCategoria_id for r in rels]
                if cat_ids:
                    items = db_session.query(AmbitoCategoria).filter(AmbitoCategoria.id.in_(cat_ids)).order_by(AmbitoCategoria.nombre).all()
                    return jsonify({'success': True, 'items': [{'id': c.id, 'nombre': c.nombre, 'valor': c.valor} for c in items]})
            except Exception:
                pass

        query = db_session.query(AmbitoCategoria)
        if id_param:
            try:
                query = query.filter(AmbitoCategoria.id == int(id_param))
            except Exception:
                pass
        elif q:
            query = query.filter(AmbitoCategoria.nombre.ilike(f"%{q}%") | AmbitoCategoria.valor.ilike(f"%{q}%"))
        items = query.order_by(AmbitoCategoria.nombre).limit(50).all()
        return jsonify({'success': True, 'items': [{'id': c.id, 'nombre': c.nombre, 'valor': c.valor} for c in items]})


@lookup.route('/api/lookup/codigos', methods=['GET'])
def api_lookup_codigos():
    q = (request.args.get('q') or '').strip()
    with get_db_session() as db_session:
        query = db_session.query(CodigoPostal)
        if q:
            query = query.filter(CodigoPostal.codigoPostal.ilike(f"%{q}%") | CodigoPostal.ciudad.ilike(f"%{q}%"))
        items = query.order_by(CodigoPostal.codigoPostal).limit(100).all()
        return jsonify({'success': True, 'items': [{'id': cp.id, 'codigoPostal': cp.codigoPostal, 'ciudad': cp.ciudad} for cp in items]})
