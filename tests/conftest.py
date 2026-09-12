import json
import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from workbench.artifacts import ArtifactStore
from workbench.config import Settings
from workbench.database import Database
from workbench.service import Service


@pytest.fixture
def service(tmp_path):
    postgres = os.environ.get("WORKBENCH_TEST_POSTGRES_URL")
    admin = None
    name = "wb_test_" + uuid.uuid4().hex
    url = f"sqlite:///{tmp_path}/test.db"
    if postgres:
        admin = create_engine(postgres, isolation_level="AUTOCOMMIT")
        with admin.connect() as c:
            c.execute(text(f"CREATE DATABASE {name}"))
        url = make_url(postgres).set(database=name).render_as_string(hide_password=False)
    settings = Settings(data_dir=tmp_path, database_url=url)
    settings.initialize()
    (tmp_path / "sources/law2018.json").write_text(
        json.dumps({"sha256": "a" * 64, "segments": [{"id": "law2018:0", "text": "A method"}]})
    )
    (tmp_path / "sources/chen2016.json").write_text(json.dumps({"sha256": "b" * 64, "segments": []}))
    db = Database(settings.database_url)
    db.migrate()
    yield Service(db, settings, ArtifactStore(tmp_path / "blobs"))
    db.engine.dispose()
    if admin:
        with admin.connect() as c:
            c.execute(text(f"DROP DATABASE {name} WITH (FORCE)"))
        admin.dispose()
