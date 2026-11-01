"""Present trusted receipts; actions navigate or request read-only screening."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from desktop.client import money
from bankagent.banking.wealth import OPERATIONS, STATES


STYLE = '''
QWidget#wealthChat {background:white;border:1px solid #dbe7df;border-radius:16px;}
QLabel#wealthChatTitle {font-size:20px;font-weight:600;color:#173f32;}
QLabel#wealthChatBody {font-size:14px;color:#425d50;}
QLabel#wealthChatCaption {font-size:12px;color:#728278;}
QLabel#wealthChatName {font-size:15px;font-weight:600;color:#244e3b;}
QLabel#wealthChatTag {font-size:12px;color:#476957;}
QFrame#wealthChatProduct {background:#f5f8f5;border:0;border-radius:10px;}
QPushButton#wealthChatPrimary {background:#205d46;color:white;border:0;border-radius:9px;padding:10px 18px;font-size:14px;}
QPushButton#wealthChatPrimary:hover {background:#2d7157;}
QPushButton#wealthChatLink {background:transparent;color:#476957;border:0;padding:8px 0;font-size:13px;text-align:left;}
'''


def render(chat, receipt):
    if receipt['operation'] not in OPERATIONS or receipt['status'] != 'COMPLETED':
        return None
    body = chat.bubble('assistant', 'wealthChat')
    body.setContentsMargins(20, 16, 20, 18)
    body.setSpacing(8)
    data, operation = receipt.get('data') or {}, receipt['operation']

    def text(value, style='wealthChatBody', target=body):
        target.addWidget(chat.label(value, style))

    def action(title, destination, payload=None, primary=False, target=body):
        button = QPushButton(title)
        button.setObjectName('wealthChatPrimary' if primary else 'wealthChatLink')
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda: chat.wealth_opened.emit(destination, payload or {}))
        target.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)

    if operation in {'QUERY_WEALTH', 'RECOMMEND_WEALTH'}:
        valid = data.get('profile_valid', False)
        if not valid:
            expired = bool(data.get('profile'))
            text('先更新一下你的理财需求' if expired else '先了解你的需求，再帮你挑选', 'wealthChatTitle')
            text('之前的问卷已过期。请确认资金安排和风险偏好是否有变化。' if expired else
                 '你准备拿出多少钱、多久不用，以及能否接受亏损？\n先完成一份简短问卷，再比较适合你需求的产品。')
            action('更新我的需求' if expired else '填写需求问卷', 'profile', primary=True)
            action('先浏览产品资料 →', 'products')
        elif operation == 'RECOMMEND_WEALTH':
            matches = {r['product_code']: r for r in data['recommendations']}
            count = sum(bool(r['eligible']) for r in matches.values())
            text(f'{count} 款产品符合当前模拟筛选条件' if count else '目前没有符合你需求的产品', 'wealthChatTitle')
            text(f"已核对 {len(data['products'])} 款产品 · {len(matches)-count} 款不匹配", 'wealthChatCaption')
            text('先比较风险和用钱时间，再决定是否继续。' if count else '可以查看排除理由，或更新实际需求；不必为了购买而改变答案。')
            excluded=QWidget();excluded_box=QVBoxLayout(excluded);excluded_box.setContentsMargins(0,0,0,0);excluded_box.setSpacing(8)
            for product in data['products']:
                result = matches.get(product['code'])
                if result is None:
                    continue
                card = QFrame(); card.setObjectName('wealthChatProduct')
                content = QVBoxLayout(card); content.setContentsMargins(14, 12, 14, 10); content.setSpacing(6)
                text(product['short_name'], 'wealthChatName', content)
                hold = f"最低持有 {product['hold_days']} 天" if product['hold_days'] else '不设封闭期'
                text(f"管理人 R{product['issuer_risk']}  ·  {money(product['minimum_minor'])} 元起  ·  {hold}", 'wealthChatCaption', content)
                text(('通过初筛 · ' if result['eligible'] else '暂不匹配 · ') + '；'.join(result['reasons']), target=content)
                action('查看产品详情 →', 'product', {'code': product['code']}, target=content)
                (body if result['eligible'] else excluded_box).addWidget(card)
            if excluded_box.count():
                toggle=QPushButton(f'查看 {excluded_box.count()} 款不匹配产品及原因')
                toggle.setObjectName('wealthChatLink');toggle.setCheckable(True);toggle.setChecked(not count)
                def expand(checked):
                    excluded.setVisible(checked)
                    toggle.setText('收起不匹配产品' if checked else f'查看 {excluded_box.count()} 款不匹配产品及原因')
                    QTimer.singleShot(0,chat.fit_bubbles)
                toggle.toggled.connect(expand);body.addWidget(toggle);body.addWidget(excluded);expand(not count)
            else:excluded.deleteLater()
            action('查看产品与匹配结果', 'products', primary=True)
        else:
            text('你的模拟理财账户', 'wealthChatTitle')
            metrics = QHBoxLayout(); metrics.setSpacing(24)
            for name, key in [('可用资金', 'available_minor'), ('模拟持仓', 'holdings_minor')]:
                column = QVBoxLayout(); column.setSpacing(4); text(name, 'wealthChatCaption', column)
                text('¥ ' + money(data[key]), 'wealthChatTitle', column); metrics.addLayout(column)
            body.addLayout(metrics)
            text(f"申购冻结 ¥ {money(data['frozen_minor'])}  ·  赎回待到账 ¥ {money(data['waiting_minor'])}", 'wealthChatCaption')
            text('演示日期 ' + data['day'], 'wealthChatCaption')
            action('查看持仓与订单 →', 'holdings', primary=True)
        text('仅模拟需求筛选 · 非保本 · 非银行正式风险测评', 'wealthChatCaption')
        if valid:
            text('真实渠道在售、最终评级、优惠费率及到账安排待核实。', 'wealthChatCaption')
    elif 'order' in data:
        order = data['order']; partial = 0 < order['filled_minor'] < order['requested_minor']
        text(STATES[order['state']] + (' · 部分成交' if partial else ''), 'wealthChatTitle')
        text(order['product_snapshot']['short_name'], 'wealthChatName')
        text(('申请申购 ¥ ' if order['side'] == 'BUY' else '申请赎回 ') + money(order['requested_minor']) + ('' if order['side'] == 'BUY' else ' 份'))
        text('已确认 ' + money(order['filled_minor']) + ' 份', 'wealthChatBody')
        text(order['events'][-1]['message'])
        text('模拟订单 · ' + order['order_id'], 'wealthChatCaption')
        action('查看订单进度 →', 'order', {'order_id': order['order_id']}, primary=True)
    elif operation == 'SAVE_WEALTH_PROFILE':
        text('你的理财需求已保存', 'wealthChatTitle')
        text('现在可以比较产品的匹配理由。保存问卷不会购买任何产品。')
        action('查看匹配产品 →', 'recommend', primary=True)
        text('仅模拟需求筛选，有效期至 ' + data['profile']['expires_on'], 'wealthChatCaption')
    else:
        text('演示日期已更新', 'wealthChatTitle')
        text(data['day'] + ' · 尚未自动提交或确认订单。')
        action('查看订单记录 →', 'orders')
    return body
