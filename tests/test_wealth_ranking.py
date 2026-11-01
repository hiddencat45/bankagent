"""Attribute changes must change recommendations; codes and catalog order must not."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import pytest
from bankagent.banking.wealth import PRODUCTS,recommend_products,screen
from bankagent.banking.wealth_ranking import shortlist
from test_wealth import ANSWERS,NOW


def top(rows):return [r['product_code'] for r in rows if r['recommendation_rank']]


def test_real_catalog_long_horizon_selects_two_with_relative_reasons():
    a={**ANSWERS,'horizon_days':1095,'priority':'风险优先'}
    rows=recommend_products(a,NOW.date())
    assert sum(r['eligible'] for r in rows)==10
    assert top(rows)==['2119987003A','5811323020']
    assert len([r for r in rows if r['comparison_group']=='其他备选'])==8
    assert any('8款风险等级更高' in reason for reason in rows[0]['recommendation_reasons'])
    assert '0.53%/年' in str(rows[0]['recommendation_reasons'])
    assert '0.57%/年' in str(rows[1]['tradeoffs'])
    balanced=recommend_products({**a,'priority':'综合比较'},NOW.date())
    assert top(balanced)==['2119987003A','5811223114']
    assert '0.22%/年' in str(balanced[1]['recommendation_reasons'])
    assert '不代表净收益更高' in str(balanced[1]['tradeoffs'])


def fixture_products():
    # Algorithm-only fixtures, never installed in the real product catalog.
    return [dict(code='a',short_name='甲',issuer_risk=1,hold_days=10,regular_fee_bps=50),
            dict(code='b',short_name='乙',issuer_risk=2,hold_days=0,regular_fee_bps=40),
            dict(code='c',short_name='丙',issuer_risk=2,hold_days=30,regular_fee_bps=20)]


def rank(products,priority):
    results=[dict(product_code=p['code'],eligible=True,match_status='matched',remaining_days=365) for p in products]
    return shortlist(products,results,priority)


def test_risk_and_liquidity_preferences_produce_different_orders():
    products=fixture_products()
    assert top(rank(products,'风险优先'))==['a','b']
    assert top(rank(products,'流动性优先'))==['b','a']
    assert top(rank(products,'综合比较'))==['a','c']


def test_order_and_code_are_not_preferred_whitelist_and_attributes_can_change_winner():
    products=fixture_products()
    assert top(rank(list(reversed(products)),'风险优先'))==['a','b']
    renamed=deepcopy(products)
    for p in renamed:p['code']='new-'+p['code']
    assert top(rank(renamed,'综合比较'))==['new-a','new-c']
    changed=deepcopy(products);changed[2].update(issuer_risk=1,hold_days=0,regular_fee_bps=10)
    assert top(rank(changed,'风险优先'))[0]=='c'


def test_unknown_fee_is_not_zero_and_ties_are_explained():
    products=fixture_products();products[2].pop('regular_fee_bps')
    rows=rank(products,'综合比较')
    assert top(rows)==['a','b']
    assert '待核实' in str(next(r for r in rows if r['product_code']=='c')['tradeoffs'])
    for p in products:p.update(issuer_risk=1,hold_days=0,regular_fee_bps=20)
    rows=rank(products,'风险优先')
    assert len(top(rows))==2 and all('不代表实质优势' in str(r['tradeoffs']) for r in rows if r['recommendation_rank'])


def test_only_eligible_can_be_recommended_and_shortlisting_never_changes_gate():
    a={**ANSWERS,'liquidity':'固定日期'}
    rows=recommend_products(a,NOW.date())
    assert top(rows)==[] and any(r['match_status']=='review' for r in rows)
    for priority in ('风险优先','流动性优先','综合比较'):
        rows=recommend_products({**ANSWERS,'priority':priority},NOW.date())
        for r in rows:
            p=next(p for p in PRODUCTS if p['code']==r['product_code'])
            assert r['eligible']==screen(p,ANSWERS,NOW.date())['eligible']
    products=fixture_products()[:1]
    assert len(top(rank(products,'风险优先')))==1


def test_structured_fee_is_the_existing_verified_contract_sum():
    records=json.loads((Path(__file__).resolve().parents[1]/'docs/evidence/wealth-catalog-20261101/verified-products.json').read_text(encoding='utf-8'))['products']
    facts={r['code']:int(Decimal(r['regular_fee_percent'])*100) for r in records}
    for p in PRODUCTS:
        assert type(p['regular_fee_bps']) is int and p['fee'].startswith(f"{p['regular_fee_bps']//100}.{p['regular_fee_bps']%100:02d}%")
        if p['code'] in facts:assert p['regular_fee_bps']==facts[p['code']]
