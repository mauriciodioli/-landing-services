import os
import unittest
from unittest.mock import patch
from flask import Flask
from extensions import db
from controllers.album import album_bp
from models.album import Album, AlbumPage

class FakeStorage:
    def signed_url(self,key): return f"https://signed/{key}"

class AlbumTest(unittest.TestCase):
    def setUp(self):
        self.app=Flask(__name__);self.app.secret_key="test";self.app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://",TESTING=True,SESSION_COOKIE_SECURE=False)
        db.init_app(self.app);self.app.register_blueprint(album_bp)
        with self.app.app_context():
            db.create_all();a=Album(slug="private",title="Dla Oli",active=True);db.session.add(a);db.session.flush();db.session.add_all([AlbumPage(album_id=a.id,title="Public",position=1,is_visible=True),AlbumPage(album_id=a.id,title="Hidden",position=2,is_visible=False)]);db.session.commit()
    def tearDown(self):
        with self.app.app_context():db.session.remove();db.drop_all()
    @patch("controllers.album.AlbumStorage",return_value=FakeStorage())
    def test_public_only_visible(self,_):
        payload=self.app.test_client().get("/api/albums/private").get_json();self.assertEqual(["Public"],[p["title"] for p in payload["pages"]])
    def test_admin_requires_auth(self):self.assertEqual(401,self.app.test_client().post("/api/albums/private/pages").status_code)
    def test_login_with_hash(self):
        import bcrypt
        with patch.dict(os.environ,{"ALBUM_ADMIN_PIN_HASH":bcrypt.hashpw(b"4409",bcrypt.gensalt()).decode()}):self.assertEqual(200,self.app.test_client().post("/api/albums/private/admin/login",json={"pin":"4409"}).status_code)

if __name__=="__main__":unittest.main()
