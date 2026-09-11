"""Pinned public inputs. No arbitrary URLs or archive extraction into the filesystem."""
import csv
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

import httpx
from defusedxml import ElementTree
from .config import ROOT, Settings

EVIDENCE = json.loads((ROOT / 'evidence/feasibility.json').read_text())
SOURCES = {
    'law2018': {'title': 'RNA-seq analysis is easy as 1-2-3 with limma, Glimma and edgeR',
                'authors': 'Law et al.', 'year': 2018, 'doi': EVIDENCE['article']['doi'],
                'version': 3, 'accession': 'GSE63310', 'figure': 'Figure 1',
                'url': EVIDENCE['article']['xml_url'], 'sha256': EVIDENCE['article']['xml_sha256'],
                'license': 'CC BY 4.0', 'recipes': ['density', 'differential']},
    'chen2016': {'title': 'From reads to genes to pathways: differential expression analysis of RNA-Seq experiments using Rsubread and the edgeR quasi-likelihood pipeline',
                 'authors': 'Chen et al.', 'year': 2016, 'doi': '10.12688/f1000research.8987.2',
                 'version': 2, 'accession': 'GSE60450', 'figure': 'Figure 1',
                 'url': 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4934518/fullTextXML',
                 'sha256': 'd0922133ec1126302fe84e84a19d8695616be59c5603c60779907e2434b68db4', 'license': 'CC BY 4.0', 'recipes': ['mds']},
}

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def fetch(url: str, dest: Path, expected: str, cap: int = 100_000_000):
    if dest.exists() and sha(dest.read_bytes()) == expected:
        return
    data = bytearray()
    with httpx.stream('GET', url, follow_redirects=True, timeout=90) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes():
            data.extend(chunk)
            if len(data) > cap:
                raise ValueError('Download exceeds input limit')
    if sha(data) != expected:
        raise ValueError(f'Source hash changed: {dest.name}. Review new bytes before updating the fixture.')
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix('.part')
    part.write_bytes(data)
    part.replace(dest)

def bounded_gunzip(data: bytes, cap: int = 10_000_000):
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
        out = stream.read(cap + 1)
    if len(out) > cap:
        raise ValueError('Decoded input exceeds limit')
    return out

def validate_counts(data: bytes, id_column: str, count_columns: list[str]):
    rows = list(csv.DictReader(io.StringIO(data.decode()), delimiter='\t'))
    ids = [row[id_column] for row in rows]
    if len(ids) != len(set(ids)) or len(ids) != 27179:
        raise ValueError('Unexpected gene universe or duplicate IDs')
    totals = []
    for column in count_columns:
        values = [int(row[column]) for row in rows]
        if any(v < 0 for v in values):
            raise ValueError('Negative counts')
        totals.append(sum(values))
    return ids, totals

def source_document(path: Path, dataset: str):
    data = path.read_bytes()
    if len(data) > 10_000_000:
        raise ValueError('Source document too large')
    root = ElementTree.fromstring(data)
    segments = []
    for el in root.iter():
        if el.tag in ('p', 'preformat', 'fig'):
            value = ' '.join(''.join(el.itertext()).split())
            if value:
                segments.append({'id': f'{dataset}:{len(segments)}', 'kind': el.tag,
                                 'text': value, 'xml_id': el.get('id'), 'source_sha256': sha(data)})
    return {**SOURCES[dataset], 'id': dataset, 'sha256': sha(data), 'segments': segments,
            'geometry': None, 'geometry_status': 'JATS passages; PDF regions not yet verified'}

def prepare(settings: Settings):
    settings.initialize()
    target = settings.data_dir / 'datasets'
    archive = settings.data_dir / 'sources/law-counts.tar'
    ref = EVIDENCE['archives'][0]
    fetch(ref['url'], archive, ref['sha256'])
    law = target / 'law2018'
    law.mkdir(exist_ok=True)
    ids = None
    with tarfile.open(archive) as tf:
        for entry in EVIDENCE['files']:
            member = tf.getmember(entry['member'])
            if not member.isfile() or member.size > 1_000_000:
                raise ValueError('Invalid archive member')
            compressed = tf.extractfile(member).read()
            text = bounded_gunzip(compressed)
            if sha(compressed) != entry['sha256_gzip'] or sha(text) != entry['sha256_text']:
                raise ValueError('Count file integrity failure')
            current, totals = validate_counts(text, 'EntrezID', ['Count'])
            if totals[0] != entry['library_size'] or (ids is not None and ids != current):
                raise ValueError('Sample or gene alignment changed')
            ids = current
            (law / entry['member'].removesuffix('.gz')).write_bytes(text)
    chen = target / 'chen2016'
    chen.mkdir(exist_ok=True)
    ref = EVIDENCE['fallback']
    compressed = settings.data_dir / 'sources/chen-counts.gz'
    fetch(ref['url'], compressed, ref['sha256'])
    data = bounded_gunzip(compressed.read_bytes())
    header = data.decode().splitlines()[0].split('\t')
    validate_counts(data, 'EntrezGeneID', header[2:])
    (chen / 'counts.tsv').write_bytes(data)
    for dataset, source in SOURCES.items():
        path = settings.data_dir / f'sources/{dataset}.xml'
        fetch(source['url'], path, source['sha256'])
        (settings.data_dir / f'sources/{dataset}.json').write_text(json.dumps(source_document(path, dataset)))
    return {d: sha((settings.data_dir / f'sources/{d}.xml').read_bytes()) for d in SOURCES}
