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
 background:#f3f7f3;}
QFrame#assistantSpace QWidget {background:transparent;}
QFrame#assistantSpace QLabel#welcomeTitle {font-size:32px;font-weight:600;color:#214f3b;padding:12px;}
QFrame#composer {background:#ffffff;border:1px solid #dce7de;border-radius:16px;}
QFrame#composer QPlainTextEdit {border:0;padding:10px;font-size:16px;background:transparent;}
QFrame#assistantSpace QPushButton#suggestion {background:#e3eee4;border:0;border-radius:16px;padding:10px 20px;}
QFrame#assistantSpace QPushButton#primary {background:#24674e;color:white;padding:10px 28px;}
QFrame#assistantSpace QGroupBox {background:#ffffff;border:1px solid #d3e2d6;}
QLabel#confirmationSummary {font-size:15px;font-weight:400;padding:8px 2px;}
QGroupBox#operationConfirmation {background:white;border:1px solid #d2e3d8;border-radius:12px;padding:0;margin-top:0;}
QLabel#confirmationHeading {font-size:14px;font-weight:600;color:#195440;}
QGroupBox#operationConfirmation::title {color:#195440;font-size:13px;font-weight:600;}
QGroupBox#operationConfirmation QPushButton {padding:10px 14px;}
QFrame#assistantSpace QPlainTextEdit {background:white;}
QProgressBar {background:#e3ece5;border:0;border-radius:2px;}
QProgressBar::chunk {background:#6b9d7d;border-radius:2px;}
QScrollBar:vertical {background:transparent;width:8px;}
QScrollBar::handle:vertical {background:#c4d3c9;min-height:24px;border-radius:4px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
/* Forest workspace: one palette shared by business views and native dialogs. */
QWidget {font-family:"Microsoft YaHei";color:#213d35;background:#f5f7f5;}
QWidget#rail {background:#103e33;}
QWidget#rail QLabel {color:#eaf4ee;}
QWidget#rail QLabel#muted {color:#adcbc0;}
QWidget#rail QPushButton#navigation {color:#c5dbd1;padding:16px 12px;}
QWidget#rail QPushButton#navigation:checked {background:#2a604e;color:white;}
QWidget#rail QPushButton#navigation:hover {background:#235442;}
QWidget#accountCard {background:#1b4c3f;border:1px solid #386554;border-radius:12px;}
QPushButton#customerPicker {background:#1b4c3f;color:#eff7f2;}
QLabel#title {font-size:26px;font-weight:700;color:#163d31;}
QLabel#sectionTitle {font-size:18px;font-weight:600;color:#163d31;}
QLineEdit,QComboBox,QDateEdit {background:white;border:1px solid #d5e0d9;border-radius:8px;padding:9px;min-height:22px;selection-background-color:#28624e;}
QLineEdit:focus,QComboBox:focus,QDateEdit:focus {border:1px solid #28765b;}
QPushButton {padding:11px 16px;}
QPushButton#primary {background:#195440;color:white;}
QPushButton#primary:hover {background:#246c53;}
QTableWidget {border:1px solid #e0e8e2;border-radius:10px;padding:8px;selection-background-color:#e4f0e9;selection-color:#173e30;}
QTableWidget::item {border-bottom:1px solid #edf1ee;padding:8px;}
QTableWidget QWidget,QFrame#transactionInspector QScrollArea,QFrame#transactionInspector QScrollArea QWidget {background:white;}
QTableWidget::item:selected {background:#e3efe7;color:#164f3c;}
QHeaderView::section {background:#f5f8f5;padding:12px 8px;color:#718379;font-size:12px;}
QFrame#ledgerSummary {background:#174f3d;border-radius:12px;}
QLabel#ledgerTotal {background:transparent;color:#ffffff;padding:4px 12px;font-size:20px;}
QLabel#status[state="normal"] {background:transparent;color:#718379;padding:0;font-size:12px;}
QComboBox::drop-down,QDateEdit::drop-down {border:0;width:22px;}
QFrame#transactionInspector {background:white;border:1px solid #e0e8e2;border-radius:12px;}
QFrame#transactionInspector QLabel {background:transparent;}
QDialog,QMessageBox,QInputDialog {background:#f5f8f5;}
QDialog QLabel {background:transparent;}
QDialog QLineEdit {background:white;padding:12px;}
QDialog QPushButton:default {background:#195440;color:white;}
QDialog QDialogButtonBox {background:transparent;}
QLabel#dialogHeading {font-size:22px;font-weight:600;color:#174f3d;padding-bottom:12px;}
QLabel#dialogSummary {background:white;border:1px solid #dce6df;border-radius:10px;padding:18px;}
/* Submission ledger: hierarchy, aligned data, and a persistent details panel. */
QWidget {font-family:"Microsoft YaHei";font-size:14px;color:#172b24;}
QLabel#title {font-size:28px;font-weight:700;color:#101e19;}
QWidget#rail QLabel#brand {font-size:28px;font-weight:700;padding:0;}
QLabel#identityName {font-size:14px;font-weight:600;padding:8px 12px;}
QWidget#rail QPushButton#navigation:checked {background:#1d5843;border-left:3px solid #43c78a;border-radius:7px;}
QWidget#rail QPushButton#navigation {font-size:16px;}
QFrame#ledgerList {background:white;border:1px solid #e3e8e4;border-radius:12px;}
QFrame#ledgerList QLabel {background:transparent;}
QFrame#ledgerSummary {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #064b38,stop:1 #003328);border-radius:12px;}
QLabel#ledgerTotal {font-size:23px;font-weight:600;color:white;background:transparent;padding:0 12px;}
QLabel#summaryIcon {background:#286653;color:white;font-size:29px;border-radius:24px;}
QFrame#summaryDivider {background:#527a68;margin:10px 14px;}
QPushButton#ledgerAccount {background:white;border:1px solid #dce3de;padding:12px 16px;color:#17392b;}
QTableWidget#ledgerTable {background:white;border:0;border-radius:0;padding:0;gridline-color:transparent;}
QPushButton#ledgerTab {background:#f3f5f3;color:#233e30;padding:10px 24px;}
QPushButton#ledgerTab:checked {background:#064b38;color:white;}
QTableWidget#ledgerTable::item {padding:8px 5px;border-bottom:1px solid #edf0ed;}
QTableWidget#ledgerTable QHeaderView::section {font-size:12px;background:#f5f7f5;color:#667069;padding:12px 5px;}
QLabel#detailMark {background:#def5e6;border-radius:27px;color:#128146;font-size:32px;font-weight:600;}
QFrame#transactionInspector QLabel#detailMark {background:#def5e6;}
QTableWidget QWidget#statusCell {background:transparent;}
QTableWidget QLabel#ledgerStatus {background:#e0f3e7;color:#177341;border-radius:6px;font-size:12px;}
QLabel#detailAmount {font-size:27px;font-weight:700;color:#101e19;padding:4px 0 18px 0;}
QFrame#transactionInspector QLabel#muted {font-size:13px;color:#79817b;}
QFrame#transactionInspector QPlainTextEdit {font-size:12px;background:#f6f8f6;}
QWidget#rail QLabel#railFooter {color:#749e8c;font-size:12px;background:transparent;line-height:1.6;}
QPushButton#profileMenu {background:transparent;color:#152b22;padding:8px 12px;}
QPushButton#profileMenu:hover {background:#e5eee8;}
QFrame#detailDivider {background:#e8ede9;}
QFrame#ledgerSegments {background:#f3f5f3;border-radius:10px;}
QLabel#detailAmount {font-size:29px;font-weight:700;}
QTableWidget#ledgerTable:focus {border:1px solid #9ebead;}
QWidget {font-family:"Microsoft YaHei UI";}
'''


from pathlib import Path
STYLE += 'QComboBox::down-arrow,QDateEdit::down-arrow {width:16px;height:16px;image:url("' + (Path(__file__).resolve().parent / 'assets/chevron-down.svg').as_posix() + '");}'
STYLE += 'QFrame#ledgerSummary {border-image:url("' + (Path(__file__).resolve().parent / 'assets/summary-forest.svg').as_posix() + '") 0 0 0 0 stretch stretch;}'


def load_chinese_font():
    """Register the bundled Windows font when Qt's fallback misses the system family."""
    import os
    from pathlib import Path
    from PySide6.QtGui import QFontDatabase, QFont
    from PySide6.QtWidgets import QApplication
    if getattr(load_chinese_font, 'loaded', False):
        return
    path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/msyh.ttc'
    if path.exists():
        QFontDatabase.addApplicationFont(str(path))
    QApplication.setFont(QFont('Microsoft YaHei UI',10))
    load_chinese_font.loaded = True
