"""Explainable shortlist from product attributes, never a list of favored codes."""
from copy import deepcopy

RANKING_VERSION='wealth-shortlist-v1'


def fee_text(product):
    value=product.get('regular_fee_bps')
    return '待核实' if value is None else f'{value//100}.{value%100:02d}%/年'


def shortlist(products,results,priority):
    """Keep eligibility unchanged. Rank by preference; balanced means two explicit tradeoffs."""
    rows=deepcopy(results);catalog={p['code']:p for p in products}
    eligible=[r for r in rows if r['eligible']]
    def fee(p):
        value=p.get('regular_fee_bps')
        return (value is None,value if value is not None else 0)
    def attributes(r):
        p=catalog[r['product_code']]
        dimensions=(p['hold_days'],p['issuer_risk']) if priority=='流动性优先' else (p['issuer_risk'],p['hold_days'])
        return (*dimensions,*fee(p))
    def stable(r):
        p=catalog[r['product_code']]
        return (*attributes(r),p['short_name'],p['code'])
    eligible.sort(key=stable)
    chosen=eligible[:2]
    if priority=='综合比较' and eligible:
        # Two endpoints of the known risk/lock-up/cost tradeoff, not fabricated utility scores.
        known=[r for r in eligible if catalog[r['product_code']].get('regular_fee_bps') is not None]
        cheap=min(known,key=lambda r:(fee(catalog[r['product_code']]),*stable(r))) if known else eligible[0]
        chosen=[eligible[0]]
        if cheap!=eligible[0]:chosen.append(cheap)
        elif len(eligible)>1 and attributes(eligible[1])==attributes(eligible[0]):chosen.append(eligible[1])
    selected={r['product_code']:i+1 for i,r in enumerate(chosen)}
    leader=catalog[chosen[0]['product_code']] if chosen else None
    for r in rows:
        p=catalog[r['product_code']];rank=selected.get(p['code'])
        r.update(recommendation_rank=rank,ranking_version=RANKING_VERSION,recommendation_reasons=[],tradeoffs=[])
        if not r['eligible']:
            r['comparison_group']='待补充或核实' if r['match_status']=='review' else '不匹配'
            r['preference_reason']='尚未通过初筛，不进入推荐排序'
            continue
        r['comparison_group']='优先推荐' if rank else '其他备选'
        r['preference_reason']=({'风险优先':'先比较风险，再比较持有要求和常规费率',
            '流动性优先':'先比较持有要求，再比较风险和常规费率',
            '综合比较':'分别选择风险与灵活性、常规费用有优势的安排；两种取舍不表示收益高低'}[priority])
        hold='不设最低持有期' if p['hold_days']==0 else f"最低持有{p['hold_days']}天"
        r['tradeoffs']=[f"{hold}，不等于即时到账；常规费率{fee_text(p)}，不代表全部成本或当前优惠。"]
        if priority=='综合比较' and rank==2 and attributes(r)!=attributes(chosen[0]):
            r['recommendation_label']='较低常规费用的选择'
            r['recommendation_reasons']=[f"在已有可核实费率的合格候选中，三项常规年费率最低，为{fee_text(p)}。",
                f"你的剩余用钱期限为{r['remaining_days']}天，{hold}，已通过模拟确认与到账时间检查。"]
            r['tradeoffs'].insert(0,f"相比{leader['short_name']}（R{leader['issuer_risk']}、最低持有{leader['hold_days']}天），这款为R{p['issuer_risk']}、最低持有{p['hold_days']}天；低常规费率不代表净收益更高。")
        elif rank:
            r['recommendation_label']=('风险与灵活性优先的选择' if priority=='综合比较' else '首选推荐' if rank==1 else '第二个选择')
            axis='最低持有要求' if priority=='流动性优先' else '风险等级'
            r['recommendation_reasons']=[f"你选择{priority}；按{axis}优先比较后，这款位于合格候选的前列：管理人R{p['issuer_risk']}、{hold}。",
                f"常规费率{fee_text(p)}；相同风险和持有要求时，优先选择已核实常规费率较低的产品。"]
            if rank==1:
                worse=sum(catalog[x['product_code']]['issuer_risk']>p['issuer_risk'] for x in eligible)
                longer=sum(catalog[x['product_code']]['hold_days']>p['hold_days'] for x in eligible)
                r['recommendation_reasons'].append(f'相比其余合格候选：{worse}款风险等级更高，{longer}款最低持有期更长。')
            else:
                r['tradeoffs'].insert(0,f"首选{leader['short_name']}的常规费率为{fee_text(leader)}；本款为{fee_text(p)}。收益口径不同，不据此判断收益优劣。")
        else:
            r['recommendation_label']='备选'
            r['recommendation_reasons']=[r['preference_reason']+'；这款通过初筛，但未进入本次推荐的1～2款。']
        if rank and sum(attributes(x)==attributes(r) for x in eligible)>1:
            r['tradeoffs'].append('有产品在本次比较指标上相同；名称排序仅用于稳定展示，不代表实质优势。')
    return sorted(rows,key=lambda r:(0 if r['recommendation_rank'] else 1 if r['eligible'] else 2 if r['match_status']=='review' else 3,
                                    r['recommendation_rank'] or 0,stable(r)))
