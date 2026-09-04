import os
import unittest
from unittest.mock import patch

import bcrypt
from flask import Flask
from sqlalchemy import text

from extensions import db
from controllers.album import _page_token, album_bp
from models.album import Album, AlbumPage


class FakeStorage:
    def signed_url(self, key):
        return f"https://signed/{key}"


class AlbumTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder="../templates", static_folder="../static")
        self.app.secret_key = "test"
        self.app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", TESTING=True, SESSION_COOKIE_SECURE=False)
        db.init_app(self.app)
        self.app.register_blueprint(album_bp)
        with self.app.app_context():
            db.create_all()
            db.session.execute(text("""CREATE TABLE usuarios (
                id INTEGER PRIMARY KEY, correo_electronico VARCHAR(120) UNIQUE NOT NULL,
                password VARCHAR(128), activo BOOLEAN NOT NULL, roll VARCHAR(20), token VARCHAR(500)
            )"""))
            password = bcrypt.hashpw(b"dpia-secret", bcrypt.gensalt()).decode()
            db.session.execute(text("INSERT INTO usuarios (id, correo_electronico, password, activo, roll) VALUES (1, 'ola.soniewicka@gmail.com', :password, 1, 'regular'), (2, 'otro@example.com', :password, 1, 'regular')"), {"password": password})
            album = Album(slug="private", title="Dla Oli", active=True, owner_user_id=1)
            db.session.add(album)
            db.session.flush()
            db.session.add_all([
                AlbumPage(album_id=album.id, title="Public", position=1, is_visible=True, share_enabled=True),
                AlbumPage(album_id=album.id, title="Hidden", position=2, is_visible=False),
            ])
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login_owner(self, client):
        return client.post("/api/album/session", json={"email": "Ola.soniewicka@gmail.com", "password": "dpia-secret"})

    @patch("controllers.album.AlbumStorage", return_value=FakeStorage())
    def test_full_album_requires_owner_login(self, _):
        anonymous = self.app.test_client()
        self.assertEqual(401, anonymous.get("/api/albums/private").status_code)
        owner = self.app.test_client(); self.assertEqual(200, self.login_owner(owner).status_code)
        payload = owner.get("/api/albums/private").get_json()
        self.assertEqual(["Public"], [page["title"] for page in payload["pages"]])
        other = self.app.test_client()
        self.assertEqual(200, other.post("/api/album/session", json={"email": "otro@example.com", "password": "dpia-secret"}).status_code)
        self.assertEqual(404, other.get("/api/albums/private").status_code)

    @patch("controllers.album.AlbumStorage", return_value=FakeStorage())
    def test_shared_link_is_public_and_only_returns_visible_page(self, _):
        with self.app.app_context():
            page = AlbumPage.query.filter_by(title="Public").one()
            token = _page_token(page.album_id, page.id)
        client = self.app.test_client()
        self.assertEqual(200, client.get(f"/album/private/page/{token}").status_code)
        payload = client.get(f"/api/albums/private/shared/{token}").get_json()
        self.assertEqual(["Public"], [page["title"] for page in payload["pages"]])

    def test_shared_link_rejects_hidden_page(self):
        with self.app.app_context():
            page = AlbumPage.query.filter_by(title="Hidden").one()
            token = _page_token(page.album_id, page.id)
        self.assertEqual(404, self.app.test_client().get(f"/api/albums/private/shared/{token}").status_code)

    def test_short_link_redirects_and_cannot_be_guessed_by_page_id(self):
        with self.app.app_context():
            page = AlbumPage.query.filter_by(title="Public").one()
            page.short_slug = "K7x3mQ9Az2/catalogo-090426"
            db.session.commit()
        client = self.app.test_client()
        response = client.get("/K7x3mQ9Az2/catalogo-090426")
        self.assertEqual(302, response.status_code)
        self.assertIn("/album/private/page/", response.headers["Location"])
        self.assertEqual(404, client.get("/K7x3mQ9Az3/catalogo-090426").status_code)

    def test_enabling_share_creates_new_short_slug(self):
        with self.app.app_context():
            page = AlbumPage.query.filter_by(title="Public").one()
            page.share_enabled = False
            page.short_slug = "OldCode123/catalogo-010126"
            db.session.commit()
            page_id = page.id
        pin_hash = bcrypt.hashpw(b"4409", bcrypt.gensalt()).decode()
        with patch.dict(os.environ, {"ALBUM_ADMIN_PIN_HASH": pin_hash, "ALBUM_PUBLIC_BASE_URL": "https://ola.dpia.site"}):
            client = self.app.test_client(); login = self.admin_login(client)
            response = client.patch(f"/api/albums/private/pages/{page_id}/share", json={"enabled": True}, headers={"X-CSRF-Token": login.get_json()["csrf_token"]})
        self.assertEqual(200, response.status_code)
        self.assertRegex(response.get_json()["share_url"], r"^https://ola\.dpia\.site/[A-Za-z0-9]{10}/public-\d{6}$")
        self.assertNotIn("OldCode123", response.get_json()["share_url"])

    def test_login_creates_album_once_and_restores_it(self):
        client = self.app.test_client()
        first = client.post("/api/album/session", json={"email": "otro@example.com", "password": "dpia-secret"})
        self.assertEqual(200, first.status_code)
        first_url = first.get_json()["album_url"]
        client.post("/api/album/session/logout")
        second = client.post("/api/album/session", json={"email": "otro@example.com", "password": "dpia-secret"})
        self.assertEqual(first_url, second.get_json()["album_url"])
        with self.app.app_context():
            self.assertEqual(1, Album.query.filter_by(owner_user_id=2).count())

    def test_logout_blocks_album_again(self):
        client = self.app.test_client(); self.login_owner(client)
        self.assertEqual(200, client.post("/api/album/session/logout").status_code)
        self.assertEqual(302, client.get("/album/private").status_code)

    def test_admin_requires_owner_and_pin(self):
        client = self.app.test_client()
        self.assertEqual(401, client.post("/api/albums/private/pages").status_code)
        self.login_owner(client)
        self.assertEqual(401, client.post("/api/albums/private/pages").status_code)

    def admin_login(self, client):
        self.login_owner(client)
        return client.post("/api/albums/private/admin/login", json={"pin": "4409"})

    def test_login_with_hash(self):
        with patch.dict(os.environ, {"ALBUM_ADMIN_PIN_HASH": bcrypt.hashpw(b"4409", bcrypt.gensalt()).decode()}):
            self.assertEqual(200, self.admin_login(self.app.test_client()).status_code)

    def test_admin_can_change_own_pin(self):
        initial_hash = bcrypt.hashpw(b"4409", bcrypt.gensalt()).decode()
        with patch.dict(os.environ, {"ALBUM_ADMIN_PIN_HASH": initial_hash}):
            client = self.app.test_client(); login = self.admin_login(client)
            response = client.post("/api/albums/private/admin/pin", json={"current_pin": "4409", "new_pin": "9876"}, headers={"X-CSRF-Token": login.get_json()["csrf_token"]})
            self.assertEqual(200, response.status_code)
            other = self.app.test_client(); self.login_owner(other)
            self.assertEqual(401, other.post("/api/albums/private/admin/login", json={"pin": "4409"}).status_code)
            self.assertEqual(200, other.post("/api/albums/private/admin/login", json={"pin": "9876"}).status_code)

    def test_admin_can_change_album_title(self):
        with patch.dict(os.environ, {"ALBUM_ADMIN_PIN_HASH": bcrypt.hashpw(b"4409", bcrypt.gensalt()).decode()}):
            client = self.app.test_client(); login = self.admin_login(client)
            response = client.patch("/api/albums/private/admin/title", json={"title": "Nuestros momentos"}, headers={"X-CSRF-Token": login.get_json()["csrf_token"]})
            self.assertEqual(200, response.status_code)
            self.assertEqual("Nuestros momentos", response.get_json()["title"])


if __name__ == "__main__":
    unittest.main()
