"""Small native line icons, independent of installed symbol fonts."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QPainterPath


def icon(kind, size=24, color='#42755b'):
    pixmap = QPixmap(size*2, size*2); pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size/12, size/12)
    painter.setPen(QPen(QColor(color), 1.5)); painter.setBrush(Qt.BrushStyle.NoBrush)
    if kind == 'avatar':
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor('#cee4da')); painter.drawEllipse(1,1,22,22)
        painter.setBrush(QColor('#0c4936')); painter.drawEllipse(8,4,8,8); painter.drawRoundedRect(5,13,14,9,5,5)
    elif kind == 'search':
        painter.drawEllipse(3,3,12,12); painter.drawLine(14,14,21,21)
    elif kind == 'filter':
        for y,left,right in ((5,3,21),(11,6,18),(17,10,14)):painter.drawLine(left,y,right,y)
    elif kind == 'calendar':
        painter.drawRoundedRect(3,5,18,16,2,2); painter.drawLine(3,10,21,10)
        painter.drawLine(8,2,8,7); painter.drawLine(16,2,16,7)
    elif kind == 'check':
        painter.drawLine(4,12,10,18); painter.drawLine(10,18,21,6)
    elif kind in {'incoming','outgoing'}:
        painter.drawLine(12,4,12,20)
        y=20 if kind=='incoming' else 4
        end=14 if kind=='incoming' else 10
        painter.drawLine(6,end,12,y); painter.drawLine(18,end,12,y)
    elif kind == 'card':
        painter.drawRoundedRect(3, 5, 18, 14, 3, 3); painter.drawLine(4, 10, 20, 10)
        painter.drawLine(7, 15, 11, 15)
    elif kind == 'overview':
        painter.drawRoundedRect(3, 3, 18, 18, 3, 3); painter.drawLine(3, 10, 21, 10)
        painter.drawLine(11, 10, 11, 21)
    elif kind == 'transfer':
        painter.drawLine(4, 8, 20, 8); painter.drawLine(16, 4, 20, 8); painter.drawLine(16, 12, 20, 8)
        painter.drawLine(20, 17, 4, 17); painter.drawLine(8, 13, 4, 17); painter.drawLine(8, 21, 4, 17)
    elif kind == 'ledger':
        for y in (5, 12, 19):
            painter.drawLine(8, y, 21, y); painter.drawEllipse(3, y-1, 2, 2)
    elif kind == 'refresh':
        painter.drawArc(4, 4, 16, 16, 30*16, 290*16); painter.drawLine(20, 3, 20, 9); painter.drawLine(20, 9, 14, 9)
    else:
        path = QPainterPath(); path.moveTo(12, 2)
        for x, y in ((15, 9), (22, 12), (15, 15), (12, 22), (9, 15), (2, 12), (9, 9)):
            path.lineTo(x, y)
        path.closeSubpath(); painter.fillPath(path, QColor('#42755b'))
    painter.end(); pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)
