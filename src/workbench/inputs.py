"""Bounded tabular input contracts, independent of any particular published dataset."""

import csv
import hashlib
import io
import re

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,100}$")
MAX_ROWS = 100_000
MAX_BYTES = 9_000_000


def rows(data, *, limit=MAX_ROWS):
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Table is empty or exceeds 9 MB")
    try:
        reader = csv.reader(io.StringIO(data.decode("utf-8-sig")), delimiter="\t", strict=True)
        header = next(reader)
        if len(header) != len(set(header)) or not all(SAFE_ID.fullmatch(x) for x in header):
            raise ValueError("Table headers must be unique identifiers")
        result = []
        for i, row in enumerate(reader, 2):
            if i > limit + 1 or len(row) != len(header):
                raise ValueError(f"Invalid table shape at row {i}")
            if any(len(value) > 200 for value in row):
                raise ValueError(f"Oversized table cell at row {i}")
            result.append(row)
        if not result:
            raise ValueError("Table has no data rows")
        return header, result
    except (UnicodeError, csv.Error, StopIteration) as error:
        raise ValueError("Expected a UTF-8 tab-separated table") from error


def validate_paired(counts_data, samples_data):
    header, counts = rows(counts_data)
    sh, samples = rows(samples_data, limit=64)
    if header[0] != "gene_id" or not 6 <= len(header) - 1 <= 64:
        raise ValueError("Counts require gene_id and 6 to 64 sample columns")
    if sh != ["sample", "donor", "condition"]:
        raise ValueError("Sample columns must be sample, donor, condition in that order")
    ids = [row[0] for row in samples]
    if len(ids) != len(set(ids)) or set(ids) != set(header[1:]):
        missing = sorted(set(header[1:]) - set(ids))
        extra = sorted(set(ids) - set(header[1:]))
        raise ValueError(f"Sample alignment must be an exact bijection; missing={missing}, extra={extra}")
    donors = {}
    for _sample, donor, condition in samples:
        if not SAFE_ID.fullmatch(donor) or condition not in ("control", "treated"):
            raise ValueError("Every sample needs a donor identifier and control or treated condition")
        donors.setdefault(donor, []).append(condition)
    if any(sorted(conditions) != ["control", "treated"] for conditions in donors.values()):
        raise ValueError("Each donor must have exactly one control and one treated sample")
    genes, totals, zero = set(), [0] * (len(header) - 1), 0
    for line, row in enumerate(counts, 2):
        if not SAFE_ID.fullmatch(row[0]) or row[0] in genes:
            raise ValueError(f"Gene identifiers must be valid and unique, row {line}")
        genes.add(row[0])
        if any(not re.fullmatch(r"[0-9]{1,10}", value) or int(value) > 2147483647 for value in row[1:]):
            raise ValueError(f"Counts must be nonnegative 32-bit integers, row {line}")
        values = [int(value) for value in row[1:]]
        zero += sum(values) == 0
        totals = [a + b for a, b in zip(totals, values, strict=True)]
    if len(genes) < 100 or any(value == 0 for value in totals):
        raise ValueError("At least 100 genes and a nonzero library for every sample are required")
    return {
        "contract": "paired-counts-v1",
        "counts_sha256": hashlib.sha256(counts_data).hexdigest(),
        "samples_sha256": hashlib.sha256(samples_data).hexdigest(),
        "input_genes": len(genes),
        "samples": len(samples),
        "donors": len(donors),
        "all_zero_genes": zero,
        "library_sizes": dict(zip(header[1:], totals, strict=True)),
        "sample_order": header[1:],
        "metadata_reordered": ids != header[1:],
        "alignment": [
            {"sample": name, "metadata_row": ids.index(name) + 2, "count_column": i + 2}
            for i, name in enumerate(header[1:])
        ],
        "design_rank": len(donors) + 1,
        "residual_degrees_of_freedom": len(donors) - 1,
    }
