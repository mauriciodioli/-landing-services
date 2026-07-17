from flask import Blueprint, request, jsonify
from popups.services.selector import seleccionar_popup, seleccionar_popup_test, seleccionar_popups
import sys

api = Blueprint("api", __name__)

# ✅ acepta /api/p y /api/p/ + OPTIONS (204)
@api.route("/api/p", methods=["GET", "POST", "OPTIONS"])
@api.route("/api/p/", methods=["GET", "POST", "OPTIONS"])
def api_popup():
    if request.method == "OPTIONS":
        return "", 204  # preflight OK

    print("💥 api_popup() ACTIVADO", file=sys.stderr)

    q = request.args.to_dict() if request.args else {}
    b = request.get_json(silent=True) or {}

    params = {
        "dominio": (b.get("dominio") or q.get("dominio") or ""),
        "categoria": (b.get("categoria") or q.get("categoria") or ""),
        "lang": (b.get("lang") or q.get("lang") or ""),
        "cp": (b.get("cp") or q.get("cp") or ""),
    }
    test_flag = (str(b.get("test") or q.get("test") or "")).lower() in ("1", "true", "yes")
    is_list   = (q.get("list") == "1")
    limit     = b.get("limit") or q.get("limit")

    print("METHOD:", request.method, "PARAMS:", params, "TEST:", test_flag, "LIST:", is_list, "LIMIT:", limit, file=sys.stderr)

    if test_flag and not is_list:
        data = seleccionar_popup_test(**params)
        return jsonify({"found": True, **data}), 200

    if is_list:
        items = seleccionar_popups(
            dominio=params["dominio"],
            categoria=params["categoria"],
            lang=params["lang"],
            cp=params["cp"],
            limit=limit,
        ) or []
        return jsonify({"items": items, "found": bool(items)}), 200

    data = seleccionar_popup(**params)
    if not data:
        return jsonify({"found": False}), 200
    return jsonify({"found": True, **data}), 200


@api.get("/health")
def health():
    return {"ok": True, "service": "dpia-popup-service"}, 200


# ✅ también OPTIONS + ambas rutas para evitar 308
@api.route("/api/popup/list", methods=["POST", "OPTIONS"])
@api.route("/api/popup/list/", methods=["POST", "OPTIONS"])
def api_popup_list():
    if request.method == "OPTIONS":
        return "", 204

    b = request.get_json(silent=True) or {}
    items = seleccionar_popups(
        dominio=b.get("dominio"),
        categoria=b.get("categoria"),
        lang=b.get("lang"),
        cp=b.get("cp"),
        limit=b.get("limit"),
    )
    return jsonify({"items": items, "found": bool(items)}), 200


