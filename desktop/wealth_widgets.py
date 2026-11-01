"""Native wealth cards and a nonblocking, explicitly confirmed onboarding form."""
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (QWidget,QFrame,QLabel,QPushButton,QVBoxLayout,QHBoxLayout,
    QDialog,QLineEdit,QComboBox,QFormLayout,QStackedWidget,QScrollArea,QSizePolicy,QGridLayout)
from desktop.theme import STYLE
from desktop.wealth_product_card import ProductSummary, ProductRiskNote

WEALTH_STYLE='''
QFrame#wealthPanel {background:white;border:1px solid #e0e8e2;border-radius:14px;}
QFrame#wealthPanel QLabel {background:transparent;}
QFrame#wealthHero {background:#184f40;border-radius:14px;}
QFrame#wealthHero QLabel {background:transparent;color:white;}
QLabel#wealthCaption {color:#718479;font-size:12px;}
QLabel#wealthNumber {font-size:26px;font-weight:600;}
QLabel#wealthYield {color:#ad5835;font-size:32px;font-weight:600;}
QLabel#wealthName {font-size:18px;font-weight:600;}
QLabel#wealthTag {background:#eaf3ec;color:#336751;border-radius:5px;padding:4px 8px;font-size:12px;}
QLabel#wealthHint {color:#667b70;font-size:13px;}
QFrame#wealthProduct {background:white;border:1px solid #dfe7e1;border-radius:14px;}
QFrame#wealthProduct[selected="true"] {background:#f2f8f3;border:2px solid #398264;}
QFrame#wealthProduct QLabel {background:transparent;}
QTabWidget::pane {border:0;}
QTabBar::tab {background:transparent;color:#75867d;padding:12px 18px;margin-right:12px;border-bottom:2px solid transparent;}
QTabBar::tab:selected {color:#195a43;border-bottom:2px solid #287453;font-weight:600;}
QDialog QPushButton#quietAction {color:#3c6756;background:transparent;}
QDialog QPushButton#quietAction:hover {background:#e5eee7;}
'''


def text(value,name=''):
    w=QLabel(value);w.setWordWrap(True);w.setTextFormat(Qt.TextFormat.PlainText)
    if name:w.setObjectName(name)
    return w


class ProductCards(QWidget):
    itemSelectionChanged=Signal()
    geometryChanged=Signal()
    def __init__(self):
        super().__init__();self.row=-1;self.cards=[];self.select_buttons=[];self.page=0
        self.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Fixed)
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0);outer.setSpacing(12)
        pager=QHBoxLayout();self.count=text('','wealthHint');pager.addWidget(self.count);pager.addStretch()
        self.previous=QPushButton('上一页');self.next=QPushButton('下一页')
        self.previous.clicked.connect(lambda:self.show_page(self.page-1));self.next.clicked.connect(lambda:self.show_page(self.page+1))
        pager.addWidget(self.previous);pager.addWidget(self.next);outer.addLayout(pager)
        self.box=QGridLayout();self.box.setContentsMargins(0,0,0,0);self.box.setSpacing(14);outer.addLayout(self.box)
        for col in range(3):self.box.setColumnStretch(col,1)

    def rowCount(self):return len(self.cards)
    def currentRow(self):return self.row
    def setRowCount(self,count):
        assert count==0
        while self.box.count():
            self.box.takeAt(0)
        for w in self.cards:w.hide();w.deleteLater()
        self.cards=[];self.select_buttons=[];self.row=-1
        self.show_page(0)

    def show_page(self,page):
        total=max(1,(len(self.cards)+5)//6);self.page=max(0,min(page,total-1))
        while self.box.count():self.box.takeAt(0).widget().hide()
        visible=self.cards[self.page*6:self.page*6+6]
        columns=2 if self.width()>=760 and len(visible)>1 else 1
        self.columns=columns
        for col in range(3):self.box.setColumnStretch(col,1 if col<columns else 0)
        for i,card in enumerate(visible):
            self.box.addWidget(card,i//columns,i%columns);card.show()
        self.count.setText(f'{len(self.cards)} 款产品 · 第 {self.page+1}/{total} 页')
        self.previous.setEnabled(self.page>0);self.next.setEnabled(self.page<total-1)
        self.updateGeometry();self.geometryChanged.emit()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        columns=2 if self.width()>=760 and len(self.cards[self.page*6:self.page*6+6])>1 else 1
        if columns!=getattr(self,'columns',None):
            QTimer.singleShot(0,lambda:self.show_page(self.page))

    def refresh_geometry(self):
        self.layout().invalidate()
        self.updateGeometry()
        self.geometryChanged.emit()

    def populate(self,products,recommendations):
        selected=max(0,self.row);self.setRowCount(0)
        for i,p in enumerate(products):
            card=QFrame(self);card.hide();card.setObjectName('wealthProduct');box=QVBoxLayout(card)
            box.setContentsMargins(20,20,20,16);box.setSpacing(12)
            box.addWidget(ProductSummary(p))
            r=recommendations.get(p['code'])
            status='待完善需求' if r is None else r.get('comparison_group','符合模拟初筛' if r['eligible'] else '暂不匹配')
            if r and r.get('recommendation_rank'):status=f"推荐 {r['recommendation_rank']} · {r['recommendation_label']}"
            box.addWidget(text(status,'wealthHint'))
            box.addStretch()
            risk=ProductRiskNote()
            risk.geometryChanged.connect(lambda:QTimer.singleShot(0,self.refresh_geometry))
            box.addWidget(risk)
            button=QPushButton('选择产品');button.setCheckable(True)
            button.clicked.connect(lambda checked=False,row=i:self.selectRow(row))
            button.setAccessibleName('选择'+p['short_name']);box.addWidget(button)
            self.cards.append(card);self.select_buttons.append(button)
        self.show_page(selected//6)
        self.selectRow(min(selected,len(self.cards)-1))

    def selectRow(self,row):
        if not 0<=row<len(self.cards):return
        self.row=row
        if row//6!=self.page:self.show_page(row//6)
        for i,(card,button) in enumerate(zip(self.cards,self.select_buttons)):
            card.setProperty('selected',i==row);card.style().unpolish(card);card.style().polish(card)
            button.setChecked(i==row);button.setText('已选择' if i==row else '选择产品')
        self.itemSelectionChanged.emit()


class ProfileDialog(QDialog):
    submitted=Signal(dict)
    def __init__(self,parent):
        super().__init__(parent);self.setWindowTitle('了解你的理财需求');self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setStyleSheet(STYLE+WEALTH_STYLE);self.resize(620,650)
        outer=QVBoxLayout(self);outer.setContentsMargins(28,24,28,24);outer.setSpacing(14)
        outer.addWidget(text('查看和修改理财需求','title'))
        outer.addWidget(text('修改后先核对再保存。明确日期优先；修改相对天数会清除原日期。仅模拟需求筛选。','wealthHint'))
        self.progress=text('','wealthTag');outer.addWidget(self.progress)
        self.pages=QStackedWidget();self.fields={}
        definitions=[[
            ('budget','计划投入多少（元）',None),('free_cash','扣除必要支出和备用金后的闲钱（元）',None),
            ('horizon_days','最早多久后会用到这笔钱（天）',None),
            ('purpose','这笔钱的用途',['闲置资金','必要支出']),('liquidity','到账要求',['可等待','当天到账','固定日期']),
            ('need_on','明确用钱日期（YYYY-MM-DD，可选）',None),
            ('early_redemption','固定日期时能否提前赎回',['可以','不可以','不确定']),
            ('reserve','是否已预留必要支出和备用金',['已预留','未预留','不确定'])],
            [('loss','能否承受本金亏损',['不能亏损','仅低风险','接受小幅亏损','接受波动','不确定']),('income','收入状况',['稳定','不稳定','不确定']),
             ('debt','还款与资金来源',['无压力','有还款压力','借款理财']),('experience','非保本理财经验',['无经验','有经验']),
             ('impact','亏损或延期会影响生活或还款吗',['会','不会','不确定']),
             ('loss_acceptance','仅低风险时，是否接受本金亏损',['可以','不可以','不确定']),
             ('priority','这次更看重什么',['风险优先','流动性优先','综合比较'])]]
        self.groups=[]
        for questions in definitions:
            page=QWidget();form=QFormLayout(page);form.setVerticalSpacing(8)
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows);self.groups.append([q[0] for q in questions])
            for key,title,options in questions:
                w=QComboBox() if options else QLineEdit();w.setAccessibleName(title)
                if options:
                    w.addItem('请选择',None)
                    for option in options:w.addItem(option,option)
                else:w.setMaxLength(12);w.setPlaceholderText('请填写')
                self.fields[key]=w;form.addRow(title,w)
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(page);self.pages.addWidget(scroll)
        self.fields['horizon_days'].textEdited.connect(lambda _:self.fields['need_on'].clear())
        outer.addWidget(self.pages,1);self.error=text('','error');outer.addWidget(self.error)
        row=QHBoxLayout();self.later=QPushButton('稍后填写');self.later.setObjectName('quietAction');self.later.clicked.connect(self.reject);row.addWidget(self.later);row.addStretch()
        self.back=QPushButton('上一步');self.back.setObjectName('quietAction');self.back.clicked.connect(lambda:self.step(0));row.addWidget(self.back)
        self.next=QPushButton('下一步');self.next.setObjectName('primary');self.next.clicked.connect(self.advance);row.addWidget(self.next)
        self.save=QPushButton('核对我的需求');self.save.setObjectName('primary');self.save.clicked.connect(self.submit);row.addWidget(self.save)
        outer.addLayout(row);self.step(0)

    def values(self):
        from bankagent.banking.wealth import PROFILE_OPTIONAL
        values={k:(w.text().strip() if isinstance(w,QLineEdit) else w.currentData()) for k,w in self.fields.items()}
        return {k:v for k,v in values.items() if v or k not in PROFILE_OPTIONAL}

    def step(self,index):
        self.pages.setCurrentIndex(index);self.progress.setText(['01 / 02   资金安排','02 / 02   风险偏好'][index])
        self.back.setVisible(index==1);self.next.setVisible(index==0);self.save.setVisible(index==1);self.error.clear()

    def validate(self,keys):
        import re
        values=self.values()
        from bankagent.banking.wealth import PROFILE_OPTIONAL
        for k in keys:
            if k in PROFILE_OPTIONAL:continue
            if not values.get(k):
                self.error.setText('请填写：'+self.fields[k].accessibleName());self.fields[k].setFocus();return False
        if 'budget' in keys:
            from decimal import Decimal,InvalidOperation
            try:
                amounts=[Decimal(values[k]) for k in ('budget','free_cash')]
                valid=all(re.fullmatch(r'[0-9]+(?:\.[0-9]{1,2})?',values[k]) for k in ('budget','free_cash'))
                valid=valid and all(v.is_finite() and 0<=v<=10**8 and v==v.quantize(Decimal('.01')) for v in amounts)
                valid=valid and amounts[0]>0 and values['horizon_days'].isascii() and values['horizon_days'].isdigit() and 1<=int(values['horizon_days'])<=3650
            except (InvalidOperation,ValueError):valid=False
            if not valid:self.error.setText('金额最多两位小数，预算需大于0；天数请填1至3650的整数。');return False
            if values.get('need_on'):
                from datetime import date
                try:valid=date.fromisoformat(values['need_on']).isoformat()==values['need_on']
                except ValueError:valid=False
                if not valid:self.error.setText('日期请填写为YYYY-MM-DD。');return False
        return True

    def advance(self):
        if self.validate(self.groups[0]):self.step(1)

    def submit(self):
        if not self.validate(self.groups[0]):self.step(0);self.validate(self.groups[0]);return
        if self.validate(self.groups[1]):
            values=self.values();self.accept();self.submitted.emit(values)

    def open(self):
        self.step(0)
        available=self.screen().availableGeometry();self.resize(min(620,available.width()-40),min(700,available.height()-60))
        super().open()
