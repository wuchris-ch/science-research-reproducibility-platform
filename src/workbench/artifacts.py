import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

MAX_BLOB = 100 * 1024 * 1024


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


class ArtifactStore:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def put(self, data: bytes) -> str:
        if len(data) > MAX_BLOB:
            raise ValueError("artifact exceeds 100 MiB")
        sha = hashlib.sha256(data).hexdigest()
        target = self.root / sha
        if target.exists():
            self.read(sha)
            return sha
        fd, temp = tempfile.mkstemp(dir=self.root)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, target)
            directory = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            Path(temp).unlink(missing_ok=True)
        return sha

    def read(self, sha: str) -> bytes:
        if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError("invalid artifact identity")
        path = self.root / sha
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError("artifact is not a regular file")
        if path.stat().st_size > MAX_BLOB:
            raise ValueError("artifact exceeds limit")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != sha:
            raise ValueError("artifact integrity failure")
        return data

    def collect(self, path: Path) -> dict:
        result = {}
        total = 0
        for file in sorted(path.rglob("*")):
            if file.is_symlink():
                raise ValueError("symlink output rejected")
            if file.is_dir():
                continue
            if not stat.S_ISREG(file.lstat().st_mode):
                raise ValueError("special output rejected")
            total += file.stat().st_size
            if total > MAX_BLOB:
                raise ValueError("outputs exceed limit")
            result[str(file.relative_to(path))] = {
                "sha256": self.put(file.read_bytes()),
                "bytes": file.stat().st_size,
            }
        return result
