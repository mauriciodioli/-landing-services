"""Validación de contenido externo, cifrado de regalos y generación de QR."""
import base64
import hashlib
import io
import re
from urllib.parse import parse_qs, urlparse

from cryptography.fernet import Fernet, InvalidToken
import qrcode


_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif")


def _https_url(value):
    value = str(value or "").strip()
    if len(value) > 2000:
        raise ValueError("url_too_long")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("invalid_url")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "0.0.0.0", "127.0.0.1", "::1"} or host.endswith((".local", ".internal")):
        raise ValueError("invalid_url")
    return value, parsed, host


def normalize_music_url(value):
    if not str(value or "").strip():
        return None
    url, parsed, host = _https_url(value)
    if host in {"open.spotify.com", "www.open.spotify.com"}:
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] in {"track", "album", "playlist", "episode", "show"}:
            return f"https://open.spotify.com/{parts[0]}/{parts[1]}"
    video_id = None
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/").split("/")[0]
    elif host in {"youtube.com", "www.youtube.com", "music.youtube.com"}:
        video_id = parse_qs(parsed.query).get("v", [None])[0]
    if video_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        return f"https://www.youtube.com/watch?v={video_id}"
    if parsed.path.lower().endswith((".mp3", ".m4a", ".ogg", ".wav")):
        return url
    raise ValueError("unsupported_music_url")


def normalize_external_url(value):
    url, parsed, host = _https_url(value)
    path = parsed.path
    video_id = None
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = path.strip("/").split("/")[0]
    elif host in {"youtube.com", "www.youtube.com", "music.youtube.com"}:
        video_id = parse_qs(parsed.query).get("v", [None])[0]
    if video_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        return {"media_type": "video", "provider": "youtube", "original_url": url, "embed_url": f"https://www.youtube-nocookie.com/embed/{video_id}"}
    if host in {"vimeo.com", "www.vimeo.com", "player.vimeo.com"}:
        match = re.search(r"/(?:video/)?(\d+)", path)
        if match:
            return {"media_type": "video", "provider": "vimeo", "original_url": url, "embed_url": f"https://player.vimeo.com/video/{match.group(1)}"}
    if host in {"giphy.com", "www.giphy.com", "media.giphy.com"}:
        match = re.search(r"(?:gifs/[^/]*-|/media/)([A-Za-z0-9]+)", path)
        if match:
            return {"media_type": "gif", "provider": "giphy", "original_url": url, "embed_url": f"https://giphy.com/embed/{match.group(1)}"}
    if host in {"tenor.com", "www.tenor.com"}:
        match = re.search(r"-(\d+)(?:/)?$", path)
        if match:
            return {"media_type": "gif", "provider": "tenor", "original_url": url, "embed_url": f"https://tenor.com/embed/{match.group(1)}"}
    if path.lower().endswith(_IMAGE_EXTENSIONS):
        return {"media_type": "gif" if path.lower().endswith(".gif") else "image", "provider": "direct", "original_url": url, "embed_url": url}
    raise ValueError("unsupported_external_url")


def _fernet(secret_key):
    digest = hashlib.sha256(str(secret_key).encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_gift(secret_key, value):
    value = str(value or "").strip()
    if not value or len(value) > 4000:
        raise ValueError("invalid_gift_secret")
    return _fernet(secret_key).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_gift(secret_key, value):
    try:
        return _fernet(secret_key).decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeError):
        raise ValueError("invalid_gift_secret")


def qr_data_url(value):
    image = qrcode.make(value)
    output = io.BytesIO()
    image.save(output, format="PNG")
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
