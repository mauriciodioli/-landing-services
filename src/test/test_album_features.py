import os
import unittest
from unittest.mock import patch

import bcrypt
from flask import Flask
from sqlalchemy import text

from controllers.album import _page_token, album_bp
from extensions import db
from models.album import Album, AlbumGift, AlbumPage
from services.album_content import normalize_external_url, normalize_music_url


class FakeStorage:
    def signed_url(self, key): return f"https://signed/{key}"


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
            page = AlbumPage(album_id=album.id, title="Página", position=1, is_visible=True)
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


if __name__ == "__main__": unittest.main()
