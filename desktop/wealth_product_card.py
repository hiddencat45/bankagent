"""Shared product presentation for catalog and trusted recommendation receipts."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy
from desktop.client import money
from desktop.wealth_disclosures import disclosure


STYLE = '''
QWidget#productSummary {background:transparent;}
QWidget#productSummary QLabel {background:transparent;border:0;}
QLabel#productTitle {font-size:19px;font-weight:600;color:#203e32;}
QWidget#productSummary QLabel#productBadge {color:#52735f;border:1px solid #c7d9cd;
 border-radius:5px;padding:3px 7px;font-size:12px;}
QLabel#productYield {color:#ad5835;font-size:34px;font-weight:600;}
QLabel#productMetric {color:#667b70;font-size:13px;}
QLabel#productDate {color:#7a8980;font-size:11px;}
QLabel#productTerm {color:#284c3b;font-size:16px;font-weight:600;}
QLabel#productCondition {color:#6b7d72;font-size:12px;}
QPushButton#productRiskToggle {background:#f1f5f2;color:#697c70;border:0;
 border-radius:7px;padding:9px 10px;text-align:left;font-size:12px;}
QPushButton#productRiskToggle:hover {background:#e8f0eb;}
QLabel#productRiskDetail {background:transparent;color:#6b7d72;font-size:12px;}
'''


def label(value, name):
    widget = QLabel(value)
    widget.setObjectName(name)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    return widget


class ProductSummary(QWidget):
    def __init__(self, product):
        super().__init__()
        self.setObjectName('productSummary')
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(STYLE)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(10)
        box.addWidget(label(product['short_name'], 'productTitle'))
        tags = QHBoxLayout()
        for value in (f"管理人 R{product['issuer_risk']}", product['issuer']):
            tags.addWidget(label(value, 'productBadge'), 0, Qt.AlignmentFlag.AlignLeft)
        tags.addStretch()
        box.addLayout(tags)
        box.addSpacing(5)
        metrics = QHBoxLayout()
        metrics.setSpacing(20)
        performance = QVBoxLayout()
        performance.setSpacing(4)
        data = disclosure(product['code'])
        performance.addWidget(label(data['value'] + '%' if data.get('value') else '—', 'productYield'))
        performance.addWidget(label(data['metric'], 'productMetric'))
        period = f"{data['start']} 至 {data['end']}" if data.get('value') else '尚无已核验的收益披露'
        performance.addWidget(label(period, 'productDate'))
        performance.addWidget(label('官方披露快照 · 非实时' if data.get('value') else '不以净值或基准替代收益率', 'productDate'))
        performance.addStretch()
        terms = QVBoxLayout()
        terms.setSpacing(6)
        terms.addSpacing(8)
        hold = f"最低持有 {product['hold_days']} 天" if product['hold_days'] else '不设封闭期'
        terms.addWidget(label(hold, 'productTerm'))
        terms.addWidget(label(money(product['minimum_minor']) + ' 元起购', 'productCondition'))
        terms.addWidget(label('赎回及到账安排\n以渠道确认为准', 'productCondition'))
        terms.addStretch()
        metrics.addLayout(performance, 3)
        metrics.addLayout(terms, 2)
        box.addLayout(metrics)


class ProductRiskNote(QWidget):
    geometryChanged = Signal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet(STYLE)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(7)
        self.toggle = QPushButton('非保本 · 过往业绩不代表未来表现  ⌄')
        self.toggle.setObjectName('productRiskToggle')
        self.toggle.setCheckable(True)
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle.setAccessibleName('展开产品风险提示')
        box.addWidget(self.toggle)
        self.detail = label('过往业绩不是收益承诺，不等于实际收益。不同指标和统计区间不能直接比较。'
                            '管理人评级不代替渠道最终评级，真实在售、费率及到账规则仍须核实。', 'productRiskDetail')
        self.detail.hide()
        box.addWidget(self.detail)
        self.toggle.toggled.connect(self.expand)

    def expand(self, checked):
        self.detail.setVisible(checked)
        self.toggle.setText('非保本 · 过往业绩不代表未来表现  ' + ('⌃' if checked else '⌄'))
        self.toggle.setAccessibleName('收起产品风险提示' if checked else '展开产品风险提示')
        self.geometryChanged.emit()
