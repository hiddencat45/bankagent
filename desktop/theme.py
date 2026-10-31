"""Shared native desktop styles."""
STYLE = '''
QWidget {font-family:"Microsoft YaHei";font-size:14px;color:#233631;background:#f4f6f5;}
QWidget#rail {background:#e7eeeb;} QWidget#rail QLabel {background:transparent;} QLabel#brand {font-size:23px;font-weight:700;}
QLabel#title {font-size:24px;font-weight:600;} QLabel#balance {font-size:36px;font-weight:600;color:#164f42;}
QLabel#muted {color:#63766e;font-size:12px;} QLabel#error {color:#a33829;}
QLabel#status {padding:10px;background:#e7eeeb;border-radius:4px;}
QLabel#status[state="error"] {background:#fbece8;color:#9a3024;}
QLabel#status[state="pending"] {background:#fff1d5;color:#79520f;}
QGroupBox {background:white;border:1px solid #dbe3de;border-radius:6px;margin-top:12px;padding:16px;}
QGroupBox::title {subcontrol-origin:margin;left:16px;padding:0 6px;color:#476158;}
QGroupBox QLabel,QGroupBox QWidget {background:white;}
QLineEdit,QComboBox {background:white;border:1px solid #bacac2;border-radius:4px;padding:10px;min-height:20px;}
QLineEdit:focus,QComboBox:focus {border:2px solid #27735e;}
QPushButton {background:white;border:1px solid #bacac2;border-radius:4px;padding:9px 12px;}
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
'''
