import runpy

from workbench.config import ROOT


def test_replay_checks_missing_numeric_files_but_excludes_package_metadata(tmp_path):
    compare = runpy.run_path(str(ROOT / "scripts/reproduce.py"))["compare_numeric"]
    original, output = tmp_path / "original", tmp_path / "output"
    original.mkdir()
    output.mkdir()
    (original / "metrics.json").write_text('{"genes":42}')
    (output / "metrics.json").write_text('{"genes":42}')
    (original / "genes.tsv").write_text("gene\n1\n")
    (original / "locked-packages.json").write_text("[]")
    assert compare(original, output) == {"metrics.json": True, "genes.tsv": False}
    (output / "genes.tsv").write_text("gene\n1\n")
    assert all(compare(original, output).values())
    (output / "genes.tsv").write_text("gene\n2\n")
    assert compare(original, output)["genes.tsv"] is False
