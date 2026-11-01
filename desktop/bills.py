"""Read-only ledger view; filters operate on complete server-bounded account results."""
from datetime import date, timedelta
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QPlainTextEdit, QBoxLayout, QScrollArea, QGridLayout)
from desktop.client import money
from desktop.icons import icon

KINDS = {'INCOME':'入账', 'TRANSFER_IN':'转入', 'EXPENSE':'消费', 'TRANSFER_OUT':'转出'}

class BillsPage(QWidget):
    requested = Signal()

    def __init__(self):
        super().__init__()
        self.data = None
        self.default_range = None
        self.rows = []
        self.page = 0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(16)
        header=QHBoxLayout()
        title = QLabel('交易记录'); title.setObjectName('title'); header.addWidget(title)
        subtitle=QLabel('查询和管理您的账户交易明细'); subtitle.setObjectName('muted'); header.addWidget(subtitle)
        header.addStretch()
        self.account_button=QPushButton('正在读取卡片…'); self.account_button.setIcon(icon('card'))
        self.account_button.setObjectName('ledgerAccount'); self.account_button.setAccessibleName('切换账单账户')
        header.addWidget(self.account_button); layout.addLayout(header)
        summary = QFrame(); summary.setObjectName('ledgerSummary')
        totals = QHBoxLayout(summary); totals.setContentsMargins(22,20,22,20); self.totals=[]
        for i,symbol in enumerate(('incoming','outgoing','card')):
            if i:
                divider=QFrame(); divider.setObjectName('summaryDivider'); divider.setFixedWidth(1); totals.addWidget(divider)
            mark=QLabel(); mark.setPixmap(icon(symbol,28,'#ffffff').pixmap(28,28)); mark.setObjectName('summaryIcon'); mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
            mark.setFixedSize(48,48); totals.addWidget(mark)
            label=QLabel('—'); label.setObjectName('ledgerTotal'); totals.addWidget(label,1); self.totals.append(label)
        layout.addWidget(summary)
        self.body = QBoxLayout(QBoxLayout.Direction.LeftToRight); self.body.setSpacing(14)
        self.list_card=QFrame(); self.list_card.setObjectName('ledgerList')
        listing=QVBoxLayout(self.list_card); listing.setContentsMargins(18,18,18,16); listing.setSpacing(16)
        tabs = QHBoxLayout()
        self.all_tab, self.expense_tab = QPushButton('全部交易'), QPushButton('消费账单')
        for button in (self.all_tab, self.expense_tab):
            button.setObjectName('ledgerTab')
            button.setCheckable(True); tabs.addWidget(button)
        tabs.addStretch()
        self.month=QComboBox(); self.month.setAccessibleName('账单月份'); self.month.setMinimumWidth(155)
        self.month.currentIndexChanged.connect(self.choose_month); tabs.addWidget(self.month)
        listing.addLayout(tabs)
        self.all_tab.setChecked(True)
        self.all_tab.clicked.connect(lambda: self.select_tab(False))
        self.expense_tab.clicked.connect(lambda: self.select_tab(True))
        self.date_range=QWidget(); dates=QHBoxLayout(self.date_range); dates.setContentsMargins(0,0,0,0)
        self.start, self.end = QDateEdit(), QDateEdit()
        for widget, label in ((self.start,'开始日期'), (self.end,'结束日期')):
            widget.setCalendarPopup(True); widget.setDisplayFormat('yyyy-MM-dd')
            widget.setAccessibleName(label); dates.addWidget(QLabel(label)); dates.addWidget(widget)
        listing.addWidget(self.date_range); self.date_range.hide()
        filters=QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText('搜索商户或对方'); self.search.setAccessibleName('搜索商户或对方')
        self.search.setMinimumWidth(130); filters.addWidget(self.search,1)
        self.kind, self.category = QComboBox(), QComboBox()
        self.kind.addItem('全部类型','')
        for key,value in KINDS.items(): self.kind.addItem(value,key)
        self.kind.setAccessibleName('交易类型'); self.category.setAccessibleName('交易分类')
        self.category.addItem('全部分类','')
        filters.addWidget(self.kind); filters.addWidget(self.category)
        self.query, self.reset = QPushButton('筛选'), QPushButton('重置筛选')
        self.query.setObjectName('primary')
        self.reset.setObjectName('quietAction'); filters.addWidget(self.query); listing.addLayout(filters)
        self.query.clicked.connect(self.requested.emit); self.reset.clicked.connect(self.reset_filters)
        self.search.returnPressed.connect(self.apply_filters)
        self.kind.currentIndexChanged.connect(self.apply_filters); self.category.currentIndexChanged.connect(self.apply_filters)
        self.search.textChanged.connect(self.apply_filters)
        note=QLabel('汇总对应当前筛选 · 入账包含转入，转出不含商户消费'); note.setObjectName('muted'); note.setWordWrap(True); listing.addWidget(note)
        self.table=QTableWidget(0,7)
        self.table.setObjectName('ledgerTable')
        self.table.setHorizontalHeaderLabels(['交易时间','对方 / 商户','类型','分类','金额（元）','状态','操作'])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().hide(); self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5,QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5,80)
        self.table.setMinimumHeight(300); self.table.cellDoubleClicked.connect(lambda r,c:self.details(r))
        self.table.cellClicked.connect(lambda r,c:self.details(r))
        self.table.currentCellChanged.connect(lambda r,c,old_r,old_c:self.details(r))
        self.table.setColumnHidden(3,True)
        self.table.setColumnHidden(6,True)
        listing.addWidget(self.table,1)
        self.body.addWidget(self.list_card,7)
        self.inspector = QFrame(); self.inspector.setObjectName('transactionInspector')
        self.inspector.setMinimumWidth(285)
        detail_layout = QVBoxLayout(self.inspector); detail_layout.setContentsMargins(20,20,20,20); detail_layout.setSpacing(16)
        heading_row=QHBoxLayout(); heading=QLabel('交易详情'); heading.setObjectName('sectionTitle'); heading_row.addWidget(heading)
        heading_row.addStretch(); close=QPushButton('×'); close.setObjectName('quietAction'); close.setAccessibleName('清除交易详情')
        close.clicked.connect(self.clear_details); heading_row.addWidget(close); detail_layout.addLayout(heading_row)
        self.detail_mark=QLabel('—'); self.detail_mark.setObjectName('detailMark'); self.detail_mark.setFixedSize(54,54)
        self.detail_mark.setAlignment(Qt.AlignmentFlag.AlignCenter); detail_layout.addWidget(self.detail_mark,0,Qt.AlignmentFlag.AlignHCenter)
        self.detail_body=QLabel('选择一笔交易查看详情'); self.detail_body.setWordWrap(True)
        self.detail_body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_body.setTextFormat(Qt.TextFormat.PlainText); self.detail_body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        detail_layout.addWidget(self.detail_body)
        self.detail_amount=QLabel('—'); self.detail_amount.setObjectName('detailAmount'); self.detail_amount.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_layout.addWidget(self.detail_amount)
        fields=QGridLayout(); fields.setVerticalSpacing(18); self.detail_values={}
        for index,name in enumerate(('交易时间','交易类型','交易状态','对方 / 商户','交易分类','备注')):
            caption=QLabel(name); caption.setObjectName('muted'); fields.addWidget(caption,index,0)
            value=QLabel('—'); value.setWordWrap(True); value.setTextFormat(Qt.TextFormat.PlainText)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
            fields.addWidget(value,index,1); self.detail_values[name]=value
        detail_layout.addLayout(fields); detail_layout.addStretch()
        self.refs=QPlainTextEdit(); self.refs.setReadOnly(True); self.refs.setMaximumHeight(120); self.refs.hide()
        self.refs_toggle=QPushButton('展开流水编号'); self.refs_toggle.setCheckable(True); self.refs_toggle.toggled.connect(self.refs.setVisible)
        detail_layout.addWidget(self.refs_toggle); detail_layout.addWidget(self.refs)
        self.body.addWidget(self.inspector,3); layout.addLayout(self.body)
        footer=QHBoxLayout(); self.note=QLabel('正在读取账本…'); self.note.setWordWrap(True); footer.addWidget(self.note,1)
        self.previous,self.next=QPushButton('上一页'),QPushButton('下一页'); self.page_label=QLabel('—')
        footer.addWidget(self.reset)
        for widget in (self.previous,self.page_label,self.next):footer.addWidget(widget)
        footer.addSpacing(64)  # Keep pagination clear of the floating assistant entry.
        self.previous.clicked.connect(lambda:self.turn(-1)); self.next.clicked.connect(lambda:self.turn(1))
        layout.addLayout(footer)

    def choose_month(self):
        value=self.month.currentData()
        self.date_range.setVisible(value == 'custom')
        if value and value != 'custom':
            start=QDate.fromString(value,'yyyy-MM-dd')
            self.start.setDate(start); self.end.setDate(start.addMonths(1).addDays(-1)); self.requested.emit()

    def sync_month(self):
        self.month.blockSignals(True); self.month.clear()
        base=QDate.fromString(self.default_range[0],'yyyy-MM-dd'); base=QDate(base.year(),base.month(),1)
        for offset in range(12):
            value=base.addMonths(-offset); self.month.addItem(value.toString('yyyy年M月'),value.toString('yyyy-MM-dd'))
        self.month.addItem('自定义日期范围','custom')
        current=self.start.date(); index=self.month.findData(current.toString('yyyy-MM-dd'))
        whole=current.day()==1 and self.end.date()==current.addMonths(1).addDays(-1)
        self.month.setCurrentIndex(index if whole and index>=0 else self.month.count()-1)
        self.date_range.setVisible(not whole or index<0); self.month.blockSignals(False)

    def period(self):
        return self.start.date().toString('yyyy-MM-dd'), self.end.date().addDays(1).toString('yyyy-MM-dd')

    def clear(self, message='正在读取账本…'):
        self.data=None; self.rows=[]; self.table.setRowCount(0); self.note.setText(message)
        self.clear_details()
        for label in self.totals:label.setText('—')
        self.previous.setEnabled(False); self.next.setEnabled(False); self.page_label.setText('—')

    def set_data(self, data, default=False):
        self.data=data
        if default or self.default_range is None:
            self.default_range=(data['start'],data['end'])
            self.start.setDate(QDate.fromString(data['start'],'yyyy-MM-dd'))
            self.end.setDate(QDate.fromString(data['end'],'yyyy-MM-dd').addDays(-1))
        self.sync_month()
        choice=self.category.currentData()
        self.category.blockSignals(True); self.category.clear(); self.category.addItem('全部分类','')
        for category in sorted({r['category'] for r in data['transactions']}): self.category.addItem(category,category)
        self.category.setCurrentIndex(max(0,self.category.findData(choice))); self.category.blockSignals(False)
        self.apply_filters()

    def select_tab(self, expense):
        self.all_tab.setChecked(not expense); self.expense_tab.setChecked(expense)
        self.kind.setCurrentIndex(self.kind.findData('EXPENSE') if expense else 0)
        self.kind.setEnabled(not expense); self.apply_filters()

    def reset_filters(self):
        self.search.clear(); self.category.setCurrentIndex(0); self.select_tab(False)
        if self.default_range:
            self.start.setDate(QDate.fromString(self.default_range[0],'yyyy-MM-dd'))
            self.end.setDate(QDate.fromString(self.default_range[1],'yyyy-MM-dd').addDays(-1))
        self.requested.emit()

    def apply_filters(self):
        if self.data is None:return
        kind,category,search=self.kind.currentData(),self.category.currentData(),self.search.text().strip().casefold()
        self.rows=sorted([r for r in self.data['transactions'] if (not kind or r['kind']==kind)
            and (not category or r['category']==category)
            and (not search or search in ((r.get('merchant') or '')+' '+(r.get('counterparty_name') or '')).casefold())],
            key=lambda r:(r['occurred_at'],r['transaction_id']),reverse=True)
        incoming=sum(r['amount_minor'] for r in self.rows if r['kind'] in {'INCOME','TRANSFER_IN'})
        outgoing=sum(r['amount_minor'] for r in self.rows if r['kind']=='TRANSFER_OUT')
        expense=sum(r['amount_minor'] for r in self.rows if r['kind']=='EXPENSE')
        for label,name,value in zip(self.totals,['入账','转出','消费'],[incoming,outgoing,expense]):
            label.setText('<span style="font-size:14px;font-weight:400">'+name+'</span><br/>'
                          '<span style="font-size:26px;font-weight:600">¥ '+money(value)+'</span>')
        self.page=0; self.render()

    def turn(self,offset):
        self.page+=offset; self.render()

    def focus_receipt(self, data):
        ids = {data.get('transaction_id')}
        ids.update(row.get('transaction_id') for row in data.get('items', []))
        for index, row in enumerate(self.rows):
            if row['transaction_id'] in ids or (data.get('batch_id') and row.get('batch_id') == data['batch_id']):
                self.page = index // 20; self.render()
                self.table.selectRow(index % 20)
                self.details(index % 20)
                self.table.scrollToItem(self.table.item(index % 20, 0))
                return
        self.note.setText('当前日期范围中未找到该笔交易，请调整日期后查询；回执仍保留在助手中。')

    def render(self):
        self.clear_details()
        # Qt defers deletion of replaced cell widgets; hide them before repopulating.
        for index in range(self.table.rowCount()):
            previous = self.table.cellWidget(index, 6)
            if previous:
                previous.hide()
        self.table.setRowCount(0)
        rows=self.rows[self.page*20:(self.page+1)*20]; self.table.setRowCount(len(rows))
        for index,row in enumerate(rows):
            positive=row['kind'] in {'INCOME','TRANSFER_IN'}
            values=[row['occurred_at'][:16].replace('T',' '),row.get('counterparty_name') or row.get('merchant') or row['category'],
                KINDS[row['kind']],row['category'],('+' if positive else '−')+money(row['amount_minor']),'已入账']
            if row['category']=='模拟入金': values[1]='模拟入金'
            for col,value in enumerate(values):
                item=QTableWidgetItem(value)
                item.setToolTip(value if col!=1 else (row.get('counterparty_name') or row.get('merchant') or row['category']))
                if col==2: item.setIcon(icon('incoming' if positive else 'outgoing' if row['kind']=='TRANSFER_OUT' else 'card',18,'#128247' if positive else '#e47724'))
                if col==4:
                    item.setForeground(QColor('#148247' if positive else '#172b24'))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
                    font=item.font(); font.setWeight(QFont.Weight.DemiBold); item.setFont(font)
                if col==5:
                    item.setForeground(QColor('#18734c')); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(index,col,item)
            badge_cell=QWidget(); badge_cell.setObjectName('statusCell'); badge_layout=QHBoxLayout(badge_cell)
            badge_layout.setContentsMargins(4,12,4,12); badge=QLabel('已入账'); badge.setObjectName('ledgerStatus')
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter); badge_layout.addWidget(badge)
            self.table.setCellWidget(index,5,badge_cell)
        self.page_label.setText(str(self.page+1)+' / '+str(max(1,(len(self.rows)+19)//20)))
        self.previous.setEnabled(self.page>0); self.next.setEnabled((self.page+1)*20<len(self.rows))
        end=(date.fromisoformat(self.data['end'])-timedelta(days=1)).isoformat()
        self.note.setText(f"{self.data['start']} 至 {end} · 共 {len(self.rows)} 笔 · 当前账户实际账本" if self.rows else '当前筛选条件下没有交易。可以重置筛选或更改日期。')

    def details(self,index):
        if index < 0 or self.page*20+index >= len(self.rows): return
        row=self.rows[self.page*20+index]
        self.detail_mark.setPixmap(icon('check',30,'#128146').pixmap(30,30)); self.detail_body.setText('交易已入账')
        positive=row['kind'] in {'INCOME','TRANSFER_IN'}
        self.detail_amount.setText(('＋' if positive else '−')+'¥ '+money(row['amount_minor']))
        values=[row['occurred_at'][:16].replace('T',' '),KINDS[row['kind']],'已入账',
            row.get('counterparty_name') or row.get('merchant') or row['category'],row['category'],
            '本机测试资金，非真实存款' if row['category']=='模拟入金' else '—']
        for widget,value in zip(self.detail_values.values(),values): widget.setText(value)
        self.refs.setPlainText('\n'.join(label+'：'+row[key] for key,label in [('transaction_id','流水编号'),('transfer_id','转账编号'),('related_transaction_id','关联流水'),('batch_id','批量编号')] if key in row))
        self.refs_toggle.setEnabled(True)
        self.table.selectRow(index)

    def clear_details(self):
        self.detail_body.setText('选择一笔交易查看详情')
        self.detail_body.setMinimumHeight(0)
        self.detail_mark.setText('—'); self.detail_amount.setText('—')
        for value in self.detail_values.values(): value.setText('—')
        self.refs.clear(); self.refs_toggle.setChecked(False); self.refs_toggle.setEnabled(False)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        wide=self.width() >= 900
        self.body.setDirection(QBoxLayout.Direction.LeftToRight if wide else QBoxLayout.Direction.TopToBottom)
        self.inspector.setMaximumWidth(355 if wide else 16777215)
