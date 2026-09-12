import pytest

from workbench.inputs import validate_paired


def paired_tables():
    names = [f"s{i}" for i in range(6)]
    counts = (
        "gene_id\t" + "\t".join(names) + "\n" + "".join(f"g{i}\t1\t2\t3\t4\t5\t6\n" for i in range(120))
    ).encode()
    samples = (
        "sample\tdonor\tcondition\n"
        + "".join(f"{name}\td{i // 2}\t{'treated' if i % 2 else 'control'}\n" for i, name in enumerate(names))
    ).encode()
    return counts, samples


def test_exact_sample_alignment_and_pairing():
    counts, samples = paired_tables()
    valid = validate_paired(counts, samples)
    assert valid["design_rank"] == 4
    assert valid["library_sizes"]["s5"] == 720
    header, *data = samples.decode().splitlines()
    reordered = (header + "\n" + "\n".join(reversed(data)) + "\n").encode()
    assert validate_paired(counts, reordered)["metadata_reordered"]
    for bad in (
        samples.replace(b"s5", b"s6"),
        samples.replace(b"s5", b"s4"),
        samples.replace(b"s1\td0\ttreated", b"s1\td0\tcontrol"),
    ):
        with pytest.raises(ValueError):
            validate_paired(counts, bad)


def test_rejects_transformed_counts_duplicates_and_ragged_rows():
    counts, samples = paired_tables()
    for old, new in [
        (b"\t1\t", b"\t1.1\t"),
        (b"\t1\t", b"\t-1\t"),
        (b"g1\t", b"g0\t"),
        (b"g1\t", b"g1\textra\t"),
        (b"\t1\t", b"\t2147483648\t"),
    ]:
        with pytest.raises(ValueError):
            validate_paired(counts.replace(old, new, 1), samples)
