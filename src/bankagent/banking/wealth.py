"""Local wealth sandbox. Public product facts NEVER stand in for live bank quotes.

Money and hundredths of shares are integers. The enclosing backend transaction
commits account cash, reserved cash, lots, events and idempotency receipts together.
"""
from copy import deepcopy
from datetime import date, timedelta
from uuid import uuid4

RULE_VERSION = 'wealth-demo-v1'
NOTICE = '仅模拟：净值固定1元，不计收益、亏损及费用；演示日历仅排除周末，不代表银行实际规则。真实渠道在售、评级、费率优惠及到账待核实。'
PRODUCTS = (
    dict(code='2119987003A', name='华夏理财现金管理类理财产品3号A', short_name='华夏现金3号A',
         issuer='华夏理财', issuer_risk=1, minimum_minor=1, hold_days=0, fee='0.53%/年（合同三项常规费率合计）',
         source='https://wap.hxb.com.cn/lcpdf/4363285c6ea303487e01ab8673ad1f77.html'),
    dict(code='YJ01251202A', name='北银理财京华远见春系列诚享7天持有期27号A', short_name='北银7天27号A',
         issuer='北银理财', issuer_risk=2, minimum_minor=100, hold_days=7, fee='0.53%/年（合同三项常规费率合计）',
         source='https://www.beijingbobwealth.com.cn/upload/pdf/1778846245812-YJ01251202Abylcjhyjcxlcx7tcyq27hlccp-lccpsms-wzyx-2026-05-15-YJ01251202.pdf'),
    dict(code='5811225439', name='交银理财稳享灵动慧利日开41号（7天持有期）', short_name='交银7天41号',
         issuer='交银理财', issuer_risk=2, minimum_minor=100, hold_days=7, fee='0.52%/年（合同三项常规费率合计）',
         source='https://www.bocommwm.cn/BankCommSite/upload/infos/202509/05/3583668/20250905163601_交银理财稳享灵动慧利日开41号（7天持有期）理财产品（微众银行代销）.pdf'),
    dict(code='5811323020', name='交银理财稳享现金添利（乐享版）1号理财产品B', short_name='交银现金添利1号B',
         issuer='交银理财', issuer_risk=1, minimum_minor=1, hold_days=0, fee='0.57%/年（三项常规费率合计）；不收取超额业绩报酬；特定流动性风险情形可收强制赎回费',
         source='https://www.bocommwm.com/BankCommSite/upload/infos/202608/20/3698979/20260820161810_20260820161755PRaLa1425.pdf'),
    dict(code='5811225192', name='交银理财慧选日开2号（14天持有期）理财产品', short_name='交银慧选14天2号',
         issuer='交银理财', issuer_risk=2, minimum_minor=100, hold_days=14, fee='0.47%/年（三项常规费率合计）；超过2.10%/年部分按20%提取超额业绩报酬',
         source='https://www.bocommwm.com/BankCommSite/upload/infos/202608/19/3697978/20260819172428_20260819172427EZYnZ1143.pdf'),
    dict(code='5811223114', name='交银理财稳享灵动慧利日开4号（30天持有期）安鑫版理财产品D', short_name='交银安鑫30天4号D',
         issuer='交银理财', issuer_risk=2, minimum_minor=100, hold_days=30, fee='0.22%/年（三项常规费率合计）；不收取超额业绩报酬',
         source='https://www.bocommwm.com/BankCommSite/upload/infos/202608/19/3697985/20260819172428_20260819172427dStuA1156.pdf'),
    dict(code='5811225237', name='交银理财慧选日开8号（90天持有期）理财产品', short_name='交银慧选90天8号',
         issuer='交银理财', issuer_risk=2, minimum_minor=100, hold_days=90, fee='0.57%/年（三项常规费率合计）；超过2.53%/年部分按40%提取超额业绩报酬',
         source='https://www.bocommwm.com/BankCommSite/upload/infos/202608/12/3691777/20260812172144_20260812172131tSIWW1474.pdf'),
    dict(code='5811223020', name='交银理财稳享固收精选日开8号（150天持有期）理财产品D', short_name='交银固收150天8号D',
         issuer='交银理财', issuer_risk=2, minimum_minor=100, hold_days=150, fee='0.62%/年（三项常规费率合计）；超过1.10%/年部分按30%提取超额业绩报酬',
         source='https://www.bocommwm.com/BankCommSite/upload/infos/202608/12/3691813/20260812172147_20260812172132dcSzE1554.pdf'),
    dict(code='5811223109', name='交银理财稳享灵动慧利日开6号（180天持有期）鑫享版理财产品', short_name='交银鑫享180天6号',
         issuer='交银理财', issuer_risk=2, minimum_minor=100, hold_days=180, fee='0.42%/年（三项常规费率合计）；不收取超额业绩报酬',
         source='https://www.bocommwm.com/BankCommSite/upload/infos/202608/12/3691806/20260812172146_20260812172133HbyUq1706.pdf'),
    dict(code='5811225212', name='交银理财慧选日开6号（365天持有期）理财产品', short_name='交银慧选365天6号',
         issuer='交银理财', issuer_risk=2, minimum_minor=100, hold_days=365, fee='0.47%/年（三项常规费率合计）；超过业绩比较基准区间中枢部分按40%提取超额业绩报酬',
         source='https://www.bocommwm.com/BankCommSite/upload/infos/202608/12/3691780/20260812172144_20260812172131EGfce1472.pdf'),
)
PRODUCT_BY_CODE = {p['code']: p for p in PRODUCTS}
WRITES = frozenset({'SAVE_WEALTH_PROFILE', 'SUBSCRIBE_WEALTH', 'REDEEM_WEALTH', 'CANCEL_WEALTH_ORDER', 'ADVANCE_WEALTH_DEMO'})
READS = frozenset({'QUERY_WEALTH', 'RECOMMEND_WEALTH'})
OPERATIONS = WRITES | READS
STATES = {'SUBMITTED':'申请已提交', 'UNCERTAIN':'受理结果确认中', 'ACCEPTED':'已受理，待交易确认',
          'WAITING_CASH':'赎回已确认，待到账', 'SETTLED':'已完成', 'CANCELLED':'已撤销', 'REJECTED':'已拒绝，资金或份额已释放'}
ERRORS = {'PROFILE_REQUIRED':'请先填写并确认模拟需求问卷。', 'PROFILE_EXPIRED':'模拟问卷已过期，请重新确认。',
          'WEALTH_NOT_MATCHED':'产品不符合当前模拟需求，请查看筛选理由。',
          'BUDGET_EXCEEDED':'已有持仓及申购冻结加本次金额超过确认的闲置资金预算。',
          'INSUFFICIENT_BALANCE':'可用余额不足，未冻结资金。', 'INSUFFICIENT_REDEEMABLE':'可赎回份额不足：请核对持有期和已锁定份额。',
          'ORDER_NOT_ACCESSIBLE':'当前账户没有这笔订单。', 'STALE_ORDER':'订单已变化，请刷新后重新确认。',
          'CANNOT_CANCEL':'订单已确认或结束，无法撤单。', 'INVALID_EVENT':'此订单状态不支持该演示动作。',
          'SOURCE_CARD_REQUIRED':'请先办理并激活当前账户的借记卡。', 'SOURCE_CARD_NOT_ACTIVE':'当前账户卡片未激活或已冻结。',
          'USER_CANCELLED':'已取消本次操作，未执行变更。', 'INVALID_PARAMS':'输入不合法，请核对产品、金额及问卷。'}
PROFILE_FIELDS = {'budget_minor', 'free_cash_minor', 'horizon_days', 'purpose', 'liquidity', 'loss', 'income', 'debt', 'experience', 'priority'}
CHOICES = {'purpose': {'闲置资金','必要支出'}, 'liquidity': {'可等待','当天到账','固定日期'},
           'loss': {'不能亏损','仅低风险','接受波动'}, 'income': {'稳定','不稳定'},
           'debt': {'无压力','有还款压力','借款理财'}, 'experience': {'无经验','有经验'},
           'priority': {'风险优先','流动性优先','综合比较'}}


def reply(operation, data=None, error=None):
    return dict(operation=operation, status='REJECTED' if error else 'COMPLETED', data=data, error_code=error)


def business_day(day, count=0):
    while day.weekday() >= 5:
        day += timedelta(days=1)
    for _ in range(count):
        day += timedelta(days=1)
        while day.weekday() >= 5:
            day += timedelta(days=1)
    return day


def validate_profile(p):
    return (set(p) == PROFILE_FIELDS and all(type(p[k]) is int and 0 <= p[k] <= 10**10 for k in ('budget_minor','free_cash_minor'))
            and p['budget_minor'] > 0 and type(p['horizon_days']) is int and 1 <= p['horizon_days'] <= 3650
            and all(isinstance(p[k], str) and p[k] in choices for k, choices in CHOICES.items()))


def screen(product, profile, day):
    reasons = []
    if profile['purpose'] != '闲置资金': reasons.append('必要支出不能承担亏损或延期到账')
    if profile['debt'] != '无压力': reasons.append('存在还款压力或使用借款')
    if profile['budget_minor'] > profile['free_cash_minor']: reasons.append('预算超过扣除必要支出和备用金后的闲钱')
    if profile['loss'] == '不能亏损': reasons.append('本产品不保本，不符合不能亏损的要求')
    cap = 2 if profile['loss'] == '接受波动' and profile['experience'] == '有经验' and profile['income'] == '稳定' else 1
    if product['issuer_risk'] > cap: reasons.append('超过本演示问卷的保守风险范围（非银行正式测评）')
    if profile['liquidity'] != '可等待': reasons.append('要求当天或固定日期到账，真实渠道规则未核实')
    earliest = business_day(business_day(day, 1) + timedelta(days=product['hold_days']))
    earliest = business_day(earliest, 2)
    needed = (earliest-day).days
    if needed > profile['horizon_days']:
        reasons.append(f"期限不足：持有{product['hold_days']}天，加上模拟确认与到账需{needed}天，超过你的{profile['horizon_days']}天用钱期限")
    if profile['budget_minor'] < product['minimum_minor']: reasons.append('预算低于说明书起投金额')
    return dict(product_code=product['code'], eligible=not reasons, reasons=reasons or [
        f"管理人R{product['issuer_risk']}在本次模拟筛选上限R{cap}内，预算覆盖起投金额",
        f"最低持有{product['hold_days']}天；含模拟确认与到账需{needed}天，未超过你的{profile['horizon_days']}天用钱期限"],
                real_status='待核实，不能作为真实购买建议', simulated_earliest_cash_date=earliest.isoformat())


class WealthMixin:
    def _wealth_day(self, data, account):
        return date.fromisoformat(data.get('wealth_clocks', {}).get(account, self._now().date().isoformat()))

    def query_wealth(self, *, context, recommend=False):
        op = 'RECOMMEND_WEALTH' if recommend else 'QUERY_WEALTH'
        with self._transaction():
            if not self._owned(context): return reply(op, error='ACCOUNT_NOT_ACCESSIBLE')
            data, account = self._data, context.account_id
            day = self._wealth_day(data, account)
            profile = data.get('wealth_profiles', {}).get(context.user_id)
            valid = profile and date.fromisoformat(profile['expires_on']) >= self._now().date()
            orders = [deepcopy(o) for o in data.get('wealth_orders', {}).values() if o['account_id'] == account]
            lots = [deepcopy(l) for l in data.get('wealth_lots', {}).values() if l['account_id'] == account and l['units_minor']]
            for lot in lots:
                lot['redeemable_minor'] = lot['units_minor'] - lot['locked_minor'] if day >= date.fromisoformat(lot['unlock_on']) else 0
            frozen = sum(o['requested_minor'] for o in orders if o['side']=='BUY' and o['state'] in {'SUBMITTED','ACCEPTED','UNCERTAIN'})
            waiting = sum(o['filled_minor'] for o in orders if o['state']=='WAITING_CASH')
            return reply(op, dict(products=deepcopy(PRODUCTS), profile=deepcopy(profile), profile_valid=bool(valid),
                recommendations=[screen(p, profile['answers'], day) for p in PRODUCTS] if valid else [],
                orders=sorted(orders, key=lambda o:o['sequence'], reverse=True), lots=lots, day=day.isoformat(),
                available_minor=data['accounts'][account]['balance_minor'], frozen_minor=frozen, waiting_minor=waiting,
                holdings_minor=sum(l['units_minor'] for l in lots), currency='CNY', notice=NOTICE, rule_version=RULE_VERSION))

    def save_wealth_profile(self, *, context, **answers):
        if not validate_profile(answers): return reply('SAVE_WEALTH_PROFILE', error='INVALID_PARAMS')
        def apply(data):
            profile = dict(answers=answers, recorded_at=self._now().isoformat(),
                expires_on=(self._now().date()+timedelta(days=365)).isoformat(), rule_version=RULE_VERSION,
                assessment='仅模拟需求筛选，不是银行正式风险测评')
            data.setdefault('wealth_profiles', {})[context.user_id] = profile
            return reply('SAVE_WEALTH_PROFILE', dict(profile=profile, notice=NOTICE))
        return self._lifecycle_write(context, 'SAVE_WEALTH_PROFILE', answers, apply)

    def _wealth_event(self, order, day, message):
        order['version'] += 1
        order['events'].append(dict(sequence=order['version'], day=day.isoformat(), state=order['state'], message=message))

    def _wealth_cash(self, data, order, amount, kind):
        if not amount: return
        account = data['accounts'][order['account_id']]
        account['balance_minor'] += -amount if kind == 'WEALTH_RESERVE' else amount
        data['transactions'].append(dict(transaction_id='wealth-tx-'+uuid4().hex, account_id=order['account_id'],
            occurred_at=self._now().isoformat(), kind=kind, amount_minor=amount, currency='CNY',
            category={'WEALTH_RESERVE':'模拟申购冻结','WEALTH_RELEASE':'模拟理财解冻','WEALTH_CREDIT':'模拟赎回到账'}[kind],
            merchant=PRODUCT_BY_CODE[order['product_code']]['short_name'], order_id=order['order_id']))

    def wealth_order(self, *, context, product_code, amount_minor, side):
        op = 'SUBSCRIBE_WEALTH' if side == 'BUY' else 'REDEEM_WEALTH'
        params = dict(product_code=product_code, amount_minor=amount_minor)
        if side not in {'BUY','SELL'} or product_code not in PRODUCT_BY_CODE or type(amount_minor) is not int or not 0 < amount_minor <= 10**10:
            return reply(op, error='INVALID_PARAMS')
        def apply(data):
            account, day = context.account_id, self._wealth_day(data, context.account_id)
            product = PRODUCT_BY_CODE[product_code]
            allocations = []
            if side == 'BUY':
                blocked = self._source_card_error(context)
                if blocked: return reply(op, error=blocked)
                profile = data.get('wealth_profiles', {}).get(context.user_id)
                if not profile: return reply(op, error='PROFILE_REQUIRED')
                if date.fromisoformat(profile['expires_on']) < self._now().date(): return reply(op, error='PROFILE_EXPIRED')
                if not screen(product, profile['answers'], day)['eligible']: return reply(op, error='WEALTH_NOT_MATCHED')
                if amount_minor < product['minimum_minor']: return reply(op, error='INVALID_PARAMS')
                exposure = sum(l['units_minor'] for l in data.get('wealth_lots', {}).values() if l['user_id']==context.user_id)
                exposure += sum(o['requested_minor'] for o in data.get('wealth_orders', {}).values()
                    if o['user_id']==context.user_id and o['side']=='BUY' and o['state'] in {'SUBMITTED','ACCEPTED','UNCERTAIN'})
                exposure += sum(o['filled_minor'] for o in data.get('wealth_orders', {}).values()
                    if o['user_id']==context.user_id and o['state']=='WAITING_CASH')
                if exposure+amount_minor > min(profile['answers']['budget_minor'],profile['answers']['free_cash_minor']): return reply(op, error='BUDGET_EXCEEDED')
                if data['accounts'][account]['balance_minor'] < amount_minor: return reply(op, error='INSUFFICIENT_BALANCE')
            else:
                remaining = amount_minor
                for lid, lot in sorted(data.get('wealth_lots', {}).items(), key=lambda pair:(pair[1]['confirmed_on'],pair[0])):
                    if lot['account_id'] != account or lot['product_code'] != product_code or day < date.fromisoformat(lot['unlock_on']): continue
                    take = min(remaining, lot['units_minor']-lot['locked_minor'])
                    if take:
                        allocations.append(dict(lot_id=lid, units_minor=take)); remaining -= take
                    if not remaining: break
                if remaining: return reply(op, error='INSUFFICIENT_REDEEMABLE')
            orders = data.setdefault('wealth_orders', {})
            oid = 'W'+uuid4().hex[:16]
            order = dict(order_id=oid, account_id=account, user_id=context.user_id, product_code=product_code,
                side=side, requested_minor=amount_minor, filled_minor=0, state='SUBMITTED', version=0,
                sequence=len(orders)+1, created_at=self._now().isoformat(), day=day.isoformat(),
                allocations=allocations, events=[], rule_version=RULE_VERSION, simulation=True,
                product_snapshot=deepcopy(product), next_on=day.isoformat())
            orders[oid] = order
            data.setdefault('wealth_clocks', {})[account] = day.isoformat()
            if side == 'BUY': self._wealth_cash(data, order, amount_minor, 'WEALTH_RESERVE')
            else:
                for allocation in allocations: data['wealth_lots'][allocation['lot_id']]['locked_minor'] += allocation['units_minor']
            self._wealth_event(order, day, '申请已提交；尚未成交。资金冻结或份额锁定已入账。')
            return reply(op, dict(order=deepcopy(order), notice=NOTICE))
        return self._lifecycle_write(context, op, params, apply)

    def _source_card_error(self, context):
        cards = [c for c in self._data['cards'].values() if c['account_id']==context.account_id]
        if len(cards)!=1: return 'SOURCE_CARD_REQUIRED'
        if cards[0]['status']!='ACTIVE': return 'SOURCE_CARD_NOT_ACTIVE'
        return None

    def _release_wealth(self, data, order):
        if order['side']=='BUY': self._wealth_cash(data, order, order['requested_minor'], 'WEALTH_RELEASE')
        else:
            for part in order['allocations']: data['wealth_lots'][part['lot_id']]['locked_minor'] -= part['units_minor']

    def change_wealth_order(self, *, context, order_id, version, event, operation):
        params = dict(order_id=order_id, version=version)
        if operation == 'ADVANCE_WEALTH_DEMO': params['event'] = event
        if (operation not in {'CANCEL_WEALTH_ORDER','ADVANCE_WEALTH_DEMO'} or not isinstance(order_id,str)
                or type(version) is not int or version < 1 or event not in {'撤单','下一步','拒单','半数成交','延迟到账','模拟超时'}):
            return reply(operation, error='INVALID_PARAMS')
        if operation == 'CANCEL_WEALTH_ORDER' and event != '撤单': return reply(operation, error='INVALID_PARAMS')
        if operation == 'ADVANCE_WEALTH_DEMO' and event == '撤单': return reply(operation, error='INVALID_PARAMS')
        def apply(data):
            order = data.get('wealth_orders', {}).get(order_id)
            if not order or order['account_id']!=context.account_id: return reply(operation, error='ORDER_NOT_ACCESSIBLE')
            if order['version']!=version: return reply(operation, error='STALE_ORDER')
            state = order['state']; day = self._wealth_day(data, context.account_id)
            if event == '撤单':
                if state not in {'SUBMITTED','ACCEPTED'}: return reply(operation, error='CANNOT_CANCEL')
                self._release_wealth(data, order); order['state']='CANCELLED'; note='撤单成功，资金或份额已释放。'
            elif event == '拒单':
                if state not in {'SUBMITTED','ACCEPTED'}: return reply(operation, error='INVALID_EVENT')
                self._release_wealth(data, order); order['state']='REJECTED'; note='演示渠道拒单，资金或份额已释放。'
            elif event == '模拟超时':
                if state!='SUBMITTED': return reply(operation, error='INVALID_EVENT')
                order['state']='UNCERTAIN'; note='模拟回执丢失；资金或份额保持锁定，下一步查询原订单，不重复下单。'
            elif event == '延迟到账':
                if state!='WAITING_CASH': return reply(operation, error='INVALID_EVENT')
                order['next_on']=business_day(max(day,date.fromisoformat(order['next_on'])),1).isoformat()
                note='演示到账延期，仍待到账；未增加可用现金。'
            elif event == '下一步' and state in {'SUBMITTED','UNCERTAIN'}:
                order['state']='ACCEPTED'; order['next_on']=business_day(day,1).isoformat(); note='模拟渠道已受理，尚未成交。'
            elif state == 'ACCEPTED' and event in {'下一步','半数成交'}:
                filled = order['requested_minor'] if event=='下一步' else order['requested_minor']//2
                if filled <= 0: return reply(operation, error='INVALID_EVENT')
                day=max(day,date.fromisoformat(order['next_on']))
                order['filled_minor']=filled
                if order['side']=='BUY':
                    self._wealth_cash(data, order, order['requested_minor']-filled, 'WEALTH_RELEASE')
                    lid='L'+uuid4().hex[:16]
                    hold=order['product_snapshot']['hold_days']
                    data.setdefault('wealth_lots', {})[lid]=dict(lot_id=lid, account_id=context.account_id,user_id=context.user_id,
                        product_code=order['product_code'], order_id=order_id, units_minor=filled, locked_minor=0,
                        confirmed_on=day.isoformat(), unlock_on=business_day(day+timedelta(days=hold)).isoformat())
                    order['state']='SETTLED'; note='申购确认，已按模拟净值1元增加份额；未成交部分已解冻。'
                else:
                    remaining=filled
                    for part in order['allocations']:
                        lot=data['wealth_lots'][part['lot_id']]; take=min(remaining,part['units_minor'])
                        lot['locked_minor']-=part['units_minor']; lot['units_minor']-=take; remaining-=take
                    order['state']='WAITING_CASH'; order['next_on']=business_day(day,2).isoformat()
                    note='赎回确认，持仓已扣减，资金待到账；未成交部分份额已释放。'
            elif event == '下一步' and state=='WAITING_CASH':
                day=max(day,date.fromisoformat(order['next_on']))
                self._wealth_cash(data,order,order['filled_minor'],'WEALTH_CREDIT')
                order['state']='SETTLED'; note='模拟赎回款已到账，可用余额已增加。'
            else: return reply(operation,error='INVALID_EVENT')
            data.setdefault('wealth_clocks', {})[context.account_id]=day.isoformat()
            self._wealth_event(order,day,note)
            return reply(operation,dict(order=deepcopy(order),notice=NOTICE))
        return self._lifecycle_write(context,operation,params,apply)

    def advance_wealth_days(self, *, context, days, expected_day):
        # Same registered action, alternative mutually exclusive shape.
        op='ADVANCE_WEALTH_DEMO'; params=dict(days=days,expected_day=expected_day)
        if type(days) is not int or not 1 <= days <= 31: return reply(op,error='INVALID_PARAMS')
        def apply(data):
            day=self._wealth_day(data,context.account_id)
            if day.isoformat()!=expected_day: return reply(op,error='STALE_ORDER')
            day+=timedelta(days=days)
            data.setdefault('wealth_clocks', {})[context.account_id]=day.isoformat()
            data.setdefault('wealth_clock_events',[]).append(dict(account_id=context.account_id,
                from_day=expected_day,day=day.isoformat(),created_at=self._now().isoformat()))
            return reply(op,dict(day=day.isoformat(),notice=NOTICE))
        return self._lifecycle_write(context,op,params,apply)
