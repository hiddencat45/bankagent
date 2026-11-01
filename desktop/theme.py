"""Shared native desktop styles."""
STYLE = '''
QWidget {font-family:"Microsoft YaHei UI","Microsoft YaHei","Noto Sans CJK SC";font-size:14px;color:#263d34;background:#f6f8f6;}
QWidget#rail {background:#e7eeeb;} QWidget#rail QLabel {background:transparent;} QLabel#brand {font-size:23px;font-weight:700;}
QLabel#title {font-size:24px;font-weight:600;} QLabel#balance {font-size:36px;font-weight:600;color:#164f42;}
QLabel#muted {color:#63766e;font-size:12px;} QLabel#error {color:#a33829;}
QLabel#status {padding:10px;background:#e7eeeb;border-radius:4px;}
QLabel#status[state="error"] {background:#fbece8;color:#9a3024;}
QLabel#status[state="pending"] {background:#fff1d5;color:#79520f;}
QGroupBox {background:white;border:1px solid #e6ece7;border-radius:12px;margin-top:16px;padding:18px;}
QGroupBox::title {subcontrol-origin:margin;left:16px;padding:0 6px;color:#476158;}
QGroupBox QLabel,QGroupBox QWidget {background:white;}
QLineEdit,QComboBox {background:white;border:1px solid #bacac2;border-radius:4px;padding:10px;min-height:20px;}
QLineEdit:focus,QComboBox:focus {border:2px solid #27735e;}
QPushButton {background:#eef3ef;border:0;border-radius:8px;padding:10px 16px;}
QPushButton:hover {background:#e8f2ed;} QPushButton:checked {background:#d5e7dd;border-color:#44816a;}
QPushButton#primary {background:#1d6551;color:white;border-color:#1d6551;}
QPushButton:disabled {background:#edf0ee;color:#89968f;border-color:#dbe2dd;}
QPushButton#primary:disabled {background:#edf0ee;color:#89968f;border-color:#dbe2dd;}
QLineEdit:disabled,QComboBox:disabled {color:#718078;background:#edf0ee;}
QPlainTextEdit,QListWidget,QTableWidget {background:white;border:1px solid #dbe3de;border-radius:4px;padding:6px;}
QListWidget::item {padding:12px;border-bottom:1px solid #edf0ee;}
QListWidget::item:selected {background:#dbece3;color:#204b3c;}
QHeaderView::section {background:#f4f7f5;color:#61756b;border:0;padding:8px;}
QScrollArea {border:0;} QStatusBar {color:#63766e;}
QWidget#accountCard {background:#194f42;border-radius:10px;}
QWidget#accountCard QLabel {background:transparent;color:#ffffff;}
QWidget#accountCard QLabel#accountCaption {color:#bdd8cd;font-size:12px;}
QWidget#accountCard QLabel#accountName {font-size:16px;font-weight:600;}
QPushButton#accountPicker {background:transparent;color:white;border:0;border-top:1px solid #467568;border-radius:0;text-align:left;padding:12px 0 0 0;}
QPushButton#accountPicker:hover {color:#bcebd7;}
QPushButton#accountPicker:disabled {color:#93afa4;}
QPushButton#customerPicker {text-align:left;border:0;border-radius:8px;padding:14px 10px;background:#f7faf8;}
QPushButton#quietAction {background:transparent;border:0;padding:8px;}
QPushButton#quietAction:hover {background:#e0eae4;}
QMenu {background:white;border:1px solid #cbd9d1;padding:6px;}
QMenu::item {padding:10px 18px;} QMenu::item:selected {background:#dbece3;}
QMenu::item:disabled {color:#89968f;}
QPushButton#navigation {text-align:left;background:transparent;padding:14px 12px;color:#50675c;}
QPushButton#navigation:checked {background:#d9e8de;color:#174c38;font-weight:600;}
QPushButton#navigation:hover {background:#e0ebe3;}
QFrame#assistantSpace {border:1px solid #d7e5d9;border-radius:18px;
 background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(238,245,233,235),stop:0.55 rgba(247,250,247,225),stop:1 rgba(230,241,236,240));}
QFrame#assistantSpace QWidget {background:transparent;}
QFrame#assistantSpace QLabel#welcomeTitle {font-size:32px;font-weight:600;color:#214f3b;padding:12px;}
QFrame#composer {background:#ffffff;border:1px solid #dce7de;border-radius:16px;}
QFrame#composer QPlainTextEdit {border:0;padding:10px;font-size:16px;background:transparent;}
QFrame#assistantSpace QPushButton#suggestion {background:#e3eee4;border:0;border-radius:16px;padding:10px 20px;}
QFrame#assistantSpace QPushButton#primary {background:#24674e;color:white;padding:10px 28px;}
QFrame#assistantSpace QGroupBox {background:#ffffff;border:1px solid #d3e2d6;}
QLabel#confirmationSummary {font-size:18px;font-weight:600;padding:6px;}
QFrame#assistantSpace QPlainTextEdit {background:white;}
QProgressBar {background:#e3ece5;border:0;border-radius:2px;}
QProgressBar::chunk {background:#6b9d7d;border-radius:2px;}
QScrollBar:vertical {background:transparent;width:8px;}
QScrollBar::handle:vertical {background:#c4d3c9;min-height:24px;border-radius:4px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
'''


def load_chinese_font():
    """Register the bundled Windows font when Qt's fallback misses the system family."""
    import os
    from pathlib import Path
    from PySide6.QtGui import QFontDatabase
    if getattr(load_chinese_font, 'loaded', False):
        return
    path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/msyh.ttc'
    if path.exists():
        QFontDatabase.addApplicationFont(str(path))
    load_chinese_font.loaded = True
