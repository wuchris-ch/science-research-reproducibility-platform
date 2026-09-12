import pytest
from fastapi.testclient import TestClient
from workbench.api import create_app
from workbench.service import REQUIRED_REVIEW

class Runtime:
    def image_id(self):return 'image'

@pytest.fixture
def client(service):
    service.settings.origins=['http://testserver']
    app=create_app(service.settings,Runtime())
    with TestClient(app) as c:
        token=c.get('/api/session').json()['csrf']
        c.headers['x-csrf-token']=token
        yield c

def test_api_review_run_export_boundaries(client):
    w=client.post('/api/workspaces',json={'name':'Lab'}).json()['id']
    p=client.post('/api/plans',json={'workspace_id':w,'title':'Figure 1'}).json()
    assert client.post('/api/runs',json={'plan_id':p['id']},headers={'Idempotency-Key':'x'}).status_code==409
    assert client.post(f"/api/plans/{p['id']}/lock",json={'expected_revision':1,'reviewed_fields':REQUIRED_REVIEW}).status_code==200
    r=client.post('/api/runs',json={'plan_id':p['id']},headers={'Idempotency-Key':'x'}).json()
    assert r['state']=='queued'
    assert client.get(f"/api/runs/{r['id']}/export").status_code==409
    assert client.post(f"/api/runs/{r['id']}/cancel").json()['state']=='cancelled'
    assert client.get(f'/api/workspaces/{w}/events').json()[-1]['kind']=='run.cancelled'

def test_csrf_host_and_origin(client):
    assert client.post('/api/workspaces',json={'name':'Lab'},headers={'x-csrf-token':''}).status_code==403
    assert client.get('/api/session',headers={'origin':'https://evil.example'}).status_code==403
    assert client.get('/api/session',headers={'host':'attacker.example'}).status_code==403
    assert client.get('/api/workspaces',headers={'sec-fetch-site':'cross-site'}).status_code==403

def test_last_owner_and_source_validation(client):
    w=client.post('/api/workspaces',json={'name':'Lab'}).json()['id']
    assert client.put(f'/api/workspaces/{w}/members',json={'subject':'local','role':'viewer'}).status_code==409
    assert client.post(f'/api/workspaces/{w}/sources',files={'file':('x.html',b'<script>alert(1)</script>')}).status_code==422
    assert client.get('/api/workspaces/unknown').status_code==403

def test_session_reuse_does_not_invalidate_another_tab(client):
    first=client.get('/api/session').json()['csrf']
    second=client.get('/api/session').json()['csrf']
    assert first==second
    assert client.post('/api/workspaces',json={'name':'Another tab'},headers={'x-csrf-token':first}).status_code==200

def test_review_survives_workspace_poll(client):
    from sqlalchemy import update
    from workbench.database import runs
    w=client.post('/api/workspaces',json={'name':'Review lab'}).json()['id']
    p=client.post('/api/plans',json={'workspace_id':w,'title':'Figure'}).json()
    client.post('/api/plans/'+p['id']+'/lock',json={'expected_revision':1,'reviewed_fields':REQUIRED_REVIEW})
    r=client.post('/api/runs',json={'plan_id':p['id']},headers={'Idempotency-Key':'review'}).json()
    with client.app.state.service.db.transaction() as c:c.execute(update(runs).where(runs.c.id==r['id']).values(state='succeeded'))
    assert client.post('/api/runs/'+r['id']+'/reviews',json={'status':'disputed','note':'A documented discrepancy'}).status_code==200
    assert client.get('/api/workspaces/'+w).json()['runs'][0]['reviews'][0]['body']['status']=='disputed'
