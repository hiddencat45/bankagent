"""Native wealth workspace. Every write emits an ordinary confirmed bank form."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTabWidget,
    QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QLineEdit,QComboBox,QFormLayout,QPlainTextEdit,QSizePolicy)
from desktop.client import money
from bankagent.banking.wealth import STATES, NOTICE


def label(value):
    w=QLabel(value); w.setWordWrap(True); w.setTextFormat(Qt.TextFormat.PlainText); return w


def table(headers):
    w=QTableWidget(0,len(headers)); w.setHorizontalHeaderLabels(headers)
    w.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    w.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    w.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    w.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    w.verticalHeader().hide(); w.verticalHeader().setDefaultSectionSize(56); w.setFixedHeight(260)
    return w


def fill(w,rows):
    w.setRowCount(len(rows))
    for i,row in enumerate(rows):
        for j,v in enumerate(row):
            item=QTableWidgetItem(str(v)); item.setToolTip(str(v)); w.setItem(i,j,item)


class WealthPage(QWidget):
    requested=Signal(str,dict)
    refresh_requested=Signal()
    geometry_changed=Signal()
    def __init__(self):
        super().__init__(); self.data=None; self.actor=None; self.profile_stamp=None; self.buttons=[]
        layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(14)
        heading=QHBoxLayout(); title=label('理财 · 模拟交易'); title.setObjectName('title'); heading.addWidget(title)
        heading.addStretch(); self.refresh=QPushButton('刷新理财'); self.refresh.clicked.connect(self.refresh_requested.emit); heading.addWidget(self.refresh)
        layout.addLayout(heading); layout.addWidget(label(NOTICE))
        self.summary=label('正在读取当前账户…'); self.summary.setObjectName('status'); layout.addWidget(self.summary)
        self.tabs=QTabWidget(); layout.addWidget(self.tabs)
        self.tabs.setStyleSheet('QTabBar::tab {padding:10px 18px; margin-right:5px; border-radius:5px; background:#e8efeb;} QTabBar::tab:selected {background:#195d48; color:white;} QTabWidget::pane {border:0;}')
        catalog=QWidget(); c=QVBoxLayout(catalog); c.setAlignment(Qt.AlignmentFlag.AlignTop); c.setSpacing(12)
        self.products=table(['产品／微众份额代码','管理人评级／起投','持有要求','需求筛选'])
        self.products.itemSelectionChanged.connect(self.product_detail); c.addWidget(self.products)
        self.product_text=QPlainTextEdit(); self.product_text.setReadOnly(True); self.product_text.setFixedHeight(130); c.addWidget(self.product_text)
        actions=QHBoxLayout(); self.buy_amount=QLineEdit(); self.buy_amount.setPlaceholderText('模拟申购金额（元）'); self.buy_amount.setAccessibleName('模拟申购金额'); actions.addWidget(self.buy_amount)
        self.buy=self.button('准备模拟申购',self.buy_selected); actions.addWidget(self.buy)
        self.compare=self.button('查看筛选结果',lambda:self.requested.emit('RECOMMEND_WEALTH',{})); actions.addWidget(self.compare); c.addLayout(actions)
        self.tabs.addTab(catalog,'产品与筛选')
        profile=QWidget(); f=QFormLayout(profile); self.fields={}
        for key,title in [('budget','理财总预算（元）'),('free_cash','扣除必要支出与备用金后的闲钱（元）'),('horizon_days','最早用钱前的天数')]:
            w=QLineEdit(); w.setAccessibleName(title); w.setMaxLength(12); f.addRow(title,w); self.fields[key]=w
        questions=[('purpose','这笔钱的用途',['闲置资金','必要支出']),('liquidity','到账要求',['可等待','当天到账','固定日期']),
            ('loss','能否承受本金亏损',['不能亏损','仅低风险','接受波动']),('income','收入状况',['稳定','不稳定']),
            ('debt','还款与资金来源',['无压力','有还款压力','借款理财']),('experience','非保本理财经验',['无经验','有经验']),
            ('priority','本次更看重什么',['风险优先','流动性优先','综合比较'])]
        for key,title,options in questions:
            w=QComboBox(); w.addItem('请选择',None)
            for option in options:w.addItem(option,option)
            w.setAccessibleName(title); self.fields[key]=w; f.addRow(title,w)
        f.addRow(label('本问卷仅作模拟需求筛选；不代替银行正式风险测评，不根据流水自动认定闲钱。保存需要本人确认。'))
        self.save=self.button('核对并保存问卷',self.save_profile); f.addRow(self.save); self.tabs.addTab(profile,'需求问卷')
        holdings=QWidget(); h=QVBoxLayout(holdings); h.setAlignment(Qt.AlignmentFlag.AlignTop)
        h.addWidget(label('每笔申购独立计算持有期。份额锁定后不能重复赎回；未解锁部分不会被自动赎回。'))
        self.lots=table(['产品','持有份额','可赎回份额','模拟可赎回日期']); h.addWidget(self.lots)
        row=QHBoxLayout(); self.sell_units=QLineEdit(); self.sell_units.setPlaceholderText('所选产品赎回份额（份）'); self.sell_units.setAccessibleName('模拟赎回份额'); row.addWidget(self.sell_units)
        self.sell=self.button('准备模拟赎回',self.sell_selected); row.addWidget(self.sell)
        self.sell_all=self.button('填入该产品全部可赎回份额',self.fill_redeemable); row.addWidget(self.sell_all); h.addLayout(row)
        self.tabs.addTab(holdings,'我的持仓')
        orders=QWidget(); o=QVBoxLayout(orders); o.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.orders=table(['订单号','产品／方向','申请数量','订单状态']); self.orders.itemSelectionChanged.connect(self.order_detail); o.addWidget(self.orders)
        self.order_text=QPlainTextEdit(); self.order_text.setReadOnly(True); self.order_text.setFixedHeight(145); o.addWidget(self.order_text)
        row=QHBoxLayout(); self.cancel=self.button('申请撤单',self.cancel_selected); row.addWidget(self.cancel)
        self.event=QComboBox(); self.event.addItems(['下一步','模拟超时','拒单','半数成交','延迟到账']); row.addWidget(self.event)
        self.step=self.button('准备订单演示动作',self.advance_order); row.addWidget(self.step); o.addLayout(row)
        row=QHBoxLayout(); row.addWidget(label('仅推进当前账户的演示日期，真实时间和其他账户不变：'))
        self.days=QComboBox(); self.days.addItems(['1','7','14']); row.addWidget(self.days)
        self.advance=self.button('准备推进日期',lambda:self.requested.emit('ADVANCE_WEALTH_DEMO',{'days':self.days.currentText()})); row.addWidget(self.advance); o.addLayout(row)
        self.tabs.addTab(orders,'订单与演示')
        self.feedback=label('请先填写问卷，再比较产品。'); layout.addWidget(self.feedback)
        self.tabs.currentChanged.connect(self.fit_tab)
        self.fit_tab()

    def fit_tab(self):
        for i in range(self.tabs.count()):
            self.tabs.widget(i).setSizePolicy(QSizePolicy.Policy.Preferred if i==self.tabs.currentIndex() else QSizePolicy.Policy.Ignored,
                QSizePolicy.Policy.Preferred if i==self.tabs.currentIndex() else QSizePolicy.Policy.Ignored)
        self.tabs.updateGeometry(); self.updateGeometry(); self.geometry_changed.emit()

    def button(self,title,slot):
        b=QPushButton(title); b.setObjectName('primary' if title in {'准备模拟申购','准备模拟赎回','核对并保存问卷'} else 'quietAction')
        b.clicked.connect(slot); self.buttons.append(b); return b

    def set_available(self,enabled):
        for w in self.buttons+[self.buy_amount,self.sell_units,self.event,self.days,*self.fields.values()]:w.setEnabled(enabled and self.data is not None)

    def clear(self):
        self.data=None; self.actor=None; self.profile_stamp=None
        for w in (self.products,self.lots,self.orders):w.setRowCount(0)
        for w in (self.product_text,self.order_text,self.buy_amount,self.sell_units):w.clear()
        for w in self.fields.values():
            if isinstance(w,QLineEdit):w.clear()
            else:w.setCurrentIndex(0)
        self.summary.setText('尚未读取当前账户理财数据。'); self.feedback.setText('请先填写问卷，再比较产品。')

    def set_data(self,data,actor):
        if actor!=self.actor:self.clear()
        selected=self.products.currentRow(); oid=self.selected_order().get('order_id') if self.selected_order() else None
        self.actor=actor; self.data=data
        self.summary.setText(f"演示日期 {data['day']}  ｜  可用 ¥{money(data['available_minor'])}  ｜  申购冻结 ¥{money(data['frozen_minor'])}  ｜  持仓 ¥{money(data['holdings_minor'])}  ｜  待到账 ¥{money(data['waiting_minor'])}")
        recommendations={r['product_code']:r for r in data['recommendations']}
        fill(self.products,[(p['short_name']+'\n'+p['code'],f"R{p['issuer_risk']} / {money(p['minimum_minor'])}元",
            f"最低{p['hold_days']}天" if p['hold_days'] else '不设置封闭期',
            ('模拟候选 · 真实渠道待核实' if recommendations[p['code']]['eligible'] else '不匹配，见下方理由') if p['code'] in recommendations else '先完善问卷') for p in data['products']])
        self.products.selectRow(max(0,selected))
        names={p['code']:p['short_name'] for p in data['products']}
        fill(self.lots,[(names[l['product_code']],money(l['units_minor']),money(l['redeemable_minor']),l['unlock_on']) for l in data['lots']])
        if data['lots']:self.lots.selectRow(0)
        fill(self.orders,[(v['order_id'],names[v['product_code']]+' / '+('申购' if v['side']=='BUY' else '赎回'),
            money(v['requested_minor'])+('元' if v['side']=='BUY' else '份'),STATES[v['state']]+('（部分成交）' if 0<v['filled_minor']<v['requested_minor'] else '')) for v in data['orders']])
        if data['orders']:self.orders.selectRow(next((i for i,v in enumerate(data['orders']) if v['order_id']==oid),0))
        profile=data.get('profile')
        if profile and profile['recorded_at']!=self.profile_stamp:
            for key,w in self.fields.items():
                value=profile['answers'].get(key)
                if key in {'budget','free_cash'}:value=money(profile['answers'][key+'_minor']).replace(',','')
                if isinstance(w,QLineEdit):w.setText(str(value))
                else:w.setCurrentIndex(w.findData(value))
            self.profile_stamp=profile['recorded_at']
        self.feedback.setText('问卷已确认；当前结果仅为模拟筛选，不是正式投资建议。' if data['profile_valid'] else '请填写或更新模拟需求问卷。')
        self.product_detail(); self.order_detail()

    def product_detail(self):
        i=self.products.currentRow()
        if self.data is None or not 0<=i<len(self.data['products']):return
        p=self.data['products'][i]; r=next((r for r in self.data['recommendations'] if r['product_code']==p['code']),None)
        self.product_text.setPlainText(p['name']+'\n管理人：'+p['issuer']+'；非保本。合同常规费用：'+p['fee']+
            '\n筛选依据：'+('；'.join(r['reasons']) if r else '问卷缺失或过期')+
            '\n微众在售、销售评级、实际到账和当前费率待核实。官方资料：\n'+p['source'])

    def save_profile(self):
        fields={k:(w.text().strip() if isinstance(w,QLineEdit) else w.currentData()) for k,w in self.fields.items()}
        if not all(fields.values()):self.feedback.setText('请逐项填写问卷，不能用默认答案代替你的选择。'); return
        self.requested.emit('SAVE_WEALTH_PROFILE',fields)

    def buy_selected(self):
        i=self.products.currentRow()
        if self.data and i>=0 and self.buy_amount.text().strip():
            self.requested.emit('SUBSCRIBE_WEALTH',{'product_name':self.data['products'][i]['code'],'amount':self.buy_amount.text().strip()})
        else:self.feedback.setText('请选择产品并输入申购金额。')

    def selected_lot(self):
        i=self.lots.currentRow(); return self.data['lots'][i] if self.data and 0<=i<len(self.data['lots']) else None

    def fill_redeemable(self):
        lot=self.selected_lot()
        if lot:
            amount=sum(l['redeemable_minor'] for l in self.data['lots'] if l['product_code']==lot['product_code'])
            self.sell_units.setText(money(amount).replace(',','')); self.feedback.setText('只填入所选产品已解锁且未冻结的份额；仍需核对确认。')

    def sell_selected(self):
        lot=self.selected_lot()
        if lot and self.sell_units.text().strip():
            self.requested.emit('REDEEM_WEALTH',{'product_name':lot['product_code'],'units':self.sell_units.text().strip()})
        else:self.feedback.setText('请选择持仓并输入赎回份额。')

    def selected_order(self):
        i=self.orders.currentRow(); return self.data['orders'][i] if self.data and 0<=i<len(self.data['orders']) else None

    def order_detail(self):
        order=self.selected_order()
        if not order:return
        self.order_text.setPlainText('规则版本：'+order['rule_version']+'；申请数量：'+money(order['requested_minor'])+
            '；已确认份额：'+money(order['filled_minor'])+'\n'+
            '\n'.join(e['day']+'  '+STATES[e['state']]+'  '+e['message'] for e in order['events']))

    def cancel_selected(self):
        order=self.selected_order()
        if order:self.requested.emit('CANCEL_WEALTH_ORDER',{'order_id':order['order_id']})

    def advance_order(self):
        order=self.selected_order()
        if order:self.requested.emit('ADVANCE_WEALTH_DEMO',{'order_id':order['order_id'],'event':self.event.currentText()})
