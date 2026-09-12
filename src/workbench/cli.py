"""Local lifecycle and operational commands for the research workbench."""
import argparse
import json
import logging
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path
from .config import ROOT, Settings
from .database import Database
from .artifacts import ArtifactStore
from .service import Service
from .runner import Docker, Worker
from .fixtures import prepare, fetch


def make_service(settings):
    settings.initialize();db=Database(settings.database_url);db.migrate()
    return Service(db,settings,ArtifactStore(settings.data_dir/'blobs'))

def prepare_annotation(settings):
    import tarfile
    ledger=ROOT/'fixtures/chen-annotation.json'
    if not ledger.exists():raise RuntimeError('Historical annotation manifest is not available')
    entry=json.loads(ledger.read_text());archive=settings.data_dir/'sources/chen-annotation.tar.gz'
    fetch(entry['url'],archive,entry['sha256'])
    with tarfile.open(archive) as tf:
        member=tf.getmember('org.Mm.eg.db/inst/extdata/org.Mm.eg.sqlite')
        if not member.isfile() or member.size>300_000_000:raise ValueError('Invalid annotation database')
        dbpath=settings.data_dir/'sources/chen-annotation.sqlite'
        dbpath.write_bytes(tf.extractfile(member).read())
    with sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True) as c:
        rows=c.execute('SELECT genes.gene_id, gene_info.symbol FROM genes JOIN gene_info USING (_id) ORDER BY genes.gene_id').fetchall()
    import csv
    with (settings.data_dir/'datasets/chen2016/symbols.tsv').open('w') as f:
        writer=csv.writer(f,delimiter='\t',lineterminator='\n');writer.writerow(['gene_id','symbol']);writer.writerows(rows)
    return len(rows)

def build(settings):
    context=settings.data_dir/'build';context.mkdir(exist_ok=True)
    packages=context/'packages';packages.mkdir(exist_ok=True)
    for entry in json.loads((ROOT/'environments/locked-packages.json').read_text()):
        fetch(entry['url'],packages/entry['file'],entry['sha256'],cap=20_000_000)
    shutil.copytree(settings.data_dir/'datasets',context/'data',dirs_exist_ok=True)
    for src,name in [('recipes/run.R','run.R'),('environments/Dockerfile','Dockerfile'),
                     ('environments/entrypoint.sh','entrypoint.sh'),('fixtures/law-samples.csv','law-samples.csv')]:
        shutil.copyfile(ROOT/src,context/name)
    shutil.copyfile(ROOT/'environments/locked-packages.json',context/'locked-packages.json')
    docker=Docker(settings)
    subprocess.run(docker.prefix+['build','--platform','linux/amd64','-t',settings.image,str(context)],check=True)
    print('Sealed execution image:',docker.image_id())

def assets(settings):
    for entry in json.loads((ROOT/'fixtures/paper-assets.json').read_text()):
        fetch(entry['url'],settings.data_dir/'sources'/entry['file'],entry['sha256'],cap=10_000_000)
    geometry=json.loads((ROOT/'fixtures/law-geometry.json').read_text())
    path=settings.data_dir/'sources/law2018.json'
    source=json.loads(path.read_text());source['geometry']=geometry;source['geometry_status']='Verified on publisher PDF, page 8';path.write_text(json.dumps(source))

def backup(settings,target:Path):
    if not settings.database_url.startswith('sqlite:///'):raise RuntimeError('Use pg_dump plus an artifact snapshot for PostgreSQL; see operations guide')
    if target.exists():raise ValueError('Backup destination already exists')
    target.mkdir(parents=True,mode=0o700)
    original=settings.database_url.removeprefix('sqlite:///')
    with sqlite3.connect(original) as source, sqlite3.connect(target/'workbench.db') as dest:source.backup(dest)
    # Append-only blobs permit a DB snapshot first, followed by copying referenced blobs.
    shutil.copytree(settings.data_dir/'blobs',target/'blobs')
    shutil.copytree(settings.data_dir/'sources',target/'sources')
    shutil.copytree(settings.data_dir/'datasets',target/'datasets')
    (target/'README.txt').write_text('Consistent metadata snapshot plus immutable artifacts. Sessions are intentionally excluded.\nRestore into a new directory using workbench restore. In-flight jobs must be reconciled.\n')
    print(target)

def restore(settings,source:Path,target:Path):
    if target.exists():raise ValueError('Restore requires a new directory')
    shutil.copytree(source,target)
    dest=Settings(data_dir=target,database_url='sqlite:///'+str(target/'workbench.db'))
    service=make_service(dest)
    from sqlalchemy import select,update
    from .database import runs
    with service.db.transaction() as c:
        for r in c.execute(select(runs)).mappings():
            for a in r['body'].get('artifacts',{}).values():service.store.read(a['sha256'])
        # A restored install must not assume ownership of the source installation's active containers.
        c.execute(update(runs).where(runs.c.state.in_(['running','queued','cancel_requested'])).values(
            state='failed',owner=None,lease_until=0))
    print('Verified restored artifacts. Active jobs marked failed; submit fresh runs after review.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('setup');sub.add_parser('build');sub.add_parser('doctor')
    serve=sub.add_parser('serve');serve.add_argument('--host',default='127.0.0.1');serve.add_argument('--port',type=int,default=8317)
    worker=sub.add_parser('worker');worker.add_argument('--once',action='store_true')
    b=sub.add_parser('backup');b.add_argument('destination',type=Path)
    r=sub.add_parser('restore');r.add_argument('source',type=Path);r.add_argument('destination',type=Path)
    e=sub.add_parser('export');e.add_argument('run_id');e.add_argument('destination',type=Path)
    v=sub.add_parser('verify-bundle');v.add_argument('path',type=Path)
    args=parser.parse_args();settings=Settings();settings.initialize()
    if args.command=='setup':
        prepare(settings);prepare_annotation(settings);assets(settings);build(settings);make_service(settings)
        print('Setup complete. Start workbench serve and workbench worker in separate terminals.')
    elif args.command=='build':build(settings)
    elif args.command=='doctor':
        result={'database':settings.database_url.split(':',1)[0],'data_dir':str(settings.data_dir),'sources':{k:(settings.data_dir/f'sources/{k}.json').exists() for k in ('law2018','chen2016')}}
        try:result['image_id']=Docker(settings).image_id()
        except Exception as ex:result['runtime_error']=str(ex)
        print(json.dumps(result,indent=2))
    elif args.command=='serve':
        if args.host not in ('127.0.0.1','localhost','::1') and not settings.oidc_issuer:
            parser.error('Non-loopback serving requires configured OIDC')
        import uvicorn
        from .api import create_app
        uvicorn.run(create_app(settings),host=args.host,port=args.port)
    elif args.command=='worker':
        worker=Worker(make_service(settings))
        while True:
            try:worker.tick()
            except KeyboardInterrupt:return
            except Exception:logging.exception('Worker operation failed; durable state retained for reconciliation')
            if args.once:return
            time.sleep(1)
    elif args.command=='backup':backup(settings,args.destination.resolve())
    elif args.command=='restore':restore(settings,args.source.resolve(),args.destination.resolve())
    elif args.command=='export':
        from .exports import bundle,verify_bundle
        service=make_service(settings)
        with service.db.transaction() as c:run=service.get_run(c,'local',args.run_id)
        data=bundle(service,run);verify_bundle(data);args.destination.write_bytes(data);print(args.destination.resolve())
    elif args.command=='verify-bundle':
        from .exports import verify_bundle
        print(json.dumps(verify_bundle(args.path.read_bytes()),indent=2))

if __name__=='__main__':main()
