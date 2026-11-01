"""Lightweight native decoration; no remote assets or business state."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QPainterPath
from PySide6.QtWidgets import QWidget


class ForestRail(QWidget):
    def paintEvent(self, event):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient=QLinearGradient(0,0,self.width(),self.height())
        gradient.setColorAt(0,QColor('#002d24')); gradient.setColorAt(1,QColor('#073e30'))
        painter.fillRect(self.rect(),gradient); painter.setPen(Qt.PenStyle.NoPen)
        for offset,alpha in ((0,24),(24,17),(50,12)):
            path=QPainterPath(); y=self.height()-190+offset
            path.moveTo(0,y); path.cubicTo(self.width()*.7,y-70,self.width()*.3,y+150,self.width(),y+70)
            path.lineTo(self.width(),self.height()); path.lineTo(0,self.height()); path.closeSubpath()
            painter.fillPath(path,QColor(90,170,125,alpha))
