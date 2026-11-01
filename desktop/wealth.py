"""Native wealth workspace. Every write emits an ordinary confirmed bank form."""
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTabWidget,
    QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QLineEdit,QComboBox,QPlainTextEdit,QSizePolicy,QFrame,QDialog)
from desktop.client import money
from bankagent.banking.wealth import STATES, NOTICE
from desktop.wealth_widgets import ProductCards,ProfileDialog,WEALTH_STYLE,text


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
        self.onboarded=set();self.available=False;self.setStyleSheet(WEALTH_STYLE)
        layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(14)
        heading=QHBoxLayout(); title=text('理财','title');heading.addWidget(title);heading.addWidget(text('模拟账户','wealthTag'))
        heading.addStretch(); self.refresh=QPushButton('刷新理财'); self.refresh.clicked.connect(self.refresh_requested.emit); heading.addWidget(self.refresh)
        layout.addLayout(heading)
        layout.addWidget(text('从了解自己的需求开始，让每一笔安排更清楚。','wealthHint'))
        assets=QHBoxLayout();assets.setSpacing(14);self.asset_values={}
        for key,title in [('available_minor','可用资金（元）'),('holdings_minor','模拟持仓'),('frozen_minor','申购冻结'),('waiting_minor','赎回待到账')]:
            card=QFrame();card.setObjectName('wealthHero' if key=='available_minor' else 'wealthPanel')
            box=QVBoxLayout(card);box.setContentsMargins(20,18,20,18);box.addWidget(text(title,'wealthCaption'))
            value=text('—','wealthNumber');box.addWidget(value);self.asset_values[key]=value;assets.addWidget(card,2 if key=='available_minor' else 1)
        layout.addLayout(assets)
        self.summary=text('正在读取当前账户…','wealthCaption');layout.addWidget(self.summary)
        intro=QFrame();intro.setObjectName('wealthPanel');row=QHBoxLayout(intro);row.setContentsMargins(18,12,18,12)
        self.profile_hint=text('完善需求后，为你解释每款产品为什么匹配或不匹配。','wealthHint');row.addWidget(self.profile_hint,1)
        self.edit_profile=self.button('完善我的需求',self.open_profile);row.addWidget(self.edit_profile);layout.addWidget(intro)
        self.tabs=QTabWidget(); layout.addWidget(self.tabs)
        catalog=QWidget(); c=QVBoxLayout(catalog); c.setAlignment(Qt.AlignmentFlag.AlignTop); c.setSpacing(12)
        self.products=ProductCards()
        self.products.itemSelectionChanged.connect(self.product_detail); c.addWidget(self.products)
        selected=QFrame();selected.setObjectName('wealthPanel');selection=QVBoxLayout(selected);selection.setContentsMargins(18,14,18,14)
        detail_row=QHBoxLayout();self.product_text=text('请选择产品','wealthHint');detail_row.addWidget(self.product_text,1)
        self.details=self.button('产品详情 ↗',self.show_product_detail);detail_row.addWidget(self.details);selection.addLayout(detail_row)
        actions=QHBoxLayout(); self.buy_amount=QLineEdit(); self.buy_amount.setMaximumWidth(300);self.buy_amount.setPlaceholderText('模拟申购金额（元）'); self.buy_amount.setAccessibleName('模拟申购金额'); actions.addWidget(self.buy_amount)
        self.buy=self.button('准备模拟申购',self.buy_selected); actions.addWidget(self.buy)
        self.compare=self.button('比较匹配结果',self.compare_products); actions.addWidget(self.compare);actions.addStretch();selection.addLayout(actions);c.addWidget(selected)
        c.addWidget(text('真实产品公开资料 · 非保本；当前微众在售、销售评级、费率与到账安排待核实。','wealthCaption'))
        self.tabs.addTab(catalog,'产品浏览')
        self.questionnaire=ProfileDialog(self);self.fields=self.questionnaire.fields;self.save=self.questionnaire.save
        self.questionnaire.submitted.connect(lambda fields:self.requested.emit('SAVE_WEALTH_PROFILE',fields))
        profile=QFrame();profile.setObjectName('wealthPanel');f=QVBoxLayout(profile);f.setAlignment(Qt.AlignmentFlag.AlignTop);f.setContentsMargins(24,24,24,24)
        f.addWidget(text('我的理财需求','wealthName'));self.profile_text=text('尚未填写需求问卷。','wealthHint');f.addWidget(self.profile_text)
        f.addWidget(self.button('填写或更新需求',self.open_profile));f.addWidget(text('仅模拟需求筛选，不生成银行正式风险等级。修改后需要重新核对确认。','wealthCaption'))
        self.tabs.addTab(profile,'我的需求')
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
        row=QHBoxLayout(); self.cancel=self.button('申请撤单',self.cancel_selected); row.addWidget(self.cancel);row.addStretch()
        self.demo_toggle=QPushButton('展开演示控制');self.demo_toggle.setCheckable(True);row.addWidget(self.demo_toggle);o.addLayout(row)
        demo=QFrame();demo.setObjectName('wealthPanel');demo_layout=QVBoxLayout(demo);demo.hide()
        self.demo_toggle.toggled.connect(lambda show:(demo.setVisible(show),self.demo_toggle.setText('收起演示控制' if show else '展开演示控制'),self.fit_tab()))
        row=QHBoxLayout()
        self.event=QComboBox(); self.event.addItems(['下一步','模拟超时','拒单','半数成交','延迟到账']); row.addWidget(self.event)
        self.step=self.button('准备订单演示动作',self.advance_order); row.addWidget(self.step); demo_layout.addLayout(row)
        row=QHBoxLayout(); row.addWidget(label('仅推进当前账户的演示日期，真实时间和其他账户不变：'))
        self.days=QComboBox(); self.days.addItems(['1','7','14']); row.addWidget(self.days)
        self.advance=self.button('准备推进日期',lambda:self.requested.emit('ADVANCE_WEALTH_DEMO',{'days':self.days.currentText()})); row.addWidget(self.advance);demo_layout.addLayout(row);o.addWidget(demo)
        self.tabs.addTab(orders,'订单记录')
        self.feedback=label('请先填写问卷，再比较产品。'); layout.addWidget(self.feedback)
        self.tabs.currentChanged.connect(self.fit_tab)
        self.fit_tab()

    def maybe_onboard(self):
        if not self.isVisible() or not self.available or not self.data or self.data['profile_valid']:return
        key=(self.actor[0] or self.actor[1],(self.data.get('profile') or {}).get('expires_on'))
        if key not in self.onboarded:
            self.onboarded.add(key);self.open_profile()

    def defer_onboarding(self):
        if self.data and self.actor:
            self.onboarded.add((self.actor[0] or self.actor[1], (self.data.get('profile') or {}).get('expires_on')))

    def showEvent(self,event):
        super().showEvent(event);QTimer.singleShot(0,self.maybe_onboard)

    def open_profile(self):
        if self.available and self.data and not self.questionnaire.isVisible():self.questionnaire.open()

    def require_profile(self):
        if self.data and self.data['profile_valid']:return True
        self.open_profile();return False

    def compare_products(self):
        if self.require_profile():self.requested.emit('RECOMMEND_WEALTH',{})

    def fit_tab(self):
        for i in range(self.tabs.count()):
            self.tabs.widget(i).setSizePolicy(QSizePolicy.Policy.Preferred if i==self.tabs.currentIndex() else QSizePolicy.Policy.Ignored,
                QSizePolicy.Policy.Preferred if i==self.tabs.currentIndex() else QSizePolicy.Policy.Ignored)
        self.tabs.updateGeometry(); self.updateGeometry(); self.geometry_changed.emit()

    def button(self,title,slot):
        b=QPushButton(title); b.setObjectName('primary' if title in {'准备模拟申购','准备模拟赎回','核对并保存问卷'} else 'quietAction')
        b.clicked.connect(slot); self.buttons.append(b); return b

    def set_available(self,enabled):
        self.available=enabled
        for w in self.buttons+[self.buy_amount,self.sell_units,self.event,self.days,*self.fields.values()]:w.setEnabled(enabled and self.data is not None)
        QTimer.singleShot(0,self.maybe_onboard)

    def clear(self):
        self.questionnaire.reject()
        self.data=None; self.actor=None; self.profile_stamp=None
        for w in (self.products,self.lots,self.orders):w.setRowCount(0)
        for w in (self.product_text,self.order_text,self.buy_amount,self.sell_units):w.clear()
        for w in self.fields.values():
            if isinstance(w,QLineEdit):w.clear()
            else:w.setCurrentIndex(0)
        self.summary.setText('尚未读取当前账户理财数据。'); self.feedback.setText('请先填写问卷，再比较产品。')
        for value in self.asset_values.values():value.setText('—')
        self.profile_text.setText('尚未填写需求问卷。');self.profile_hint.setText('完善需求后，再比较产品。');self.edit_profile.setText('完善我的需求')

    def set_data(self,data,actor):
        if actor!=self.actor:self.clear()
        selected=self.products.currentRow(); oid=self.selected_order().get('order_id') if self.selected_order() else None
        self.actor=actor; self.data=data
        for key,value in self.asset_values.items():value.setText(money(data[key]))
        self.summary.setText(f"演示日期 {data['day']}  ·  模拟净值1元，不计收益、亏损与费用。")
        recommendations={r['product_code']:r for r in data['recommendations']}
        self.products.populate(data['products'],recommendations)
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
        valid=data['profile_valid'];self.edit_profile.setText('更新我的需求' if valid else '完善我的需求')
        self.profile_hint.setText('需求已确认 · 可查看每款产品的匹配理由。' if valid else '问卷已过期，请更新需求。' if profile else '还不了解你的需求 · 完成问卷后再进行匹配。')
        if profile:
            a=profile['answers'];self.profile_text.setText(f"总预算 {money(a['budget_minor'])} 元   ·   闲置资金 {money(a['free_cash_minor'])} 元\n最早 {a['horizon_days']} 天后用钱\n\n"+
                ' / '.join(a[k] for k in ('purpose','liquidity','loss','income','debt','experience','priority'))+f"\n\n有效期至 {profile['expires_on']}"+('（已过期）' if not valid else ''))
        self.feedback.setText('问卷已确认；当前结果仅为模拟筛选，不是正式投资建议。' if data['profile_valid'] else '请填写或更新模拟需求问卷。')
        self.product_detail(); self.order_detail();self.fit_tab()

    def product_detail(self):
        i=self.products.currentRow()
        if self.data is None or not 0<=i<len(self.data['products']):return
        p=self.data['products'][i]; r=next((r for r in self.data['recommendations'] if r['product_code']==p['code']),None)
        self.product_text.setText('已选：'+p['short_name']+'\n'+('；'.join(r['reasons']) if r else '填写需求后，可查看匹配理由。'))

    def show_product_detail(self):
        if not self.data or self.products.currentRow()<0:return
        from html import escape
        p=self.data['products'][self.products.currentRow()]
        dialog=QDialog(self);dialog.setWindowTitle('产品资料');dialog.resize(600,480);box=QVBoxLayout(dialog);box.setContentsMargins(24,24,24,24);box.setSpacing(18)
        box.addWidget(text(p['name'],'wealthName'));box.addWidget(text('份额代码 '+p['code'],'wealthCaption'))
        box.addWidget(text(f"管理人：{p['issuer']}  ·  R{p['issuer_risk']}  ·  非保本\n合同常规费用：{p['fee']}\n真实渠道在售、评级、实际到账与当前费率待核实。"))
        source=QLabel('<a href="'+escape(p['source'],quote=True)+'">查看官方产品说明书 ↗</a>');source.setOpenExternalLinks(True);box.addWidget(source)
        box.addWidget(text(NOTICE,'wealthHint'));close=QPushButton('知道了');close.clicked.connect(dialog.accept);box.addWidget(close)
        dialog.exec();dialog.deleteLater()

    def buy_selected(self):
        if not self.require_profile():return
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
