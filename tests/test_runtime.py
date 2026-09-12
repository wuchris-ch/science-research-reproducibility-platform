import json

import pytest

from workbench.runtime import RuntimeRegistry


def test_api_runtime_registration_needs_no_docker(service):
    registry = RuntimeRegistry(service.settings)
    with pytest.raises(RuntimeError):
        registry.image_id()
    path = service.settings.data_dir / "runtime.json"
    path.write_text(json.dumps({"image_tag": service.settings.image, "image_id": "sha256:" + "a" * 64}))
    assert registry.image_id() == "sha256:" + "a" * 64
    path.write_text(json.dumps({"image_tag": service.settings.image, "image_id": "mutable:latest"}))
    with pytest.raises(RuntimeError):
        registry.image_id()


def test_missing_registered_image_fails_with_actionable_diagnostic(service):
    from test_worker import Sandbox, queued

    from workbench.runner import UnavailableImage, Worker

    run = queued(service)
    sandbox = Sandbox()

    def missing(name, run):
        raise UnavailableImage("Registered image is absent")

    sandbox.launch = missing
    Worker(service, sandbox).tick()
    with service.db.transaction() as c:
        result = service.get_run(c, "alice", run["id"])
    assert result["state"] == "failed"
    assert "absent" in result["body"]["diagnostic"]
