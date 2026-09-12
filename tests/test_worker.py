from sqlalchemy import select, update
from test_plans import locked

from workbench.database import attempts, runs
from workbench.runner import Worker
from workbench.schemas import RunCreate


class Sandbox:
    def __init__(self):
        self.objects = {}
        self.stopped = []

    def inspect(self, name):
        return self.objects.get(name)

    def launch(self, name, run):
        self.objects[name] = {
            "Config": {"Labels": {"research.run": run["id"]}},
            "Image": "image",
            "State": {"Status": "created", "Running": False},
        }

    def start(self, name):
        self.objects[name]["State"] = {"Running": True, "Status": "running"}

    def done(self, name):
        return False

    def stop(self, name):
        self.stopped.append(name)
        self.objects.pop(name, None)

    def remove(self, name):
        self.objects.pop(name, None)


def queued(service):
    p = locked(service)
    return service.submit("alice", RunCreate(plan_id=p["id"]), "key", "image")


def test_recovered_lease_fences_stale_completion(service):
    r = queued(service)
    one, two = Worker(service, Sandbox(), "one"), Worker(service, Sandbox(), "two")
    first = one.claim()
    assert two.claim() is None
    with service.db.transaction() as c:
        c.execute(update(runs).where(runs.c.id == r["id"]).values(lease_until=0))
    second = two.claim()
    assert second["epoch"] == first["epoch"]
    assert not one.finish(first, "succeeded", {})
    assert two.finish(second, "failed", {"diagnostic": "test"})


def test_cancellation_requires_stop_before_terminal_status(service):
    r = queued(service)
    sandbox = Sandbox()
    worker = Worker(service, sandbox)
    worker.tick()
    service.cancel("alice", r["id"])
    with service.db.transaction() as c:
        assert service.get_run(c, "alice", r["id"])["state"] == "cancel_requested"
    worker.tick()
    assert sandbox.stopped
    with service.db.transaction() as c:
        assert service.get_run(c, "alice", r["id"])["state"] == "cancelled"


def test_daemon_failure_does_not_claim_cancellation(service):
    r = queued(service)
    sandbox = Sandbox()
    worker = Worker(service, sandbox)
    worker.tick()
    service.cancel("alice", r["id"])

    def fail(_):
        raise RuntimeError("daemon unreachable")

    sandbox.stop = fail
    import pytest

    with pytest.raises(RuntimeError):
        worker.tick()
    with service.db.transaction() as c:
        assert service.get_run(c, "alice", r["id"])["state"] == "cancel_requested"


def test_deterministic_intent_survives_restart(service):
    r = queued(service)
    sandbox = Sandbox()
    worker = Worker(service, sandbox, "one")
    worker.tick()
    with service.db.transaction() as c:
        c.execute(update(runs).where(runs.c.id == r["id"]).values(lease_until=0))
    Worker(service, sandbox, "two").tick()
    assert len(sandbox.objects) == 1
    with service.db.transaction() as c:
        assert len(c.execute(select(attempts)).all()) == 1
