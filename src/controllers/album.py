import hashlib
import io
import os
import re
import secrets
import string
import time
import unicodedata
import uuid
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path

import bcrypt
from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, session, url_for
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func
from itsdangerous import BadSignature, URLSafeSerializer
from werkzeug.utils import secure_filename

from extensions import db
from models.album import Album, AlbumExternalMedia, AlbumGift, AlbumMedia, AlbumPage
from services.album_content import decrypt_gift, encrypt_gift, normalize_external_url, normalize_music_url, qr_data_url
from services.album_storage import AlbumStorage

album_bp = Blueprint("album", __name__)
SESSION_KEY = "ola_album_admin_until"
USER_SESSION_KEY = "album_dpia_user"
MAX_FILES = 20
MAX_IMAGE = 20 * 1024 * 1024
MAX_VIDEO = 250 * 1024 * 1024
_attempts = {}
SHORT_CODE_LENGTH = 10
SHORT_CODE_ALPHABET = string.ascii_letters + string.digits


def _admin(item):
    records = session.get(SESSION_KEY, {})
    record = records.get(str(item.id), {}) if isinstance(records, dict) else {}
    return float(record.get("until", 0)) > time.time() and int(record.get("version", 0)) == item.admin_session_version

def _set_admin(item):
    records = session.get(SESSION_KEY, {})
    if not isinstance(records, dict):
        records = {}
    records[str(item.id)] = {"until": time.time() + int(os.environ.get("ALBUM_ADMIN_SESSION_SECONDS", "3600")), "version": item.admin_session_version}
    session[SESSION_KEY] = records
    session.permanent = False

def _pin_hash(item):
    return (item.admin_pin_hash or os.environ.get("ALBUM_ADMIN_PIN_HASH", "")).encode()

def _csrf():
    token = session.get("ola_album_csrf")
    if not token: token = session["ola_album_csrf"] = secrets.token_urlsafe(32)
    return token

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        item = _owned_album(kwargs.get("slug"))
        if not _admin(item): return jsonify(error="unauthorized"), 401
        if request.method not in ("GET", "HEAD") and not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), _csrf()):
            return jsonify(error="invalid_request"), 403
        return fn(*args, **kwargs)
    return wrapped

def _current_user():
    saved = session.get(USER_SESSION_KEY) or {}
    user_id = saved.get("id") if isinstance(saved, dict) else None
    if not user_id:
        return None
    from sqlalchemy import text
    user = db.session.execute(text("SELECT id, correo_electronico, activo FROM usuarios WHERE id = :id LIMIT 1"), {"id": int(user_id)}).mappings().first()
    if not user or not bool(user.get("activo")):
        session.pop(USER_SESSION_KEY, None)
        return None
    return user

def _owned_album(slug):
    user = _current_user()
    if not user:
        abort(401)
    item = Album.query.filter_by(slug=slug, owner_user_id=int(user["id"]), active=True).first()
    if not item:
        abort(404)
    return item

def _album(slug):
    item = Album.query.filter_by(slug=slug, active=True).first()
    if not item: abort(404)
    return item

def _album_template_context(item):
    legacy_slug = os.environ.get("ALBUM_LEGACY_SLUG", "ola-prod-9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4")
    return {"album_title": item.title, "personalized_ola": item.slug == legacy_slug}

def _gift_encryption_key():
    return os.environ.get("ALBUM_GIFT_ENCRYPTION_KEY") or current_app.secret_key

def _page_token(album_id, page_id, version=1):
    signer = URLSafeSerializer(current_app.secret_key, salt="album-page-share-v1")
    return signer.dumps({"album": album_id, "page": page_id, "version": version})

def _short_urls_enabled():
    return os.environ.get("ALBUM_SHORT_URLS_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")

def _slug_text(value):
    value = str(value or "").translate(str.maketrans({"ł": "l", "Ł": "L"}))
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")[:80] or "hoja"

def _new_short_slug(page):
    label = f"{_slug_text(page.title)}-{date.today().strftime('%d%m%y')}"
    for _ in range(20):
        code = "".join(secrets.choice(SHORT_CODE_ALPHABET) for _ in range(SHORT_CODE_LENGTH))
        if not AlbumPage.query.filter(AlbumPage.short_slug.like(f"{code}/%")).first():
            return f"{code}/{label}"
    raise RuntimeError("short_slug_generation_failed")

def _long_share_path(page):
    return url_for("album.album_page_view", slug=page.album.slug, token=_page_token(page.album_id, page.id, page.share_version))

def _absolute_url(path):
    base = os.environ.get("ALBUM_PUBLIC_BASE_URL", request.url_root).rstrip("/")
    return base + path

def _share_url(page):
    if _short_urls_enabled() and page.short_slug:
        return _absolute_url("/" + page.short_slug)
    return _absolute_url(_long_share_path(page))

def _preview_token(album_id, page_id):
    signer = URLSafeSerializer(current_app.secret_key, salt="album-page-preview-v1")
    return signer.dumps({"album": album_id, "page": page_id})

def _contribution_token(album_id, page_id, version=1):
    signer = URLSafeSerializer(current_app.secret_key, salt="album-page-contribution-v1")
    return signer.dumps({"album": album_id, "page": page_id, "version": version})


def _contribution_page(item, token):
    signer = URLSafeSerializer(current_app.secret_key, salt="album-page-contribution-v1")
    try:
        payload = signer.loads(token)
        album_id, page_id = int(payload["album"]), int(payload["page"])
    except (BadSignature, KeyError, TypeError, ValueError):
        abort(404)
    if album_id != item.id:
        abort(404)
    page = AlbumPage.query.filter_by(id=page_id, album_id=item.id, is_visible=True, share_enabled=True, contribution_enabled=True).first_or_404()
    if int(payload.get("version", 1)) != page.contribution_version:
        abort(404)
    if not page.contribution_expires_at or page.contribution_expires_at <= datetime.utcnow():
        abort(410)
    return page

def _preview_page(item, token):
    signer = URLSafeSerializer(current_app.secret_key, salt="album-page-preview-v1")
    try:
        payload = signer.loads(token)
        album_id, page_id = int(payload["album"]), int(payload["page"])
    except (BadSignature, KeyError, TypeError, ValueError):
        abort(404)
    if album_id != item.id: abort(404)
    return AlbumPage.query.filter_by(id=page_id, album_id=item.id).first_or_404()

def _shared_page(item, token):
    signer = URLSafeSerializer(current_app.secret_key, salt="album-page-share-v1")
    try:
        payload = signer.loads(token)
        album_id, page_id = int(payload["album"]), int(payload["page"])
    except (BadSignature, KeyError, TypeError, ValueError):
        abort(404)
    if album_id != item.id:
        abort(404)
    page = AlbumPage.query.filter_by(id=page_id, album_id=item.id, is_visible=True, share_enabled=True).first_or_404()
    token_version = int(payload.get("version", 1))
    if token_version != page.share_version: abort(404)
    return page

def _media_json(item, storage):
    return {"id":item.id,"type":item.media_type,"name":item.display_name or item.original_name,"url":storage.signed_url(item.object_key),"thumbnail_url":storage.signed_url(item.thumbnail_key or item.object_key),"moderation_status":item.moderation_status,"contributor_name":item.contributor_name or ""}

def _external_json(item):
    return {"id": item.id, "type": item.media_type, "provider": item.provider, "url": item.original_url, "embed_url": item.embed_url, "title": item.title or "", "alt_text": item.alt_text or ""}

def _gift_json(item, admin=False):
    expired = bool(item.expires_at and item.expires_at < datetime.utcnow())
    status = "expired" if expired and item.status == "available" else item.status
    result = {"id": item.id, "token": item.public_token, "title": item.title, "message": item.message or "", "provider": item.provider or "", "status": status, "requires_pin": bool(item.pin_hash), "expires_at": item.expires_at.isoformat() if item.expires_at else None}
    if admin:
        result["opened_at"] = item.opened_at.isoformat() if item.opened_at else None
        result["claimed_at"] = item.claimed_at.isoformat() if item.claimed_at else None
    return result

def _page_json(page, storage, admin=False):
    approved_media=[m for m in page.media if m.moderation_status == "approved"]
    result={"id":page.id,"title":page.title,"memory_date":page.memory_date.isoformat() if page.memory_date else None,"description":page.description or "","position":page.position,"is_visible":page.is_visible,"music_url":page.music_url or page.album.music_url,"page_music_url":page.music_url,"media":[_media_json(m,storage) for m in approved_media],"external_media":[_external_json(m) for m in page.external_media],"gifts":[_gift_json(g,admin) for g in page.gifts]}
    if admin:
        result["updated_at"] = page.updated_at.isoformat()
        preview_token = _preview_token(page.album_id, page.id)
        result["share_enabled"] = page.share_enabled
        result["share_url"] = _share_url(page)
        result["preview_url"] = request.url_root.rstrip("/") + f"/album/{page.album.slug}/preview/{preview_token}"
        contribution_active = bool(page.contribution_enabled and page.contribution_expires_at and page.contribution_expires_at > datetime.utcnow())
        contribution_token = _contribution_token(page.album_id, page.id, page.contribution_version)
        result["contribution_enabled"] = contribution_active
        result["contribution_expires_at"] = page.contribution_expires_at.isoformat() if page.contribution_expires_at else None
        result["contribution_url"] = request.url_root.rstrip("/") + f"/album/{page.album.slug}/contribute/{contribution_token}"
        result["pending_contributions"] = [_media_json(m, storage) for m in page.media if m.moderation_status == "pending"]
    return result

@album_bp.get("/album")
def album_home():
    user = _current_user()
    if not user:
        return render_template("album/login.html")
    item = Album.query.filter_by(owner_user_id=int(user["id"]), active=True).first()
    if not item:
        item = Album(owner_user_id=int(user["id"]), slug=f"album-{uuid.uuid4().hex}", title="Nuestros momentos", active=True)
        db.session.add(item); db.session.commit()
    return redirect(url_for("album.album_view", slug=item.slug))

@album_bp.post("/api/album/session")
def album_user_login():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip(); now = time.time()
    recent = [stamp for stamp in _attempts.get("user:" + ip, []) if now - stamp < 900]
    if len(recent) >= 5: return jsonify(error="try_later"), 429
    data = request.get_json(silent=True) or {}
    if str(data.get("hp", "")).strip(): return jsonify(error="invalid_request"), 400
    email = str(data.get("email", "")).strip().lower(); password = str(data.get("password", ""))
    from controllers.campania_telefonica import _consultar_usuario_por_correo, _verificar_password_usuario
    user = _consultar_usuario_por_correo(email) if email and password else None
    if not user or not bool(user.get("activo")) or not _verificar_password_usuario(user.get("password"), password):
        recent.append(now); _attempts["user:" + ip] = recent
        return jsonify(error="invalid_credentials"), 401
    _attempts.pop("user:" + ip, None)
    session[USER_SESSION_KEY] = {"id": int(user["id"]), "email": user["correo_electronico"]}
    item = Album.query.filter_by(owner_user_id=int(user["id"]), active=True).first()
    if not item:
        item = Album(owner_user_id=int(user["id"]), slug=f"album-{uuid.uuid4().hex}", title="Nuestros momentos", active=True)
        db.session.add(item); db.session.commit()
    return jsonify(ok=True, album_url=url_for("album.album_view", slug=item.slug), email=user["correo_electronico"])

@album_bp.get("/api/album/session")
def album_user_session():
    user = _current_user()
    if not user:
        return jsonify(authenticated=False), 401
    item = Album.query.filter_by(owner_user_id=int(user["id"]), active=True).first()
    return jsonify(authenticated=True, email=user["correo_electronico"], album_url=url_for("album.album_view", slug=item.slug) if item else url_for("album.album_home"))

@album_bp.post("/api/album/session/logout")
def album_user_logout():
    session.pop(USER_SESSION_KEY, None); session.pop(SESSION_KEY, None)
    return jsonify(ok=True)

@album_bp.get("/album/<slug>")
def album_view(slug):
    if not _current_user(): return redirect(url_for("album.album_home"))
    item = _owned_album(slug)
    response=current_app.make_response(render_template("album/index.html", slug=slug, **_album_template_context(item)))
    response.headers["X-Robots-Tag"]="noindex, nofollow, noarchive"; response.headers["Cache-Control"]="private, no-store"
    return response

@album_bp.get("/album/<slug>/page/<token>")
def album_page_view(slug, token):
    item = _album(slug)
    _shared_page(item, token)
    response = current_app.make_response(render_template("album/index.html", slug=slug, page_token=token, **_album_template_context(item)))
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["Cache-Control"] = "private, no-store"
    return response

@album_bp.get("/<share_code>/<label>")
def album_short_link(share_code, label):
    if not _short_urls_enabled() or not re.fullmatch(r"[A-Za-z0-9]{10}", share_code):
        abort(404)
    page = (AlbumPage.query.join(Album)
            .filter(AlbumPage.short_slug == f"{share_code}/{label}",
                    AlbumPage.share_enabled.is_(True),
                    AlbumPage.is_visible.is_(True),
                    Album.active.is_(True)).first_or_404())
    response = redirect(_long_share_path(page), code=302)
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["Cache-Control"] = "private, no-store"
    return response


@album_bp.get("/album/<slug>/contribute/<token>")
def album_contribution_view(slug, token):
    item = _album(slug)
    _contribution_page(item, token)
    response = current_app.make_response(render_template("album/index.html", slug=slug, contribution_token=token, **_album_template_context(item)))
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["Cache-Control"] = "private, no-store"
    return response
@album_bp.get("/album/<slug>/preview/<token>")
def album_page_preview(slug, token):
    item = _owned_album(slug); _preview_page(item, token)
    response = current_app.make_response(render_template("album/index.html", slug=slug, preview_token=token, **_album_template_context(item)))
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["Cache-Control"] = "private, no-store"
    return response


@album_bp.get("/api/albums/<slug>/contribute/<token>")
def album_contribution_api(slug, token):
    item = _album(slug); page = _contribution_page(item, token); storage = AlbumStorage()
    page_data = _page_json(page, storage); page_data["gifts"] = []
    return jsonify(title=item.title, subtitle=item.subtitle, music_url=item.music_url, contribution_enabled=True, contribution_expires_at=page.contribution_expires_at.isoformat(), pages=[page_data])
@album_bp.get("/api/albums/<slug>/preview/<token>")
def album_preview_api(slug, token):
    item = _owned_album(slug); page = _preview_page(item, token); storage = AlbumStorage()
    return jsonify(title=item.title, subtitle=item.subtitle, music_url=item.music_url, pages=[_page_json(page, storage)])

@album_bp.get("/api/albums/<slug>")
def album_public(slug):
    item=_owned_album(slug); storage=AlbumStorage()
    pages=AlbumPage.query.filter_by(album_id=item.id,is_visible=True).order_by(AlbumPage.position).all()
    return jsonify(title=item.title,subtitle=item.subtitle,music_url=item.music_url,pages=[_page_json(p,storage) for p in pages])

@album_bp.get("/api/albums/<slug>/shared/<token>")
def album_shared(slug, token):
    item = _album(slug); page = _shared_page(item, token); storage = AlbumStorage()
    return jsonify(title=item.title, subtitle=item.subtitle, music_url=item.music_url, pages=[_page_json(page, storage)])

@album_bp.post("/api/albums/<slug>/admin/login")
def album_login(slug):
    item=_owned_album(slug); ip=request.headers.get("X-Forwarded-For",request.remote_addr or "").split(",")[0].strip(); now=time.time()
    recent=[stamp for stamp in _attempts.get(ip,[]) if now-stamp<900]
    if len(recent)>=5: return jsonify(error="try_later"),429
    pin_hash=_pin_hash(item); pin=str((request.get_json(silent=True) or {}).get("pin","")).encode()
    if not pin_hash: return jsonify(error="pin_not_configured"),503
    try: valid=bool(pin) and bcrypt.checkpw(pin,pin_hash)
    except ValueError: valid=False
    if not valid:
        recent.append(now); _attempts[ip]=recent; return jsonify(error="invalid_credentials"),401
    _attempts.pop(ip,None); _set_admin(item)
    return jsonify(ok=True,csrf_token=_csrf())

@album_bp.post("/api/albums/<slug>/admin/logout")
@admin_required
def album_logout(slug):
    item = _album(slug); records = session.get(SESSION_KEY, {})
    if isinstance(records, dict): records.pop(str(item.id), None); session[SESSION_KEY] = records
    return jsonify(ok=True)

@album_bp.post("/api/albums/<slug>/admin/pin")
@admin_required
def album_change_pin(slug):
    item = _album(slug); data = request.get_json(silent=True) or {}
    current_pin = str(data.get("current_pin", "")); new_pin = str(data.get("new_pin", ""))
    if len(new_pin) < 4 or len(new_pin) > 64:
        return jsonify(error="invalid_new_pin"), 400
    try:
        valid = bool(current_pin) and bcrypt.checkpw(current_pin.encode(), _pin_hash(item))
    except ValueError:
        valid = False
    if not valid:
        return jsonify(error="invalid_current_pin"), 400
    if secrets.compare_digest(current_pin, new_pin):
        return jsonify(error="same_pin"), 400
    item.admin_pin_hash = bcrypt.hashpw(new_pin.encode(), bcrypt.gensalt()).decode()
    item.admin_session_version = (item.admin_session_version or 1) + 1
    db.session.commit(); _set_admin(item)
    return jsonify(ok=True, csrf_token=_csrf())

@album_bp.patch("/api/albums/<slug>/admin/title")
@admin_required
def album_change_title(slug):
    item = _album(slug)
    title = str((request.get_json(silent=True) or {}).get("title", "")).strip()[:160]
    if not title:
        return jsonify(error="title_required"), 400
    item.title = title; db.session.commit()
    return jsonify(ok=True, title=item.title)

@album_bp.get("/api/albums/<slug>/admin")
@admin_required
def album_admin(slug):
    item = _album(slug)
    if _short_urls_enabled():
        missing = [page for page in item.pages if page.share_enabled and not page.short_slug]
        for page in missing:
            page.short_slug = _new_short_slug(page)
        if missing: db.session.commit()
    storage = AlbumStorage()
    return jsonify(title=item.title,subtitle=item.subtitle,music_url=item.music_url,csrf_token=_csrf(),pages=[_page_json(p,storage,True) for p in item.pages])

@album_bp.post("/api/albums/<slug>/pages")
@admin_required
def page_create(slug):
    item=_album(slug); pos=(db.session.query(func.max(AlbumPage.position)).filter_by(album_id=item.id).scalar() or 0)+1; today=date.today()
    page=AlbumPage(album_id=item.id,title=f"Recuerdo del {today.strftime('%d/%m/%Y')}",memory_date=today,position=pos,is_visible=False)
    db.session.add(page); db.session.commit(); return jsonify(id=page.id),201

@album_bp.patch("/api/albums/<slug>/pages/<int:page_id>")
@admin_required
def page_update(slug,page_id):
    item=_album(slug); page=AlbumPage.query.filter_by(id=page_id,album_id=item.id).first_or_404(); data=request.get_json(silent=True) or {}
    if "title" in data:
        title=str(data["title"]).strip()[:200]
        if not title: return jsonify(error="title_required"),400
        page.title=title
    if "description" in data: page.description=str(data["description"])[:10000]
    if "memory_date" in data: page.memory_date=date.fromisoformat(data["memory_date"]) if data["memory_date"] else None
    if "is_visible" in data: page.is_visible=bool(data["is_visible"])
    if "music_url" in data:
        try: page.music_url = normalize_music_url(data.get("music_url"))
        except ValueError as exc: return jsonify(error=str(exc)), 400
    db.session.commit(); return jsonify(ok=True)

@album_bp.delete("/api/albums/<slug>/pages/<int:page_id>")
@admin_required
def page_delete(slug,page_id):
    item=_album(slug); page=AlbumPage.query.filter_by(id=page_id,album_id=item.id).first_or_404(); storage=AlbumStorage()
    for media in page.media:
        for key in {media.object_key,media.thumbnail_key}:
            if key:
                try: storage.delete(key)
                except Exception: current_app.logger.exception("No se pudo eliminar objeto del álbum")
    db.session.delete(page); db.session.commit(); return "",204

@album_bp.patch("/api/albums/<slug>/pages/<int:page_id>/share")
@admin_required
def page_share_update(slug, page_id):
    item = _owned_album(slug)
    page = AlbumPage.query.filter_by(id=page_id, album_id=item.id).first_or_404()
    enabled = bool((request.get_json(silent=True) or {}).get("enabled"))
    if enabled and not page.is_visible:
        return jsonify(error="page_not_visible"), 400
    if not enabled:
        page.share_version = (page.share_version or 1) + 1
    elif not page.share_enabled or not page.short_slug:
        page.short_slug = _new_short_slug(page) if _short_urls_enabled() else page.short_slug
    page.share_enabled = enabled
    db.session.commit()
    return jsonify(enabled=page.share_enabled, share_url=_share_url(page))

@album_bp.post("/api/albums/<slug>/pages/reorder")
@admin_required
def pages_reorder(slug):
    item=_album(slug); ids=(request.get_json(silent=True) or {}).get("ids",[]); pages={p.id:p for p in item.pages}
    if set(ids)!=set(pages): return jsonify(error="invalid_order"),400
    for pos,pid in enumerate(ids,1): pages[pid].position=-pos
    db.session.flush()
    for pos,pid in enumerate(ids,1): pages[pid].position=pos
    db.session.commit(); return jsonify(ok=True)

def _prepare(upload):
    raw=upload.read(); size=len(raw); digest=hashlib.sha256(raw).hexdigest(); mime=(upload.mimetype or "").lower(); name=secure_filename(upload.filename or "archivo")[:255]
    if mime.startswith("image/"):
        if size>MAX_IMAGE: raise ValueError("image_too_large")
        try:
            image=ImageOps.exif_transpose(Image.open(io.BytesIO(raw))); image.thumbnail((2400,2400)); output=io.BytesIO(); image.convert("RGB").save(output,"JPEG",quality=88,optimize=True); optimized=output.getvalue()
            thumb=image.copy(); thumb.thumbnail((600,600)); tout=io.BytesIO(); thumb.convert("RGB").save(tout,"JPEG",quality=82,optimize=True)
            return "image",name,digest,size,image.width,image.height,optimized,tout.getvalue(),"image/jpeg"
        except (UnidentifiedImageError,OSError): raise ValueError("invalid_image")
    if mime.startswith("video/"):
        if size>MAX_VIDEO: raise ValueError("video_too_large")
        if mime not in {"video/mp4","video/quicktime","video/webm"}: raise ValueError("invalid_video")
        return "video",name,digest,size,None,None,raw,None,mime
    raise ValueError("unsupported_type")

@album_bp.post("/api/albums/<slug>/pages/<int:page_id>/media")
@admin_required
def media_upload(slug,page_id):
    item=_album(slug); page=AlbumPage.query.filter_by(id=page_id,album_id=item.id).first_or_404(); uploads=request.files.getlist("files")
    if not uploads or len(uploads)>MAX_FILES: return jsonify(error="invalid_file_count"),400
    storage=AlbumStorage(); created=[]; uploaded=[]
    try:
        next_pos=(db.session.query(func.max(AlbumMedia.position)).filter_by(page_id=page.id).scalar() or 0)+1
        for upload in uploads:
            kind,name,digest,size,width,height,payload,thumb,mime=_prepare(upload)
            if AlbumMedia.query.filter_by(page_id=page.id,sha256=digest).first(): continue
            uid=uuid.uuid4().hex; folder="images" if kind=="image" else "videos"; key=f"albums/{item.id}/{page.id}/{folder}/{uid}-{Path(name).stem}.{'jpg' if kind=='image' else Path(name).suffix.lstrip('.')}"
            storage.upload(key,io.BytesIO(payload),mime); uploaded.append(key); thumb_key=None
            if thumb is not None:
                thumb_key=f"albums/{item.id}/{page.id}/images/{uid}-thumb.jpg"; storage.upload(thumb_key,io.BytesIO(thumb),"image/jpeg"); uploaded.append(thumb_key)
            media=AlbumMedia(page_id=page.id,media_type=kind,original_name=name,object_key=key,thumbnail_key=thumb_key,mime_type=mime,size=size,sha256=digest,width=width,height=height,position=next_pos)
            next_pos+=1; db.session.add(media); created.append(media)
        db.session.commit(); return jsonify(ids=[m.id for m in created]),201
    except ValueError as exc:
        db.session.rollback()
        for key in uploaded:
            try: storage.delete(key)
            except Exception: pass
        return jsonify(error=str(exc)),400
    except Exception:
        db.session.rollback(); current_app.logger.exception("Falló carga del álbum")
        for key in uploaded:
            try: storage.delete(key)
            except Exception: pass
        return jsonify(error="upload_failed"),500

@album_bp.patch("/api/albums/<slug>/media/<int:media_id>")
@admin_required
def media_update(slug,media_id):
    item=_album(slug); media=AlbumMedia.query.join(AlbumPage).filter(AlbumMedia.id==media_id,AlbumPage.album_id==item.id).first_or_404(); media.display_name=str((request.get_json(silent=True) or {}).get("name","")).strip()[:255] or None; db.session.commit(); return jsonify(ok=True)

@album_bp.delete("/api/albums/<slug>/media/<int:media_id>")
@admin_required
def media_delete(slug,media_id):
    item=_album(slug); media=AlbumMedia.query.join(AlbumPage).filter(AlbumMedia.id==media_id,AlbumPage.album_id==item.id).first_or_404(); storage=AlbumStorage()
    for key in {media.object_key,media.thumbnail_key}:
        if key: storage.delete(key)
    db.session.delete(media); db.session.commit(); return "",204

@album_bp.patch("/api/albums/<slug>/admin/music")
@admin_required
def album_change_music(slug):
    item = _owned_album(slug)
    try:
        item.music_url = normalize_music_url((request.get_json(silent=True) or {}).get("music_url"))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    db.session.commit()
    return jsonify(ok=True, music_url=item.music_url)


@album_bp.post("/api/albums/<slug>/pages/<int:page_id>/external-media")
@admin_required
def external_media_create(slug, page_id):
    item = _owned_album(slug)
    page = AlbumPage.query.filter_by(id=page_id, album_id=item.id).first_or_404()
    data = request.get_json(silent=True) or {}
    try:
        normalized = normalize_external_url(data.get("url"))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    position = (db.session.query(func.max(AlbumExternalMedia.position)).filter_by(page_id=page.id).scalar() or 0) + 1
    external = AlbumExternalMedia(
        page_id=page.id, position=position, title=str(data.get("title", "")).strip()[:255] or None,
        alt_text=str(data.get("alt_text", "")).strip()[:500] or None, **normalized,
    )
    db.session.add(external); db.session.commit()
    return jsonify(item=_external_json(external)), 201


@album_bp.delete("/api/albums/<slug>/external-media/<int:media_id>")
@admin_required
def external_media_delete(slug, media_id):
    item = _owned_album(slug)
    external = AlbumExternalMedia.query.join(AlbumPage).filter(AlbumExternalMedia.id == media_id, AlbumPage.album_id == item.id).first_or_404()
    db.session.delete(external); db.session.commit()
    return "", 204


@album_bp.post("/api/albums/<slug>/pages/<int:page_id>/gifts")
@admin_required
def gift_create(slug, page_id):
    item = _owned_album(slug)
    page = AlbumPage.query.filter_by(id=page_id, album_id=item.id).first_or_404()
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()[:200]
    pin = str(data.get("pin", "")).strip()
    if not title: return jsonify(error="gift_title_required"), 400
    if pin and (len(pin) < 4 or len(pin) > 64): return jsonify(error="invalid_gift_pin"), 400
    expires_at = None
    if data.get("expires_at"):
        try: expires_at = datetime.fromisoformat(str(data["expires_at"]))
        except ValueError: return jsonify(error="invalid_expiration"), 400
    try: encrypted = encrypt_gift(_gift_encryption_key(), data.get("secret"))
    except ValueError as exc: return jsonify(error=str(exc)), 400
    gift = AlbumGift(
        page_id=page.id, public_token=secrets.token_urlsafe(24), title=title,
        message=str(data.get("message", ""))[:5000] or None,
        provider=str(data.get("provider", "")).strip()[:120] or None,
        secret_encrypted=encrypted, pin_hash=bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode() if pin else None,
        expires_at=expires_at, status="available",
    )
    db.session.add(gift); db.session.commit()
    return jsonify(gift=_gift_json(gift, True)), 201


@album_bp.patch("/api/albums/<slug>/gifts/<int:gift_id>")
@admin_required
def gift_update(slug, gift_id):
    item = _owned_album(slug)
    gift = AlbumGift.query.join(AlbumPage).filter(AlbumGift.id == gift_id, AlbumPage.album_id == item.id).first_or_404()
    data = request.get_json(silent=True) or {}
    status = str(data.get("status", ""))
    if status not in {"available", "claimed", "revoked"}: return jsonify(error="invalid_gift_status"), 400
    gift.status = status
    if status == "claimed" and not gift.claimed_at: gift.claimed_at = datetime.utcnow()
    db.session.commit()
    return jsonify(gift=_gift_json(gift, True))


@album_bp.delete("/api/albums/<slug>/gifts/<int:gift_id>")
@admin_required
def gift_delete(slug, gift_id):
    item = _owned_album(slug)
    gift = AlbumGift.query.join(AlbumPage).filter(AlbumGift.id == gift_id, AlbumPage.album_id == item.id).first_or_404()
    db.session.delete(gift); db.session.commit()
    return "", 204


@album_bp.post("/api/albums/<slug>/shared/<page_token>/gifts/<gift_token>/reveal")
@album_bp.post("/api/albums/<slug>/preview/<page_token>/gifts/<gift_token>/reveal")
def gift_reveal(slug, page_token, gift_token):
    if "/preview/" in request.path:
        item = _owned_album(slug); page = _preview_page(item, page_token)
    else:
        item = _album(slug); page = _shared_page(item, page_token)
    gift = AlbumGift.query.filter_by(page_id=page.id, public_token=gift_token).first_or_404()
    now = datetime.utcnow()
    if gift.status == "revoked": return jsonify(error="gift_revoked"), 410
    if gift.status == "claimed": return jsonify(error="gift_claimed"), 410
    if gift.expires_at and gift.expires_at < now: return jsonify(error="gift_expired"), 410
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
    attempt_key = f"gift:{gift.id}:{ip}"
    recent = [stamp for stamp in _attempts.get(attempt_key, []) if time.time() - stamp < 900]
    if len(recent) >= 8: return jsonify(error="try_later"), 429
    pin = str((request.get_json(silent=True) or {}).get("pin", ""))
    if gift.pin_hash:
        try: valid = bool(pin) and bcrypt.checkpw(pin.encode(), gift.pin_hash.encode())
        except ValueError: valid = False
        if not valid:
            recent.append(time.time()); _attempts[attempt_key] = recent
            return jsonify(error="invalid_gift_pin"), 401
    _attempts.pop(attempt_key, None)
    try: secret = decrypt_gift(_gift_encryption_key(), gift.secret_encrypted)
    except ValueError: return jsonify(error="gift_unavailable"), 500
    if not gift.opened_at: gift.opened_at = now
    if bool((request.get_json(silent=True) or {}).get("claim")):
        gift.status = "claimed"; gift.claimed_at = now
    db.session.commit()
    is_url = secret.startswith("https://")
    return jsonify(secret=secret, is_url=is_url, qr_data_url=qr_data_url(secret), status=gift.status)


@album_bp.post("/api/albums/<slug>/pages/<int:page_id>/contributions")
@admin_required
def contribution_access_update(slug, page_id):
    item = _owned_album(slug)
    page = AlbumPage.query.filter_by(id=page_id, album_id=item.id).first_or_404()
    data = request.get_json(silent=True) or {}
    enabled = bool(data.get("enabled"))
    if enabled and (not page.is_visible or not page.share_enabled):
        return jsonify(error="page_must_be_shared"), 400
    page.contribution_version = (page.contribution_version or 1) + 1
    page.contribution_enabled = enabled
    if enabled:
        try:
            hours = int(data.get("hours", 24))
        except (TypeError, ValueError):
            return jsonify(error="invalid_duration"), 400
        if hours < 1 or hours > 168:
            return jsonify(error="invalid_duration"), 400
        page.contribution_expires_at = datetime.utcnow() + timedelta(hours=hours)
    else:
        page.contribution_expires_at = None
    db.session.commit()
    token = _contribution_token(item.id, page.id, page.contribution_version)
    return jsonify(
        enabled=page.contribution_enabled,
        expires_at=page.contribution_expires_at.isoformat() if page.contribution_expires_at else None,
        contribution_url=request.url_root.rstrip("/") + f"/album/{item.slug}/contribute/{token}" if enabled else None,
    )


@album_bp.post("/api/albums/<slug>/contribute/<token>/media")
def contribution_media_upload(slug, token):
    item = _album(slug)
    page = _contribution_page(item, token)
    uploads = request.files.getlist("files")
    if not uploads or len(uploads) > 10:
        return jsonify(error="invalid_file_count"), 400
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
    attempt_key = f"album-contribution:{page.id}:{ip}"
    now = time.time()
    recent = [stamp for stamp in _attempts.get(attempt_key, []) if now - stamp < 3600]
    if len(recent) + len(uploads) > 20:
        return jsonify(error="try_later"), 429
    contributor_name = str(request.form.get("contributor_name", "")).strip()[:120] or None
    storage = AlbumStorage(); created = []; uploaded_keys = []
    try:
        next_pos = (db.session.query(func.max(AlbumMedia.position)).filter_by(page_id=page.id).scalar() or 0) + 1
        for upload in uploads:
            kind, name, digest, size, width, height, payload, thumb, mime = _prepare(upload)
            if AlbumMedia.query.filter_by(page_id=page.id, sha256=digest).first():
                continue
            uid = uuid.uuid4().hex
            extension = "jpg" if kind == "image" else Path(name).suffix.lstrip(".")
            key = f"albums/{item.id}/{page.id}/contributions/{uid}-{Path(name).stem}.{extension}"
            storage.upload(key, io.BytesIO(payload), mime); uploaded_keys.append(key)
            thumb_key = None
            if thumb is not None:
                thumb_key = f"albums/{item.id}/{page.id}/contributions/{uid}-thumb.jpg"
                storage.upload(thumb_key, io.BytesIO(thumb), "image/jpeg"); uploaded_keys.append(thumb_key)
            media = AlbumMedia(
                page_id=page.id, media_type=kind, original_name=name, object_key=key,
                thumbnail_key=thumb_key, mime_type=mime, size=size, sha256=digest,
                width=width, height=height, position=next_pos, moderation_status="pending",
                contributor_name=contributor_name,
            )
            next_pos += 1; db.session.add(media); created.append(media)
        db.session.commit()
        _attempts[attempt_key] = recent + [now] * len(uploads)
        return jsonify(ids=[media.id for media in created], status="pending"), 201
    except ValueError as exc:
        db.session.rollback()
        for key in uploaded_keys:
            try: storage.delete(key)
            except Exception: pass
        return jsonify(error=str(exc)), 400
    except Exception:
        db.session.rollback(); current_app.logger.exception("Falló aporte multimedia del álbum")
        for key in uploaded_keys:
            try: storage.delete(key)
            except Exception: pass
        return jsonify(error="upload_failed"), 500


@album_bp.patch("/api/albums/<slug>/contributions/<int:media_id>")
@admin_required
def contribution_moderate(slug, media_id):
    item = _owned_album(slug)
    media = AlbumMedia.query.join(AlbumPage).filter(
        AlbumMedia.id == media_id,
        AlbumPage.album_id == item.id,
        AlbumMedia.moderation_status == "pending",
    ).first_or_404()
    action = str((request.get_json(silent=True) or {}).get("action", ""))
    if action == "approve":
        media.moderation_status = "approved"
        db.session.commit()
        return jsonify(ok=True, status="approved")
    if action == "reject":
        storage = AlbumStorage()
        try:
            for key in {media.object_key, media.thumbnail_key}:
                if key: storage.delete(key)
        except Exception:
            current_app.logger.exception("No se pudo borrar un aporte rechazado")
            return jsonify(error="storage_delete_failed"), 500
        db.session.delete(media); db.session.commit()
        return jsonify(ok=True, status="rejected")
    return jsonify(error="invalid_action"), 400
