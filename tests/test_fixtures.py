import gzip
from pathlib import Path
import pytest
from workbench.fixtures import bounded_gunzip, source_document

def test_gzip_expansion_is_bounded():
    with pytest.raises(ValueError, match='limit'):
        bounded_gunzip(gzip.compress(b'x' * 10000), 100)

def test_source_parser_rejects_entities(tmp_path: Path):
    p = tmp_path / 'source.xml'
    p.write_text('<!DOCTYPE a [<!ENTITY x SYSTEM "file:///etc/passwd">]><a><p>&x;</p></a>')
    with pytest.raises(Exception, match='EntitiesForbidden'):
        source_document(p, 'law2018')

def test_stable_evidence_ids(tmp_path: Path):
    p = tmp_path / 'source.xml'
    p.write_text('<article><p>Ten counts <b>minimum</b>.</p></article>')
    result = source_document(p, 'law2018')
    assert result['segments'][0]['id'] == 'law2018:0'
    assert result['segments'][0]['text'] == 'Ten counts minimum.'
    assert result['geometry'] is None
