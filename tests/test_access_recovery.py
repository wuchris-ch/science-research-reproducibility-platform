import time
from types import SimpleNamespace
import jwt
import pytest
from sqlalchemy import insert,select,update
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from workbench.api import create_app
from workbench.auth import Auth
from workbench.database import members,runs,attempts
from workbench.runner import Worker
from workbench.schemas import RunCreate
from workbench.cli import backup,restore
from workbench.comparison import compare_fresh
from test_worker import Sandbox,queued
from test_plans import locked


def test_team_scope_including_artifacts_events_and_cache(service):
    p=locked(service);r=service.submit('alice',RunCreate(plan_id=p['id']),'one','image')
    with service.db.transaction() as c:
        c.execute(insert(members).values(workspace_id=p['workspace_id'],subject='viewer',role='viewer'))
        c.execute(insert(members).values(workspace_id=p['workspace_id'],subject='reviewer',role='reviewer'))
    service.settings.origins=['http://testserver']
    app=create_app(service.settings,Sandbox());identity={'sub':'outsider'}
    app.dependency_overrides[app.state.auth.actor]=lambda:identity['sub']
    with TestClient(app) as c:
        for path in [f'/api/runs/{r["id"]}',f'/api/plans/{p["id"]}',f'/api/runs/{r["id"]}/export',
                     f'/api/runs/{r["id"]}/artifacts/metrics.json',f'/api/workspaces/{p["workspace_id"]}/events']:
            assert c.get(path).status_code==403,path
        identity['sub']='viewer'
        assert c.get('/api/runs/'+r['id']).status_code==200
        assert c.post('/api/runs/'+r['id']+'/cancel').status_code==403
        assert c.post('/api/runs/'+r['id']+'/notes',json={'text':'review note'}).status_code==403
        identity['sub']='reviewer'
        assert c.post('/api/runs/'+r['id']+'/notes',json={'text':'review note'}).status_code==200
        assert c.post('/api/plans',json={'workspace_id':p['workspace_id'],'title':'Denied'}).status_code==403

def test_oidc_signature_issuer_audience_and_expiry(service,monkeypatch):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    settings=service.settings.model_copy(update={'oidc_issuer':'https://identity.example','oidc_audience':'research',
        'oidc_jwks_url':'https://identity.example/keys','origins':['http://testserver']})
    app=create_app(settings,Sandbox())
    monkeypatch.setattr(app.state.auth.jwks,'get_signing_key_from_jwt',lambda token:SimpleNamespace(key=key.public_key()))
    base={'sub':'alice','iss':'https://identity.example','aud':'research','iat':int(time.time()),'exp':int(time.time())+60}
    with TestClient(app) as c:
        assert c.get('/api/session').status_code==401
        for changes,status in [({},200),({'iss':'https://other.example'},401),({'aud':'other'},401),({'exp':0},401)]:
            token=jwt.encode({**base,**changes},key,algorithm='RS256')
            assert c.get('/api/me',headers={'Authorization':'Bearer '+token}).status_code==status
        bad=jwt.encode(base,'wrong-key',algorithm='HS256')
        assert c.get('/api/me',headers={'Authorization':'Bearer '+bad}).status_code==401

def test_receipt_survives_crash_after_termination(service):
    r=queued(service);sandbox=Sandbox();worker=Worker(service,sandbox,'first');run=worker.claim()
    attempt=worker.attempt(run)
    assert worker.save_attempt(run,{**attempt,'phase':'sealed','outcome':'succeeded','receipt':{'artifacts':{},'diagnostic':'sealed'}})
    with service.db.transaction() as c:c.execute(update(runs).where(runs.c.id==r['id']).values(lease_until=0))
    Worker(service,sandbox,'second').tick()
    with service.db.transaction() as c:assert service.get_run(c,'alice',r['id'])['state']=='succeeded'

def test_other_docker_host_cannot_recover_ephemeral_sandbox(service):
    queued(service);worker=Worker(service,Sandbox(),'one');worker.claim()
    with service.db.transaction() as c:c.execute(update(runs).values(lease_until=0))
    other=Worker(service,Sandbox(),'two');other.engine_id='different-runtime'
    assert other.claim() is None

def test_backup_restore_validates_blobs_and_separates_active_jobs(service,tmp_path):
    r=queued(service);blob=service.store.put(b'durable result')
    with service.db.transaction() as c:
        row=service.get_run(c,'alice',r['id']);body={**row['body'],'artifacts':{'output':{'sha256':blob,'bytes':14}}}
        c.execute(update(runs).where(runs.c.id==r['id']).values(body=body))
    snapshot=tmp_path/'backup';backup(service.settings,snapshot)
    restore(service.settings,snapshot,tmp_path/'restored')
    from workbench.cli import make_service
    from workbench.config import Settings
    target=tmp_path/'restored'
    copy=make_service(Settings(data_dir=target,database_url='sqlite:///'+str(target/'workbench.db')))
    with copy.db.transaction() as c:assert copy.get_run(c,'alice',r['id'])['state']=='failed'
    assert copy.store.read(blob)==b'durable result'
    (snapshot/'blobs'/blob).write_bytes(b'changed')
    with pytest.raises(ValueError):restore(service.settings,snapshot,tmp_path/'corrupt-restore')

def test_empty_artifacts_do_not_imply_reproducibility(service):
    assert not compare_fresh(service.store,{}, {})['same_numeric_bytes']
