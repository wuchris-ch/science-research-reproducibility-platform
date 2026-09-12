# Inspection evidence

Current execution, sandbox, export, PostgreSQL, API image and extraction receipts are described in [implemented behavior and evidence](../docs/IMPLEMENTED.md). The feasibility discussion below records the earlier planning probe and its original limits.

[Start](../README.md) · [Demo interpretation](../docs/DEMO.md)

These receipts describe bounded checks performed September 11, 2026. They are not product outputs or certification of reproducibility.

- [feasibility.json](feasibility.json): primary article/code/input identifiers, all nine count-file hashes and library totals, a small independent filter check, and a fallback count-file inspection.
- [repository-inspection.json](repository-inspection.json): local repository HEADs and hashes of selected source/planning files. No tests or applications from those repositories were executed.

## Repeating the numerical probe

Retrieve the count archive from the URL in the receipt into temporary storage, verify its archive hash, then run this bounded standard-library Python check against that local path. It reads named members without extracting paths onto disk. It does not execute R or author code. A new or changed archive requires inspection rather than changing the expected digest to make the check pass.

```python
import csv, gzip, hashlib, io, json, statistics, tarfile
from pathlib import Path

receipt = json.loads(Path("evidence/feasibility.json").read_text())
archive = Path("/tmp/science-planning-research/GSE63310_RAW.tar")
assert archive.stat().st_size == receipt["archives"][0]["bytes"]
assert hashlib.sha256(archive.read_bytes()).hexdigest() == receipt["archives"][0]["sha256"]
columns, first_ids = [], None
with tarfile.open(archive) as members:
    for item in receipt["files"]:
        member = members.getmember(item["member"])
        assert member.isfile() and member.size == item["compressed_bytes"]
        packed = members.extractfile(member).read()
        assert hashlib.sha256(packed).hexdigest() == item["sha256_gzip"]
        with gzip.GzipFile(fileobj=io.BytesIO(packed)) as stream:
            raw = stream.read(item["decompressed_bytes"] + 1)
        assert len(raw) == item["decompressed_bytes"]
        assert hashlib.sha256(raw).hexdigest() == item["sha256_text"]
        rows = list(csv.DictReader(io.StringIO(raw.decode()), delimiter="\t"))
        ids = [row["EntrezID"] for row in rows]
        counts = [int(row["Count"]) for row in rows]
        first_ids = ids if first_ids is None else first_ids
        assert ids == first_ids and len(ids) == len(set(ids)) == 27179
        assert min(counts) >= 0 and sum(counts) == item["library_size"]
        columns.append(counts)

libraries = [sum(column) for column in columns]
cutoff = 10 / statistics.median(libraries) * 1_000_000
kept, alternative, all_zero = 0, 0, 0
for row in zip(*columns):
    cpm = [value / library * 1_000_000 for value, library in zip(row, libraries)]
    kept += sum(value >= cutoff for value in cpm) >= 3 and sum(row) >= 15
    alternative += sum(value > 1 for value in cpm) >= 3
    all_zero += all(value == 0 for value in row)
print({"shape": [len(first_ids), len(columns)], "all_zero": all_zero,
       "retained": kept, "variation_retained": alternative, "cpm_cutoff": cutoff})
```

Observed output: shape `[27179, 9]`, all-zero rows `5153`, retained genes `16624`, alternative retained genes `14165`, cutoff `0.19467135824640042`. The filtering calculation translates the inspected historical edgeR function for three equal-sized groups and the original library totals. It does not verify log-CPM transformation, density estimation, the plotted figure, historical environment compatibility or scientific validity.

The fallback file probe only decompressed and parsed the GSE60450 count table, confirming 27,179 rows and 12 sample columns alongside ID/length fields. It did not test sample annotation or MDS. Airway archive requests were stopped at byte limits without loading their R objects.
