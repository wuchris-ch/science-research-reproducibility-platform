"""Exercise all curated recipes and a fresh reference rerun against real Docker."""
import json
import time
from pathlib import Path
from sqlalchemy import select
from workbench.cli import make_service
from workbench.config import Settings,ROOT
from workbench.database import workspaces,plans,runs
from workbench.schemas import PlanCreate,LockRequest,RunCreate,Parameters
from workbench.service import REQUIRED_REVIEW
from workbench.runner import Docker,Worker
from workbench.comparison import compare_fresh

s=make_service(Settings());docker=Docker(s.settings);worker=Worker(s,docker)
with s.db.transaction() as c:
 w=c.execute(select(workspaces.c.id).where(workspaces.c.name=='Mammary transcriptomics')).scalar()
if not w:w=s.workspace('local','Mammary transcriptomics')
image=docker.image_id();submitted=[];baseline=None
for recipe,dataset,title,parameters in [
 ('density','law2018','Figure 1: expression filtering',Parameters()),
 ('density','law2018','Stricter expression filter',Parameters(filter_policy='cpm1')),
 ('differential','law2018','Basal versus LP expression',Parameters()),
 ('mds','chen2016','Mammary cell-state relationships',Parameters(min_samples=2))]:
 with s.db.transaction() as c:p=c.execute(select(plans).where(plans.c.workspace_id==w)).mappings().all()
 p=next((dict(p) for p in p if p['body']['title']==title and p['state']=='locked'),None)
 if p is None:
  p=s.new_plan('local',PlanCreate(workspace_id=w,title=title,dataset_id=dataset,recipe=recipe,parameters=parameters,
                 parent_id=baseline if parameters.filter_policy=='cpm1' else None,reason='Test sensitivity to a stricter expression threshold' if parameters.filter_policy=='cpm1' else ''))
  p=s.lock('local',p['id'],LockRequest(expected_revision=p['revision'],reviewed_fields=REQUIRED_REVIEW))
 if recipe=='density' and parameters.filter_policy=='published':baseline=p['id']
 r=s.submit('local',RunCreate(plan_id=p['id']),f'verify-{image}-{p["id"]}',image);submitted.append(r['id'])
 if p['id']==baseline:
  r=s.submit('local',RunCreate(plan_id=p['id']),f'verify-fresh-{image}-{p["id"]}',image);submitted.append(r['id'])
print('Verifying',len(submitted),'fresh recipe executions',flush=True)
deadline=time.time()+600
while time.time()<deadline:
 worker.tick()
 with s.db.transaction() as c:current=[s.get_run(c,'local',i) for i in submitted]
 if all(r['state'] not in ('queued','running','cancel_requested') for r in current):break
 time.sleep(.5)
for r in current:
 print(r['body']['plan']['title'],r['state'],r['body'].get('diagnostic',''),flush=True)
 if r['state']!='succeeded':
  for n in ['stderr.log','stdout.log']:
   if n in r['body']['artifacts']:print(s.store.read(r['body']['artifacts'][n]['sha256']).decode(),flush=True)
 assert r['state']=='succeeded'
 assert r['body']['comparison']['status']=='checks_match',r['body']['comparison']
 print('Retained:',r['body']['comparison']['metrics']['retained_genes'],flush=True)
fresh=compare_fresh(s.store,current[0]['body']['artifacts'],current[1]['body']['artifacts'])
assert fresh['same_numeric_bytes'],fresh
receipt={'checked_date':'2026-09-11','image_id':image,'runs':[{'id':r['id'],'plan_id':r['plan_id'],'recipe':r['body']['plan']['recipe'],'dataset':r['body']['plan']['dataset_id'],'filter':r['body']['plan']['parameters']['filter_policy'],'state':r['state'],'comparison':r['body']['comparison'],'artifacts':r['body']['artifacts']} for r in current],'fresh_comparison':fresh}
(ROOT/'evidence/science-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('All recipe and fresh-rerun checks passed',flush=True)
