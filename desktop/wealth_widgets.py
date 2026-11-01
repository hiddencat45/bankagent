"""Native wealth cards and a nonblocking, explicitly confirmed onboarding form."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget,QFrame,QLabel,QPushButton,QVBoxLayout,QHBoxLayout,
    QDialog,QLineEdit,QComboBox,QFormLayout,QStackedWidget,QScrollArea,QSizePolicy)
from desktop.client import money
from desktop.theme import STYLE

WEALTH_STYLE='''
QFrame#wealthPanel {background:white;border:1px solid #e0e8e2;border-radius:14px;}
QFrame#wealthPanel QLabel {background:transparent;}
QFrame#wealthHero {background:#184f40;border-radius:14px;}
QFrame#wealthHero QLabel {background:transparent;color:white;}
QLabel#wealthCaption {color:#718479;font-size:12px;}
QLabel#wealthNumber {font-size:26px;font-weight:600;}
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
    def __init__(self):
        super().__init__();self.row=-1;self.cards=[];self.select_buttons=[]
        self.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Fixed)
        self.box=QHBoxLayout(self);self.box.setContentsMargins(0,0,0,0);self.box.setSpacing(14)

    def rowCount(self):return len(self.cards)
    def currentRow(self):return self.row
    def setRowCount(self,count):
        assert count==0
        while self.box.count():
            w=self.box.takeAt(0).widget();w.hide();w.deleteLater()
        self.cards=[];self.select_buttons=[];self.row=-1

    def populate(self,products,recommendations):
        selected=max(0,self.row);self.setRowCount(0)
        for i,p in enumerate(products):
            card=QFrame();card.setObjectName('wealthProduct');box=QVBoxLayout(card)
            box.setContentsMargins(16,16,16,16);box.setSpacing(8)
            head=QHBoxLayout();head.addWidget(text(p['issuer'],'wealthCaption'));head.addStretch()
            head.addWidget(text(f"R{p['issuer_risk']}",'wealthTag'));box.addLayout(head)
            box.addWidget(text(p['short_name'],'wealthName'))
            box.addWidget(text('不保本 · 管理人评级','wealthCaption'))
            price=QHBoxLayout();price.addWidget(text(money(p['minimum_minor'])+' 元','wealthNumber'))
            price.addWidget(text('起投','wealthCaption'));price.addStretch();box.addLayout(price)
            box.addWidget(text(f"最低持有 {p['hold_days']} 天" if p['hold_days'] else '无封闭期'))
            r=recommendations.get(p['code'])
            status='待完善需求' if r is None else '符合模拟初筛' if r['eligible'] else '暂不匹配'
            box.addWidget(text(status,'wealthHint'))
            button=QPushButton('选择产品');button.setCheckable(True)
            button.clicked.connect(lambda checked=False,row=i:self.selectRow(row))
            button.setAccessibleName('选择'+p['short_name']);box.addWidget(button)
            self.cards.append(card);self.select_buttons.append(button);self.box.addWidget(card,1)
        self.selectRow(min(selected,len(self.cards)-1))

    def selectRow(self,row):
        if not 0<=row<len(self.cards):return
        self.row=row
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
        outer.addWidget(text('先了解你，再比较产品','title'))
        outer.addWidget(text('约 1 分钟 · 仅用于模拟需求筛选，不代替银行正式风险测评。','wealthHint'))
        self.progress=text('','wealthTag');outer.addWidget(self.progress)
        self.pages=QStackedWidget();self.fields={}
        definitions=[[
            ('budget','计划投入多少（元）',None),('free_cash','扣除必要支出和备用金后的闲钱（元）',None),
            ('horizon_days','最早多久后会用到这笔钱（天）',None),
            ('purpose','这笔钱的用途',['闲置资金','必要支出']),('liquidity','到账要求',['可等待','当天到账','固定日期'])],
            [('loss','能否承受本金亏损',['不能亏损','仅低风险','接受波动']),('income','收入状况',['稳定','不稳定']),
             ('debt','还款与资金来源',['无压力','有还款压力','借款理财']),('experience','非保本理财经验',['无经验','有经验']),
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
        outer.addWidget(self.pages,1);self.error=text('','error');outer.addWidget(self.error)
        row=QHBoxLayout();self.later=QPushButton('稍后填写');self.later.setObjectName('quietAction');self.later.clicked.connect(self.reject);row.addWidget(self.later);row.addStretch()
        self.back=QPushButton('上一步');self.back.setObjectName('quietAction');self.back.clicked.connect(lambda:self.step(0));row.addWidget(self.back)
        self.next=QPushButton('下一步');self.next.setObjectName('primary');self.next.clicked.connect(self.advance);row.addWidget(self.next)
        self.save=QPushButton('核对我的需求');self.save.setObjectName('primary');self.save.clicked.connect(self.submit);row.addWidget(self.save)
        outer.addLayout(row);self.step(0)

    def values(self):
        return {k:(w.text().strip() if isinstance(w,QLineEdit) else w.currentData()) for k,w in self.fields.items()}

    def step(self,index):
        self.pages.setCurrentIndex(index);self.progress.setText(['01 / 02   资金安排','02 / 02   风险偏好'][index])
        self.back.setVisible(index==1);self.next.setVisible(index==0);self.save.setVisible(index==1);self.error.clear()

    def validate(self,keys):
        import re
        values=self.values()
        for k in keys:
            if not values[k]:
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
