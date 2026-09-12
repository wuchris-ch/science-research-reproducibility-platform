"""Export API contracts without reading or modifying a research installation."""

import json
import tempfile
from pathlib import Path

from workbench.api import create_app
from workbench.config import ROOT, Settings

with tempfile.TemporaryDirectory(prefix="workbench-contracts-") as directory:
    app = create_app(Settings(data_dir=Path(directory), database_url="sqlite://"))
    (ROOT / "openapi.json").write_text(json.dumps(app.openapi(), indent=2) + "\n")
    app.state.service.db.engine.dispose()
