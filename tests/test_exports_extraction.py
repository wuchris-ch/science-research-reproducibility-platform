import io,json,zipfile
import pytest
from workbench.exports import verify_bundle
from workbench.extraction import validate_proposals,lexical

def test_bundle_rejects_traversal_and_unlisted_files():
    for name in ['../escape','extra']:
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:
            z.writestr('manifest.json',json.dumps({'files':{}}));z.writestr(name,'bad')
        with pytest.raises(ValueError):verify_bundle(data.getvalue())

def test_extraction_requires_real_quote_and_evidence():
    source={'segments':[{'id':'s:1','text':'The data are GSE63310 and use TMM.'}]}
    result=validate_proposals(lexical(source),source)
    assert next(x for x in result if x['key']=='accession')['value']=='GSE63310'
    field={'key':'min_count','value':10,'origin':'reported','evidence_ids':['s:1'],'quote':'10','explanation':'Guess'}
    with pytest.raises(ValueError):validate_proposals([field],source)
    field.update(key='accession',value='GSE63310',quote='GSE63310',evidence_ids=['invented'])
    with pytest.raises(ValueError):validate_proposals([field],source)
    field.update(key='shell_command',evidence_ids=['s:1'])
    with pytest.raises(ValueError):validate_proposals([field],source)
