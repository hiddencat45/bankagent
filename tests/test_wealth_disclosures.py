"""Check provenance and missing-share behavior independently of UI styling."""
import json
from pathlib import Path
from desktop.wealth_disclosures import disclosure


def test_rates_and_dates_match_exact_official_share_records():
    records=json.loads((Path(__file__).resolve().parents[1]/
        'docs/evidence/wealth-yields-20261101/official-excerpts.json').read_text(encoding='utf-8'))['records']
    hx,_,bob,jy=[r['fields'] for r in records]
    assert hx['sectionType']=='01'
    assert disclosure(hx['subShareCode'])['value']==hx['yieldYear']
    assert disclosure(hx['subShareCode'])['end'].replace('-','')==hx['endDate']
    assert disclosure(bob['PROD_CODE'])['value']==str(bob['INC'])
    b=disclosure(bob['PROD_CODE'])
    assert b['start'].replace('-','.')+'-'+b['end'].replace('-','.')==bob['INC_PERIOD']
    assert jy['c_agencyno']=='微众银行' and jy['c_interestway']=='0'
    j=disclosure(jy['c_fundcode'])
    assert j['value']+'%'==jy['yieldratio']
    assert j['start'].replace('-','')==jy['d_setupdate']
    assert j['end'].replace('-','')==jy['d_cdate']


def test_other_share_cannot_inherit_return_and_lookup_cannot_mutate_snapshot():
    assert 'value' not in disclosure('2119987003C')
    assert 'value' not in disclosure('YJ01251202')
    result=disclosure('2119987003A');result['value']='999'
    assert disclosure('2119987003A')['value']=='2.01'
