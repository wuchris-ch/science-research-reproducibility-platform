import pytest
from workbench.artifacts import ArtifactStore, canonical

def test_corruption_and_symlink(tmp_path):
    store = ArtifactStore(tmp_path / 'blobs')
    sha = store.put(b'evidence')
    assert store.read(sha) == b'evidence'
    (store.root / sha).write_bytes(b'changed')
    with pytest.raises(ValueError, match='integrity'): store.read(sha)
    out = tmp_path / 'output'; out.mkdir()
    (out / 'escape').symlink_to('/etc/passwd')
    with pytest.raises(ValueError, match='symlink'): store.collect(out)

def test_canonical_rejects_nonfinite():
    with pytest.raises(ValueError): canonical({'result': float('nan')})
    assert canonical({'b': 2, 'a': 1}) == canonical({'a': 1, 'b': 2})
