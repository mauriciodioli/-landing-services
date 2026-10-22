import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from flask import Flask
from sqlalchemy import create_engine
from controllers.web_landing import web_landing
from services.web_landing.models import Base, Lead

def create_app(config):
    root=Path(__file__).resolve().parents[1] / 'src'
    app=Flask(__name__,template_folder=str(root/'templates'),static_folder=str(root/'static'))
    app.config.update(SECRET_KEY='test-secret',TESTING=True)
    app.config.update(config)
    engine=create_engine(config['DATABASE_URL'])
    Base.metadata.create_all(engine)
    app.extensions['web_landing_engine']=engine
    app.register_blueprint(web_landing)
    return app

HOST = 'https://web.dpia.site'

class LandingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app({'TESTING': True, 'DATABASE_URL': 'sqlite:///'+self.temp.name+'/leads.sqlite'})
        self.client = self.app.test_client()
        self.client.get('/desarrollo-web/es/', base_url=HOST)
        with self.client.session_transaction(base_url=HOST) as session:
            self.csrf = session['web_csrf']

    def tearDown(self):
        self.app.extensions['web_landing_engine'].dispose()
        self.temp.cleanup()

    def payload(self, **changes):
        value = dict(name='Test Visitor', email='visitor@example.com', lang='es', business_type='retail', solution_type='web', features='Orders and customer accounts', online_payments='yes', ai='unsure', integration='no', description='We need a portal to manage customer orders.', privacy_consent=True, csrf_token=self.csrf, website='')
        value.update(changes)
        return value

    def post(self, **changes):
        return self.client.post('/desarrollo-web/api/leads', base_url=HOST, json=self.payload(**changes))

    def count(self):
        with self.app.extensions['web_landing_engine'].connect() as conn:
            return conn.execute(select(func.count()).select_from(Lead)).scalar_one()

    def test_multilingual_pages_and_seo(self):
        for lang in ('es', 'en', 'it'):
            r = self.client.get('/desarrollo-web/'+lang+'/', base_url=HOST)
            self.assertEqual(r.status_code, 200)
            self.assertIn(('lang="'+lang+'"').encode(), r.data)
            self.assertIn(b'https://web.dpia.site', r.data)
            self.assertIn('Content-Security-Policy', r.headers)
            self.assertEqual(self.client.get('/desarrollo-web/'+lang+'/privacy/', base_url=HOST).status_code, 200)
        self.assertEqual(self.client.get('/desarrollo-web/fr/', base_url=HOST).status_code, 404)
        self.assertEqual(self.client.get('/desarrollo-web', base_url=HOST).status_code, 302)
        self.assertEqual(self.client.get('/desarrollo-web/sitemap.xml', base_url=HOST).status_code, 200)

    def test_direct_route_works_on_current_app_hosts(self):
        for host in ('https://dpia.site','https://solutions.dpia.site','https://example.com'):
            self.assertEqual(self.client.get('/desarrollo-web/es/',base_url=host).status_code,200)

    def test_registration_is_persistent(self):
        r=self.post()
        self.assertEqual(r.status_code,201)
        self.assertTrue(r.json['ok'])
        self.assertEqual(self.count(),1)
        with self.app.extensions['web_landing_engine'].connect() as conn:
            row=conn.execute(select(Lead)).first()
            self.assertEqual(row.email,'visitor@example.com')

    def test_invalid_inputs_never_saved(self):
        for changes in ({'email':'not-an-email'},{'description':'too short'},{'business_type':'unknown'},{'privacy_consent':False},{'online_payments':True},{'lang':[]},{'features':[]},{'name':'x'*121},{'website':'spam.example'}):
            self.assertEqual(self.post(**changes).status_code,400,changes)
        self.assertEqual(self.count(),0)

    def test_csrf_and_origin(self):
        self.assertEqual(self.post(csrf_token='wrong').status_code,403)
        r=self.client.post('/desarrollo-web/api/leads',base_url=HOST,json=self.payload(),headers={'Origin':'https://foreign.example'})
        self.assertEqual(r.status_code,403)
        self.assertEqual(self.count(),0)

    def test_storage_failure_cannot_report_success(self):
        with patch('controllers.web_landing.register',side_effect=SQLAlchemyError('unavailable')):
            r=self.post()
        self.assertEqual(r.status_code,503)
        self.assertFalse(r.json['ok'])
        self.assertEqual(self.count(),0)

    def test_rate_limit_shared_between_app_instances(self):
        for _ in range(15):self.assertEqual(self.post().status_code,201)
        self.assertEqual(self.post().status_code,429)
        second=create_app({'TESTING':True,'DATABASE_URL':self.app.config['DATABASE_URL']})
        c=second.test_client();c.get('/desarrollo-web/es/',base_url=HOST)
        with c.session_transaction(base_url=HOST) as session:token=session['web_csrf']
        self.assertEqual(c.post('/desarrollo-web/api/leads',base_url=HOST,json=self.payload(csrf_token=token)).status_code,429)
        second.extensions['web_landing_engine'].dispose()

    def test_https_origin_behind_existing_proxy(self):
        r=self.client.post('/desarrollo-web/api/leads',base_url='http://web.dpia.site',json=self.payload(),headers={'Origin':HOST})
        self.assertEqual(r.status_code,201)

    def test_assets_and_video(self):
        for asset in ('styles.css','app.js','logo.png'):
            with self.client.get('/static/web/'+asset,base_url=HOST) as response:
                self.assertEqual(response.status_code,200)
        r=self.client.get('/static/web/presentation.mp4',base_url=HOST,headers={'Range':'bytes=0-1023'})
        self.assertEqual(r.status_code,206)
        self.assertEqual(len(r.data),1024)
        r.close()

    def test_size_and_json_validation(self):
        self.assertEqual(self.client.post('/desarrollo-web/api/leads',base_url=HOST,data='x'*33000,content_type='application/json').status_code,413)
        self.assertEqual(self.client.post('/desarrollo-web/api/leads',base_url=HOST,json=[]).status_code,400)

if __name__=='__main__':unittest.main()
