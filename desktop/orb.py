"""Accessible in-window assistant entry, painted with real alpha transparency."""
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QPen, QPainterPath
from PySide6.QtWidgets import QPushButton

class AssistantOrb(QPushButton):
    def __init__(self,parent):
        super().__init__(parent)
        self.setFixedSize(64,64)
        self.setAccessibleName('打开或收起 AI 助手')
        self.setToolTip('AI 助手 · 点击展开')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setStyleSheet('background: transparent; border: none;')

    def paintEvent(self,event):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(24,91,79,25)); painter.drawEllipse(3,5,58,58)
        glass=QRadialGradient(QPointF(23,18),43)
        glass.setColorAt(0,QColor('#cfe7cb' if self.underMouse() else '#e3efe0'))
        glass.setColorAt(.5,QColor('#89b79a'))
        glass.setColorAt(1,QColor('#2d6850' if self.isDown() else '#50866c'))
        painter.setBrush(glass); painter.setPen(QPen(QColor(255,255,255,210),1.5)); painter.drawEllipse(4,3,56,56)
        sparkle=QPainterPath(); sparkle.moveTo(32,17)
        for x,y in [(36,28),(47,32),(36,36),(32,47),(28,36),(17,32),(28,28)]:sparkle.lineTo(x,y)
        sparkle.closeSubpath(); painter.fillPath(sparkle,QColor(255,255,255,235))
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(QColor('#16725b'),2)); painter.drawEllipse(1,1,62,62)
