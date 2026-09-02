import hashlib
import io
import os
import secrets
import time
import uuid
from datetime import date
from functools import wraps
from pathlib import Path

import bcrypt
from flask import Blueprint, abort, current_app, jsonify, render_template, request, session
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func
from itsdangerous import BadSignature, URLSafeSerializer
from werkzeug.utils import secure_filename

from extensions import db
from models.album import Album, AlbumMedia, AlbumPage
from services.album_storage import AlbumStorage

album_bp = Blueprint("album", __name__)
SESSION_KEY = "ola_album_admin_until"
MAX_FILES = 20
MAX_IMAGE = 20 * 1024 * 1024
MAX_VIDEO = 250 * 1024 * 1024
_attempts = {}


def _admin(): return float(session.get(SESSION_KEY, 0)) > time.time()
def _csrf():
    token = session.get("ola_album_csrf")
    if not token: token = session["ola_album_csrf"] = secrets.token_urlsafe(32)
    return token

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not _admin(): return jsonify(error="unauthorized"), 401
        if request.method not in ("GET", "HEAD") and not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), _csrf()):
            return jsonify(error="invalid_request"), 403
        return fn(*args, **kwargs)
    return wrapped

def _album(slug):
    item = Album.query.filter_by(slug=slug, active=True).first()
    if not item: abort(404)
    return item

def _page_token(album_id, page_id):
    signer = URLSafeSerializer(current_app.secret_key, salt="album-page-share-v1")
    return signer.dumps({"album": album_id, "page": page_id})

def _shared_page(item, token):
    signer = URLSafeSerializer(current_app.secret_key, salt="album-page-share-v1")
    try:
        payload = signer.loads(token)
        album_id, page_id = int(payload["album"]), int(payload["page"])
    except (BadSignature, KeyError, TypeError, ValueError):
        abort(404)
    if album_id != item.id:
        abort(404)
    return AlbumPage.query.filter_by(id=page_id, album_id=item.id, is_visible=True).first_or_404()

def _media_json(item, storage):
    return {"id":item.id,"type":item.media_type,"name":item.display_name or item.original_name,"url":storage.signed_url(item.object_key),"thumbnail_url":storage.signed_url(item.thumbnail_key or item.object_key)}

def _page_json(page, storage, admin=False):
    result={"id":page.id,"title":page.title,"memory_date":page.memory_date.isoformat() if page.memory_date else None,"description":page.description or "","position":page.position,"is_visible":page.is_visible,"media":[_media_json(m,storage) for m in page.media]}
    if admin:
        result["updated_at"] = page.updated_at.isoformat()
        token = _page_token(page.album_id, page.id)
        result["share_url"] = request.url_root.rstrip("/") + f"/album/{page.album.slug}/page/{token}"
    return result

@album_bp.get("/album/<slug>")
def album_view(slug):
    _album(slug)
    response=current_app.make_response(render_template("album/index.html",slug=slug))
    response.headers["X-Robots-Tag"]="noindex, nofollow, noarchive"; response.headers["Cache-Control"]="private, no-store"
    return response

@album_bp.get("/album/<slug>/page/<token>")
def album_page_view(slug, token):
    item = _album(slug)
    _shared_page(item, token)
    response = current_app.make_response(render_template("album/index.html", slug=slug, page_token=token))
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["Cache-Control"] = "private, no-store"
    return response

@album_bp.get("/api/albums/<slug>")
def album_public(slug):
    item=_album(slug); storage=AlbumStorage()
    pages=AlbumPage.query.filter_by(album_id=item.id,is_visible=True).order_by(AlbumPage.position).all()
    return jsonify(title=item.title,subtitle=item.subtitle,music_url=item.music_url,pages=[_page_json(p,storage) for p in pages])

@album_bp.get("/api/albums/<slug>/shared/<token>")
def album_shared(slug, token):
    item = _album(slug); page = _shared_page(item, token); storage = AlbumStorage()
    return jsonify(title=item.title, subtitle=item.subtitle, music_url=item.music_url, pages=[_page_json(page, storage)])

@album_bp.post("/api/albums/<slug>/admin/login")
def album_login(slug):
    _album(slug); ip=request.headers.get("X-Forwarded-For",request.remote_addr or "").split(",")[0].strip(); now=time.time()
    recent=[stamp for stamp in _attempts.get(ip,[]) if now-stamp<900]
    if len(recent)>=5: return jsonify(error="try_later"),429
    pin_hash=os.environ.get("ALBUM_ADMIN_PIN_HASH","").encode(); pin=str((request.get_json(silent=True) or {}).get("pin","")).encode()
    if not pin_hash: return jsonify(error="pin_not_configured"),503
    try: valid=bool(pin) and bcrypt.checkpw(pin,pin_hash)
    except ValueError: valid=False
    if not valid:
        recent.append(now); _attempts[ip]=recent; return jsonify(error="invalid_credentials"),401
    _attempts.pop(ip,None); session[SESSION_KEY]=now+int(os.environ.get("ALBUM_ADMIN_SESSION_SECONDS","3600")); session.permanent=False
    return jsonify(ok=True,csrf_token=_csrf())

@album_bp.post("/api/albums/<slug>/admin/logout")
@admin_required
def album_logout(slug): _album(slug); session.pop(SESSION_KEY,None); return jsonify(ok=True)

@album_bp.get("/api/albums/<slug>/admin")
@admin_required
def album_admin(slug):
    item=_album(slug); storage=AlbumStorage(); return jsonify(csrf_token=_csrf(),pages=[_page_json(p,storage,True) for p in item.pages])

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
            uid=uuid.uuid4().hex; folder="images" if kind=="image" else "videos"; key=f"albums/ola/{page.id}/{folder}/{uid}-{Path(name).stem}.{'jpg' if kind=='image' else Path(name).suffix.lstrip('.')}"
            storage.upload(key,io.BytesIO(payload),mime); uploaded.append(key); thumb_key=None
            if thumb is not None:
                thumb_key=f"albums/ola/{page.id}/images/{uid}-thumb.jpg"; storage.upload(thumb_key,io.BytesIO(thumb),"image/jpeg"); uploaded.append(thumb_key)
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
