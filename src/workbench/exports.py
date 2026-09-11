import io
import json
import zipfile
from pathlib import Path, PurePosixPath
from fastapi import Depends
from fastapi.responses import Response
from sqlalchemy import select
from .artifacts import canonical, digest
from .config import ROOT
from .database import plans, revisions, events
from .service import Problem


def bundle(service,run):
    files={}
    def add(name,data):files[name]=data
    add('run.json',canonical(run))
    add('plan.json',canonical(run['body']['plan']))
    add('comparison.json',canonical(run['body'].get('comparison')))
    for name,item in run['body']['artifacts'].items():add('outputs/'+name,service.store.read(item['sha256']))
    dataset=run['body']['plan']['dataset_id']
    for path in (service.settings.data_dir/'datasets'/dataset).glob('*'):
        if path.is_file():add('build/data/'+dataset+'/'+path.name,path.read_bytes())
    for relative,name in [('recipes/run.R','build/run.R'),('recipes/ADAPTATIONS.md','ADAPTATIONS.md'),
             ('environments/Dockerfile','build/Dockerfile'),('environments/entrypoint.sh','build/entrypoint.sh'),
             ('fixtures/law-samples.csv','build/law-samples.csv'),('environments/locked-packages.json','locked-packages.json'),
             ('scripts/reproduce.py','reproduce.py')]:add(name,(ROOT/relative).read_bytes())
    for suffix in ('xml','json','pdf'):
        path=service.settings.data_dir/f'sources/{dataset}.{suffix}'
        if path.exists():add('source/'+path.name,path.read_bytes())
    with service.db.transaction() as c:
        rows=c.execute(select(revisions).where(revisions.c.plan_id==run['plan_id'])).mappings()
        add('plan-history.json',canonical([dict(row) for row in rows]))
        rows=c.execute(select(events).where(events.c.run_id==run['id']).order_by(events.c.id)).mappings()
        add('run-events.json',canonical([dict(row) for row in rows]))
    add('README.txt',b'Research Workbench result bundle\n\nRun: python3 reproduce.py --verify-only\nRerun: python3 reproduce.py --context colima-research\nRequires Python 3 and Docker. Rebuild downloads only hash-pinned R package archives.\nThe script verifies bundle hashes before execution and creates a fresh isolated container.\n\nPublic GEO counts retain source attribution and access terms. Papers are CC BY.\nSee source metadata, ADAPTATIONS.md and comparison.json for limits.\nExecution success and checked-observable agreement do not establish all conclusions of the paper.\n')
    import hashlib
    manifest={'schema_version':1,'run_id':run['id'],'files':{k:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for k,v in sorted(files.items())}}
    add('manifest.json',canonical(manifest))
    result=io.BytesIO()
    with zipfile.ZipFile(result,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in files.items():z.writestr(name,data)
    return result.getvalue()

def verify_bundle(data: bytes):
    import hashlib
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or len(names)>1000:raise ValueError('Duplicate or excessive archive entries')
        total=0
        for info in z.infolist():
            p=PurePosixPath(info.filename)
            total+=info.file_size
            if p.is_absolute() or '..' in p.parts or total>100_000_000 or info.is_dir():raise ValueError('Unsafe archive')
        manifest=json.loads(z.read('manifest.json'))
        if set(names)!=set(manifest['files'])|{'manifest.json'}:raise ValueError('Unlisted or missing bundle file')
        for name,entry in manifest['files'].items():
            content=z.read(name)
            if len(content)!=entry['bytes'] or hashlib.sha256(content).hexdigest()!=entry['sha256']:raise ValueError('Bundle integrity failure')
        return manifest

def register_exports(app,service,actor):
    @app.get('/api/runs/{identity}/export')
    def export(identity:str,who=Depends(actor)):
        with service.db.transaction() as c:run=service.get_run(c,who,identity)
        if run['state'] not in ('succeeded','failed','cancelled'):raise Problem(409,'Wait for a terminal execution before exporting')
        data=bundle(service,run);verify_bundle(data)
        with service.db.transaction() as c:service.db.emit(c,run['workspace_id'],'run.exported',who,{'run_id':identity},identity)
        return Response(data,media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="research-{identity[:8]}.zip"'})
