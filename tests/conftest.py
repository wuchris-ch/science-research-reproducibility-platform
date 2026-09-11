import json
import pytest
from workbench.config import Settings
from workbench.database import Database
from workbench.artifacts import ArtifactStore
from workbench.service import Service

@pytest.fixture
def service(tmp_path):
    settings = Settings(data_dir=tmp_path,database_url=f'sqlite:///{tmp_path}/test.db')
    settings.initialize()
    (tmp_path/'sources/law2018.json').write_text(json.dumps({'sha256':'a'*64,'segments':[{'id':'law2018:0','text':'A method'}]}))
    (tmp_path/'sources/chen2016.json').write_text(json.dumps({'sha256':'b'*64,'segments':[]}))
    db=Database(settings.database_url);db.migrate()
    yield Service(db,settings,ArtifactStore(tmp_path/'blobs'))
    db.engine.dispose()
