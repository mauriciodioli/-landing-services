import io
import os
import unittest
from unittest.mock import patch

import bcrypt
from PIL import Image
from flask import Flask
from sqlalchemy import text

from controllers.album import _page_token, album_bp
from extensions import db
from models.album import Album, AlbumGift, AlbumPage
from services.album_content import normalize_external_url, normalize_music_url


class FakeStorage:
    def signed_url(self, key): return f"https://signed/{key}"
    def upload(self, key, stream, mime_type): self.uploaded = getattr(self, "uploaded", []) + [key]
    def delete(self, key): self.deleted = getattr(self, "deleted", []) + [key]


class AlbumFeatureTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder="../templates", static_folder="../static")
        self.app.secret_key = "feature-test-secret"
        self.app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", TESTING=True, SESSION_COOKIE_SECURE=False)
        db.init_app(self.app); self.app.register_blueprint(album_bp)
        self.env = patch.dict(os.environ, {"ALBUM_ADMIN_PIN_HASH": bcrypt.hashpw(b"4409", bcrypt.gensalt()).decode()})
        self.env.start()
        with self.app.app_context():
            db.create_all()
            db.session.execute(text("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, correo_electronico VARCHAR(120), password VARCHAR(128), activo BOOLEAN, roll VARCHAR(20))"))
            password = bcrypt.hashpw(b"dpia-secret", bcrypt.gensalt()).decode()
            db.session.execute(text("INSERT INTO usuarios VALUES (1, 'owner@example.com', :password, 1, 'regular')"), {"password": password})
            album = Album(owner_user_id=1, slug="features", title="Recuerdos", active=True, music_url="https://open.spotify.com/track/abc")
            db.session.add(album); db.session.flush()
            page = AlbumPage(album_id=album.id, title="Página", position=1, is_visible=True, share_enabled=True)
            db.session.add(page); db.session.commit()
            self.page_id = page.id; self.album_id = album.id
        self.client = self.app.test_client()
        self.client.post("/api/album/session", json={"email":"owner@example.com", "password":"dpia-secret"})
        login = self.client.post("/api/albums/features/admin/login", json={"pin":"4409"})
        self.csrf = login.get_json()["csrf_token"]
        self.headers = {"X-CSRF-Token": self.csrf, "Content-Type":"application/json"}

    def tearDown(self):
        self.env.stop()
        with self.app.app_context(): db.session.remove(); db.drop_all()

    def test_provider_validation_and_private_network_rejection(self):
        youtube = normalize_external_url("https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual("youtube", youtube["provider"])
        self.assertEqual("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ", youtube["embed_url"])
        with self.assertRaises(ValueError): normalize_external_url("http://127.0.0.1/private.jpg")
        with self.assertRaises(ValueError): normalize_music_url("https://example.com/not-music")

    def test_page_music_and_external_media(self):
        music = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        response = self.client.patch(f"/api/albums/features/pages/{self.page_id}", headers=self.headers, json={"music_url":music})
        self.assertEqual(200, response.status_code)
        external = self.client.post(f"/api/albums/features/pages/{self.page_id}/external-media", headers=self.headers, json={"url":"https://vimeo.com/123456", "title":"Video"})
        self.assertEqual(201, external.status_code)
        self.assertEqual("vimeo", external.get_json()["item"]["provider"])
        with self.app.app_context():
            page = db.session.get(AlbumPage, self.page_id)
            self.assertEqual(music, page.music_url)

    @patch("controllers.album.AlbumStorage", return_value=FakeStorage())
    def test_preview_works_for_hidden_page_and_share_can_be_revoked(self, _):
        with self.app.app_context():
            page = db.session.get(AlbumPage, self.page_id)
            page.is_visible = False; db.session.commit()
        admin = self.client.get("/api/albums/features/admin").get_json()
        page_data = admin["pages"][0]
        old_url = page_data["share_url"]
        preview_path = page_data["preview_url"].replace("http://localhost", "")
        self.assertEqual(200, self.client.get(preview_path).status_code)
        old_path = old_url.replace("http://localhost", "")
        self.assertEqual(404, self.app.test_client().get(old_path).status_code)
        with self.app.app_context():
            page = db.session.get(AlbumPage, self.page_id)
            page.is_visible = True; db.session.commit()
        revoked = self.client.patch(f"/api/albums/features/pages/{self.page_id}/share", headers=self.headers, json={"enabled":False})
        self.assertEqual(200, revoked.status_code)
        self.assertEqual(404, self.app.test_client().get(old_path).status_code)
        activated = self.client.patch(f"/api/albums/features/pages/{self.page_id}/share", headers=self.headers, json={"enabled":True}).get_json()
        self.assertNotEqual(old_url, activated["share_url"])
        new_path = activated["share_url"].replace("http://localhost", "")
        self.assertEqual(200, self.app.test_client().get(new_path, follow_redirects=True).status_code)

    @patch("controllers.album.AlbumStorage", return_value=FakeStorage())
    def test_gift_secret_is_hidden_and_reveal_requires_pin(self, _):
        created = self.client.post(f"/api/albums/features/pages/{self.page_id}/gifts", headers=self.headers, json={"title":"Tu regalo", "secret":"https://store.example/redeem/SECRET", "pin":"1234"})
        self.assertEqual(201, created.status_code)
        gift = created.get_json()["gift"]
        self.assertNotIn("secret", gift)
        with self.app.app_context(): page_token = _page_token(self.album_id, self.page_id)
        public = self.app.test_client()
        payload = public.get(f"/api/albums/features/shared/{page_token}").get_json()
        self.assertNotIn("secret", payload["pages"][0]["gifts"][0])
        reveal_url = f"/api/albums/features/shared/{page_token}/gifts/{gift['token']}/reveal"
        self.assertEqual(401, public.post(reveal_url, json={"pin":"bad"}).status_code)
        revealed = public.post(reveal_url, json={"pin":"1234"})
        self.assertEqual(200, revealed.status_code)
        self.assertEqual("https://store.example/redeem/SECRET", revealed.get_json()["secret"])
        self.assertTrue(revealed.get_json()["qr_data_url"].startswith("data:image/png;base64,"))
        with self.app.app_context():
            stored = AlbumGift.query.one()
            self.assertNotIn("SECRET", stored.secret_encrypted)
            self.assertIsNotNone(stored.opened_at)

    def test_revoked_gift_cannot_be_revealed(self):
        created = self.client.post(f"/api/albums/features/pages/{self.page_id}/gifts", headers=self.headers, json={"title":"Regalo", "secret":"CODE-123"}).get_json()["gift"]
        self.client.patch(f"/api/albums/features/gifts/{created['id']}", headers=self.headers, json={"status":"revoked"})
        with self.app.app_context(): page_token = _page_token(self.album_id, self.page_id)
        response = self.app.test_client().post(f"/api/albums/features/shared/{page_token}/gifts/{created['token']}/reveal", json={})
        self.assertEqual(410, response.status_code)


    def test_temporary_contributions_require_moderation(self):
        enabled = self.client.post(f"/api/albums/features/pages/{self.page_id}/contributions", headers=self.headers, json={"enabled":True,"hours":24})
        self.assertEqual(200, enabled.status_code)
        contribution_path = enabled.get_json()["contribution_url"].replace("http://localhost", "")
        token = contribution_path.rsplit("/", 1)[-1]
        public = self.app.test_client()
        self.assertEqual(200, public.get(contribution_path).status_code)
        image = Image.new("RGB", (4, 4), "red"); payload = io.BytesIO(); image.save(payload, "PNG"); payload.seek(0)
        storage = FakeStorage()
        with patch("controllers.album.AlbumStorage", return_value=storage):
            uploaded = public.post(f"/api/albums/features/contribute/{token}/media", data={"files":(payload,"guest.png"),"contributor_name":"Ana"}, content_type="multipart/form-data")
            self.assertEqual(201, uploaded.status_code)
            media_id = uploaded.get_json()["ids"][0]
            admin_page = self.client.get("/api/albums/features/admin").get_json()["pages"][0]
            self.assertEqual([], admin_page["media"]); self.assertEqual("Ana", admin_page["pending_contributions"][0]["contributor_name"] )
            approved = self.client.patch(f"/api/albums/features/contributions/{media_id}", headers=self.headers, json={"action":"approve"})
            self.assertEqual(200, approved.status_code)
            shared = public.get(f"/api/albums/features/contribute/{token}").get_json()["pages"][0]
            self.assertEqual(1, len(shared["media"])); self.assertNotIn("pending_contributions", shared)
            second = Image.new("RGB", (4, 4), "blue"); second_payload = io.BytesIO(); second.save(second_payload, "PNG"); second_payload.seek(0)
            second_upload = public.post(f"/api/albums/features/contribute/{token}/media", data={"files":(second_payload,"second.png")}, content_type="multipart/form-data").get_json()
            rejected = self.client.patch(f"/api/albums/features/contributions/{second_upload['ids'][0]}", headers=self.headers, json={"action":"reject"})
            self.assertEqual(200, rejected.status_code); self.assertTrue(storage.deleted)

    def test_contribution_link_can_expire_and_be_revoked(self):
        enabled = self.client.post(f"/api/albums/features/pages/{self.page_id}/contributions", headers=self.headers, json={"enabled":True,"hours":1}).get_json()
        path = enabled["contribution_url"].replace("http://localhost", "")
        self.assertEqual(200, self.app.test_client().get(path).status_code)
        revoked = self.client.post(f"/api/albums/features/pages/{self.page_id}/contributions", headers=self.headers, json={"enabled":False})
        self.assertEqual(200, revoked.status_code)
        self.assertEqual(404, self.app.test_client().get(path).status_code)


if __name__ == "__main__": unittest.main()
