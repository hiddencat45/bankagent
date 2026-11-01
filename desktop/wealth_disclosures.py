"""Verified public disclosures for display, never simulation valuations.

Verified 2026-11-01 against each exact share class. Evidence and field mappings:
docs/理财收益披露核验.md. Refreshing an account does not refresh these snapshots.
"""
from copy import deepcopy

DISCLOSURES = {
    '2119987003A': dict(
        value='2.01', start='2021-06-25', end='2026-10-25', issuer='华夏理财',
        source='https://www.hxwm.com.cn/gmlc/gmlcDetail.html?id=2119987003A',
        note='按该 A 份额每万份净收益计算，由管理人披露。公开净值文件另有七日年化 '
             '0.9157%，数据日期 2026-09-29（较旧），不作为当前七日年化展示。'),
    'YJ01251202A': dict(
        value='2.64', start='2026-04-28', end='2026-10-30', issuer='北银理财',
        source='https://www.beijingbobwealth.com.cn/products_index/index.html?PROD_CODE=YJ01251202A',
        note='采用官网 A 类份额“过往业绩”中的成立以来年化值。同期单位净值 1.013486，'
             '净值不是百分比；近一个月年化为 1.67%（2026-09-30 至 2026-10-30）。'),
    '5811225439': dict(
        value='2.3967', start='2025-09-10', end='2026-10-29', issuer='交银理财',
        source='https://www.bocommwm.com/BankCommSite/shtml/jylc/cn/2503328/2503403/list.shtml?channelId=2503328&c_fundcode=5811225439',
        note='采用官网微众银行代销份额详情的成立以来年化值。同期单位净值 1.02723；'
             '未使用业绩比较基准或现金管理类字段作为收益率。'),
    '5811323020': dict(value='1.0265', start='2026-10-25', end='2026-10-31', metric='七日年化收益率',
        issuer='交银理财', source='https://www.bocommwm.com/BankCommSite/shtml/jylc/cn/2503328/2503403/list.shtml?channelId=2503328&c_fundcode=5811323020', note='按精确销售代码核对官网披露；微众渠道条款见下方产品合同。不同统计口径不直接比较。'),
    '5811225192': dict(value='3.3969', start='2025-04-29', end='2026-10-28', metric='成立以来年化收益率',
        issuer='交银理财', source='https://www.bocommwm.com/BankCommSite/shtml/jylc/cn/2503328/2503403/list.shtml?channelId=2503328&c_fundcode=5811225192', note='按精确销售代码核对官网披露；微众渠道条款见下方产品合同。不同统计口径不直接比较。'),
    '5811223114': dict(value='2.2254', start='2023-11-23', end='2026-10-28', metric='成立以来年化收益率',
        issuer='交银理财', source='https://www.bocommwm.com/BankCommSite/shtml/jylc/cn/2503328/2503403/list.shtml?channelId=2503328&c_fundcode=5811223114', note='按精确销售代码核对官网披露；微众渠道条款见下方产品合同。不同统计口径不直接比较。'),
    '5811225237': dict(value='2.5237', start='2025-05-22', end='2026-10-28', metric='成立以来年化收益率',
        issuer='交银理财', source='https://www.bocommwm.com/BankCommSite/shtml/jylc/cn/2503328/2503403/list.shtml?channelId=2503328&c_fundcode=5811225237', note='按精确销售代码核对官网披露；微众渠道条款见下方产品合同。不同统计口径不直接比较。'),
    '5811223020': dict(value='3.0258', start='2023-04-04', end='2026-10-28', metric='成立以来年化收益率',
        issuer='交银理财', source='https://www.bocommwm.com/BankCommSite/shtml/jylc/cn/2503328/2503403/list.shtml?channelId=2503328&c_fundcode=5811223020', note='按精确销售代码核对官网披露；微众渠道条款见下方产品合同。不同统计口径不直接比较。'),
    '5811223109': dict(value='3.0749', start='2023-11-15', end='2026-10-28', metric='成立以来年化收益率',
        issuer='交银理财', source='https://www.bocommwm.com/BankCommSite/shtml/jylc/cn/2503328/2503403/list.shtml?channelId=2503328&c_fundcode=5811223109', note='按精确销售代码核对官网披露；微众渠道条款见下方产品合同。不同统计口径不直接比较。'),
    '5811225212': dict(value='3.0394', start='2025-05-15', end='2026-10-28', metric='成立以来年化收益率',
        issuer='交银理财', source='https://www.bocommwm.com/BankCommSite/shtml/jylc/cn/2503328/2503403/list.shtml?channelId=2503328&c_fundcode=5811225212', note='按精确销售代码核对官网披露；微众渠道条款见下方产品合同。不同统计口径不直接比较。'),
}


def disclosure(code):
    """Unknown share classes never inherit another share class's performance."""
    result = deepcopy(DISCLOSURES.get(code, {}))
    result.update(metric=result.get('metric', '成立以来年化收益率' if result else '收益率待核实'),
                  checked='2026-11-01')
    return result
