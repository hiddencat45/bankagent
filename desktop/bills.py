"""Read-only ledger view; filters operate on complete server-bounded account results."""
from datetime import date, timedelta
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QDialog, QDialogButtonBox)
from desktop.client import money

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
        title = QLabel('交易记录'); title.setObjectName('title'); layout.addWidget(title)
        layout.addWidget(QLabel('查看当前账户的账单与资金往来'))
        tabs = QHBoxLayout()
        self.all_tab, self.expense_tab = QPushButton('全部交易'), QPushButton('消费账单')
        for button in (self.all_tab, self.expense_tab):
            button.setCheckable(True); tabs.addWidget(button)
        tabs.addStretch(); layout.addLayout(tabs)
        self.all_tab.setChecked(True)
        self.all_tab.clicked.connect(lambda: self.select_tab(False))
        self.expense_tab.clicked.connect(lambda: self.select_tab(True))
        filters = QHBoxLayout()
        self.start, self.end = QDateEdit(), QDateEdit()
        for widget, label in ((self.start,'开始日期'), (self.end,'结束日期')):
            widget.setCalendarPopup(True); widget.setDisplayFormat('yyyy-MM-dd')
            widget.setAccessibleName(label); filters.addWidget(widget)
        self.kind, self.category = QComboBox(), QComboBox()
        self.kind.addItem('全部类型','')
        for key,value in KINDS.items(): self.kind.addItem(value,key)
        self.kind.setAccessibleName('交易类型'); self.category.setAccessibleName('交易分类')
        self.category.addItem('全部分类','')
        filters.addWidget(self.kind); filters.addWidget(self.category)
        self.search = QLineEdit(); self.search.setPlaceholderText('搜索商户或对方'); self.search.setAccessibleName('搜索商户或对方')
        filters.addWidget(self.search,1)
        layout.addLayout(filters)
        actions = QHBoxLayout()
        self.query, self.reset = QPushButton('查询 / 刷新'), QPushButton('重置筛选')
        self.query.setObjectName('primary'); actions.addWidget(self.query); actions.addWidget(self.reset); actions.addStretch()
        layout.addLayout(actions)
        self.query.clicked.connect(self.requested.emit); self.reset.clicked.connect(self.reset_filters)
        self.search.returnPressed.connect(self.apply_filters)
        self.kind.currentIndexChanged.connect(self.apply_filters); self.category.currentIndexChanged.connect(self.apply_filters)
        self.search.textChanged.connect(self.apply_filters)
        totals = QHBoxLayout(); self.totals=[]
        for _ in range(3):
            label=QLabel('—'); label.setObjectName('ledgerTotal'); totals.addWidget(label,1); self.totals.append(label)
        layout.addLayout(totals)
        note=QLabel('以下统计对应筛选结果。支出包含消费与转出；消费不包含转账。'); note.setWordWrap(True); layout.addWidget(note)
        self.table=QTableWidget(0,7)
        self.table.setHorizontalHeaderLabels(['日期时间','商户或对方','类型','分类','金额（元）','状态','操作'])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().hide(); self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(260); self.table.cellDoubleClicked.connect(lambda r,c:self.details(r))
        layout.addWidget(self.table)
        footer=QHBoxLayout(); self.note=QLabel('正在读取账本…'); self.note.setWordWrap(True); footer.addWidget(self.note,1)
        self.previous,self.next=QPushButton('上一页'),QPushButton('下一页'); self.page_label=QLabel('—')
        for widget in (self.previous,self.page_label,self.next):footer.addWidget(widget)
        self.previous.clicked.connect(lambda:self.turn(-1)); self.next.clicked.connect(lambda:self.turn(1))
        layout.addLayout(footer)

    def period(self):
        return self.start.date().toString('yyyy-MM-dd'), self.end.date().addDays(1).toString('yyyy-MM-dd')

    def clear(self, message='正在读取账本…'):
        self.data=None; self.rows=[]; self.table.setRowCount(0); self.note.setText(message)
        for label in self.totals:label.setText('—')
        self.previous.setEnabled(False); self.next.setEnabled(False); self.page_label.setText('—')

    def set_data(self, data, default=False):
        self.data=data
        if default or self.default_range is None:
            self.default_range=(data['start'],data['end'])
            self.start.setDate(QDate.fromString(data['start'],'yyyy-MM-dd'))
            self.end.setDate(QDate.fromString(data['end'],'yyyy-MM-dd').addDays(-1))
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
        outgoing=sum(r['amount_minor'] for r in self.rows if r['kind'] in {'EXPENSE','TRANSFER_OUT'})
        expense=sum(r['amount_minor'] for r in self.rows if r['kind']=='EXPENSE')
        for label,name,value in zip(self.totals,['收入','支出','其中消费'],[incoming,outgoing,expense]):label.setText(name+'\n¥ '+money(value))
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
                self.table.scrollToItem(self.table.item(index % 20, 0))
                return
        self.note.setText('当前日期范围中未找到该笔交易，请调整日期后查询；回执仍保留在助手中。')

    def render(self):
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
            for col,value in enumerate(values):
                item=QTableWidgetItem(value)
                if col==4:
                    item.setForeground(QColor('#16725b' if positive else '#ad4141'))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(index,col,item)
            button=QPushButton('详情'); button.clicked.connect(lambda checked=False,i=index:self.details(i)); self.table.setCellWidget(index,6,button)
        self.page_label.setText(str(self.page+1)+' / '+str(max(1,(len(self.rows)+19)//20)))
        self.previous.setEnabled(self.page>0); self.next.setEnabled((self.page+1)*20<len(self.rows))
        end=(date.fromisoformat(self.data['end'])-timedelta(days=1)).isoformat()
        self.note.setText(f"{self.data['start']} 至 {end} · 共 {len(self.rows)} 笔 · 当前账户实际账本" if self.rows else '当前筛选条件下没有交易。可以重置筛选或更改日期。')

    def details(self,index):
        row=self.rows[self.page*20+index]
        dialog=QDialog(self); dialog.setWindowTitle('交易详情'); dialog.resize(470,300); layout=QVBoxLayout(dialog)
        body=QLabel(f"{KINDS[row['kind']]} · ¥ {money(row['amount_minor'])}\n对方 / 商户：{row.get('counterparty_name') or row.get('merchant') or row['category']}\n时间：{row['occurred_at']}\n分类：{row['category']}\n状态：已入账")
        body.setTextFormat(Qt.TextFormat.PlainText); body.setWordWrap(True); layout.addWidget(body)
        from PySide6.QtWidgets import QPlainTextEdit
        refs=QPlainTextEdit(); refs.setReadOnly(True); refs.setPlainText('\n'.join(label+'：'+row[key] for key,label in [('transaction_id','流水编号'),('transfer_id','转账编号'),('related_transaction_id','关联流水'),('batch_id','批量编号')] if key in row))
        refs.hide(); toggle=QPushButton('展开流水编号'); toggle.setCheckable(True); toggle.toggled.connect(refs.setVisible)
        layout.addWidget(toggle); layout.addWidget(refs)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Close); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
        dialog.exec(); dialog.deleteLater()
