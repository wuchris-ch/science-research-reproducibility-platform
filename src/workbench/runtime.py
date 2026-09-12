"""Read-only runtime registration for an API with no Docker socket or CLI access."""

import json
import re

from .artifacts import canonical


class RuntimeRegistry:
    def __init__(self, settings):
        self.settings = settings

    def image_id(self):
        path = self.settings.data_dir / "runtime.json"
        if self.settings.image_id:
            identity = self.settings.image_id
        else:
            try:
                record = json.loads(path.read_text())
            except (OSError, ValueError):
                raise RuntimeError("Runtime registration is missing; run workbench build") from None
            if record.get("image_tag") != self.settings.image:
                raise RuntimeError("Runtime registration names a different image")
            identity = record.get("image_id", "")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", identity):
            raise RuntimeError("Runtime registration requires an immutable image identity")
        return identity


def register(settings, docker):
    import time

    record = {
        "schema_version": 1,
        "image_tag": settings.image,
        "image_id": docker.image_id(),
        "engine_id": docker.engine_id(),
        "registered_at": time.time(),
        "platform": "linux/amd64",
    }
    path = settings.data_dir / "runtime.json"
    temp = path.with_suffix(".part")
    temp.write_bytes(canonical(record))
    temp.chmod(0o600)
    temp.replace(path)
    return record
