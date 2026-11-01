"""Different cash horizons must produce meaningfully different candidate sets."""
import json
from pathlib import Path
import pytest
from bankagent.banking.wealth import PRODUCTS, screen
from desktop.wealth_disclosures import disclosure
from test_wealth import ANSWERS, NOW


@pytest.mark.parametrize('changes,expected',[
    ({'horizon_days':400,'experience':'无经验','loss':'仅低风险','loss_acceptance':'可以'},2),
    ({'horizon_days':15},4),
    ({'horizon_days':45},6),
    ({'horizon_days':200},9),
    ({'horizon_days':400},10),
    ({'horizon_days':400,'loss':'不能亏损'},0),
])
def test_user_cases_change_candidate_set(changes,expected):
    results=[screen(p,{**ANSWERS,**changes},NOW.date()) for p in PRODUCTS]
    assert len(results)==10 and sum(r['eligible'] for r in results)==expected
    assert all(len(r['reasons'])>=2 for r in results if r['eligible'])
    if changes.get('horizon_days')==45:
        assert not next(r for r in results if r['product_code']=='5811225237')['eligible']
        assert '90天' in ';'.join(next(r for r in results if r['product_code']=='5811225237')['reasons'])


def test_expanded_catalog_uses_verified_share_contracts_and_correct_yield_metric():
    records=json.loads((Path(__file__).resolve().parents[1]/
        'docs/evidence/wealth-catalog-20261101/verified-products.json').read_text(encoding='utf-8'))['products']
    catalog={p['code']:p for p in PRODUCTS}
    assert len(catalog)==10 and len(records)==7
    for r in records:
        p=catalog[r['code']];d=disclosure(r['code'])
        assert '微众银行代销' in r['contract_title'] and '2027年3月31日生效' not in r['contract_title']
        assert p['source']==r['contract_source'] and p['hold_days']==r['hold_days']
        assert p['minimum_minor']==r['minimum_minor'] and p['issuer_risk']==r['risk']
        assert d['metric']==r['performance_metric'] and d['value']==r['performance_value']
    cash=disclosure('5811323020')
    assert cash['metric']=='七日年化收益率' and cash['value']=='1.0265' and cash['end']=='2026-10-31'
