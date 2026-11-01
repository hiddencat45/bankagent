"""Lightweight native decoration; no remote assets or business state."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class ForestRail(QWidget):
    def paintEvent(self, event):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient=QLinearGradient(0,0,self.width(),self.height())
        gradient.setColorAt(0,QColor('#002d24')); gradient.setColorAt(1,QColor('#073e30'))
        painter.fillRect(self.rect(),gradient); painter.setPen(Qt.PenStyle.NoPen)
        for offset in range(0,100,4):
            path=QPainterPath(); y=self.height()-260+offset
            path.moveTo(-30,y); path.cubicTo(self.width()*.65,y-95,self.width()*.25,y+130,self.width()+30,y+55)
            painter.setPen(QPen(QColor(111,198,148,12),1)); painter.drawPath(path)
            path.lineTo(self.width(),self.height()); path.lineTo(0,self.height()); path.closeSubpath()
            painter.fillPath(path,QColor(90,170,125,2))
