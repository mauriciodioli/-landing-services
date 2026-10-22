import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from flask import Flask, render_template
from sqlalchemy import text, select, func
from sqlalchemy.exc import SQLAlchemyError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from extensions import db
from controllers.web_leads_admin import web_leads_admin
from models.web_lead import Lead

class WebLeadsAdminTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        root=Path(__file__).resolve().parents[1]/'src'
        self.app=Flask(__name__,template_folder=str(root/'templates'),static_folder=str(root/'static'))
        self.app.config.update(TESTING=True,SECRET_KEY='test',SQLALCHEMY_DATABASE_URI='sqlite:///'+self.temp.name+'/db.sqlite')
        db.init_app(self.app)
        self.app.register_blueprint(web_leads_admin)
        with self.app.app_context():
            db.create_all()
            with db.engine.begin() as conn:
                conn.execute(text('CREATE TABLE usuarios (id INTEGER PRIMARY KEY, correo_electronico VARCHAR(254), activo INTEGER, roll VARCHAR(40), token VARCHAR(100))'))
                for i,(role,active) in enumerate([('ADMINISTRADOR',1),('MODERADOR',1),('USUARIO',1),('AVANZADO',1),('ADMINISTRADOR',0)],1):
                    conn.execute(text('INSERT INTO usuarios (id,activo,roll,token) VALUES (:id,:active,:role,:token)'),dict(id=i,active=active,role=role,token='token-'+str(i)))
            self.engine=db.engine
        self.client=self.app.test_client()

    def tearDown(self):
        with self.app.app_context():db.session.remove()
        self.engine.dispose();self.temp.cleanup()

    def call(self,method,path='/admin/api/web-leads',token='token-1',**kwargs):
        headers={'Authorization':'Bearer '+token} if token else {}
        return self.client.open(path,method=method,headers=headers,**kwargs)

    def data(self,**changes):
        data=dict(name='Example Contact',email='contact@example.com',business_type='retail',solution_type='web',features='Customer portal',description='A website to manage orders and customer enquiries.',online_payments='yes',ai='unsure',integration='no',integration_details='',lang='es',privacy_consent=True)
        data.update(changes);return data

    def test_roles_enforced_for_every_operation(self):
        paths=[('GET','/admin/api/web-leads'),('GET','/admin/api/web-leads/missing'),('POST','/admin/api/web-leads'),('PATCH','/admin/api/web-leads/missing'),('DELETE','/admin/api/web-leads/missing')]
        for method,path in paths:
            self.assertEqual(self.call(method,path,token=None).status_code,401)
            self.assertEqual(self.call(method,path,token='invalid').status_code,401)
            for token in ['token-3','token-4','token-5']:
                self.assertEqual(self.call(method,path,token=token).status_code,403)
        for token in ['token-1','token-2']:
            self.assertEqual(self.call('GET',token=token).status_code,200)
        self.assertFalse(self.call('GET','/admin/api/access',token='token-4').json['permissions']['web_leads'])

    def test_crud_search_and_pagination(self):
        r=self.call('POST',json=self.data())
        self.assertEqual(r.status_code,201);identifier=r.json['id']
        self.assertEqual(self.call('GET','/admin/api/web-leads/'+identifier,token='token-2').json['item']['email'],'contact@example.com')
        self.assertEqual(self.call('PATCH','/admin/api/web-leads/'+identifier,json={'name':'Updated Contact'}).status_code,200)
        self.assertEqual(self.call('GET','/admin/api/web-leads?q=Updated').json['total'],1)
        self.assertEqual(self.call('GET','/admin/api/web-leads?q=%25').json['total'],0)
        self.assertEqual(self.call('GET','/admin/api/web-leads?business=industry').json['total'],0)
        self.assertEqual(self.call('GET','/admin/api/web-leads?page=2&per_page=1').json['items'],[])
        self.assertEqual(self.call('GET','/admin/api/web-leads?page=oops').status_code,400)
        self.assertEqual(self.call('DELETE','/admin/api/web-leads/'+identifier,token='token-2').status_code,200)
        self.assertEqual(self.call('GET','/admin/api/web-leads/'+identifier).status_code,404)

    def test_validation_and_immutable_fields(self):
        self.assertEqual(self.call('POST',json=self.data(email='bad')).status_code,400)
        self.assertEqual(self.call('POST',json=self.data(privacy_consent=False)).status_code,400)
        identifier=self.call('POST',json=self.data()).json['id']
        self.assertEqual(self.call('PATCH','/admin/api/web-leads/'+identifier,json={'id':'other'}).status_code,400)
        self.assertEqual(self.call('PATCH','/admin/api/web-leads/'+identifier,json={'description':'short'}).status_code,400)
        self.assertEqual(self.call('GET','/admin/api/web-leads/'+identifier).json['item']['description'],self.data()['description'])
        self.assertEqual(self.call('POST',data='x'*33000,content_type='application/json').status_code,413)

    def test_commit_failure_rolls_back(self):
        with self.app.app_context():
            original_commit=db.session.commit
            def fail_lead_commit():
                if any(isinstance(row,Lead) for row in db.session.new):raise SQLAlchemyError('failure')
                original_commit()
            with patch.object(db.session,'commit',side_effect=fail_lead_commit):
                self.assertEqual(self.call('POST',json=self.data()).status_code,503)
            self.assertFalse(db.session.registry.has())
            self.assertEqual(db.session.scalar(select(func.count()).select_from(Lead)),0)

    def test_separate_pages_and_navigation(self):
        for path in ['/admin','/admin/solicitudes-web']:
            r=self.client.get(path);self.assertEqual(r.status_code,200)
            self.assertIn(b'/admin/participantes',r.data);self.assertIn(b'/admin/solicitudes-web',r.data)
            self.assertEqual(r.headers['Cache-Control'],'no-store')
        with self.app.test_request_context('/admin/participantes'):
            html=render_template('participants/index.html')
            self.assertIn('/admin/solicitudes-web',html)
            self.assertIn('participantsBody',html)
        with self.app.app_context():self.assertEqual(db.session.scalar(select(func.count()).select_from(Lead)),0)

if __name__=='__main__':unittest.main()
