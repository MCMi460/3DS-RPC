# Created by Deltaion Lee (MCMi460) on Github

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from layout import Ui_MainWindow
from client import *
from client import _REGION

# 3DS Variables
friendCode = None
config = {}
if not os.path.isdir(path):
    os.mkdir(path)
if os.path.isfile(privateFile):
    with open(privateFile, 'r') as file:
        js = json.loads(file.read())
        friendCode = js['friendCode']
        config = js
        del config['friendCode']
client = None
# PyQt5 Variables
style = """
QWidget {
  background-color: #F2F2F2;
}
QGroupBox {
  background-color: #fff;
  border: 1px solid #dfdfdf;
  border-radius: 8px;
}
QLineEdit {
  color: #888c94;
  background-color: #F2F2F2;
}
QLabel {
  background-color: #F2F2F2;
  color: #3c3c3c;
  text-align: center;
}
QComboBox {
  background-color: #F2F2F2;
  color: #3c3c3c;
  border: 1px solid #dfdfdf;
  text-align: center;
}
QPushButton {
  color: #ffffff;
  background-color: #ff8000;
  border-radius: 10px;
  text-align: center;
}
QPushButton:disabled {
  background-color: #706465;
}
QMenu::item {
  color: #393939;
}
QScrollBar:vertical {
    border: 0px;
    background-color: transparent;
}
QScrollBar::handle:vertical {
    background-color: #393939;
    border-radius: 4px;
}
QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
    background: none;
    border: none;
}
QScrollBar::add-line, QScrollBar::sub-line {
    background: none;
    border: none;
}
"""

class GUI(Ui_MainWindow):
    def __init__(self, MainWindow):
        self.MainWindow = MainWindow

    def selfService(self, app):
        self.app = app
        self.MainWindow.setStyleSheet(style)
        self.assignVariables()
        self.page = 0

        self.MainWindow.closeEvent = self.closeEvent

        self.state = False
        threading.Thread(target = self.grabCode, daemon = True).start()

    def assignVariables(self):
        self.button2 = self.groupBox_2.findChild(QPushButton, 'pushButton_2')
        self.button2.clicked.connect(self.continueButton)

        self.button = self.groupBox.findChild(QPushButton, 'pushButton')
        self.button.clicked.connect(self.changeState)

        self.lineEdit = self.groupBox.findChild(QLineEdit, 'lineEdit')

        self.label5 = self.groupBox_2.findChild(QLabel, 'label_5')
        self.label5.setText('-'.join(botFC[i:i+4] for i in range(0, len(botFC), 4)))

    def closeEvent(self, event):
        if client.connected:
            event.ignore()
            self.MainWindow.hide()
            tray.show()
        else:
            event.accept()
            self.app.quit()

    def grabCode(self):
        global friendCode, client, config
        if friendCode:
            return
        friendCode = self.waitUntil()
        try:
            try:
                client = Client(friendCode, config)
            except (AssertionError, FriendCodeValidityError) as e:
                if os.path.isfile(privateFile):
                    os.remove(privateFile)
                raise e
        except:
            print(traceback.format_exc())
            os._exit(1)
        friendCode = client.friendCode

    def waitUntil(self):
        while not self.state:
            pass
        return self.lineEdit.text().strip()

    def changeState(self):
        self.state = True
        while not client:
            pass
        self.MainWindow.close()

    def continueButton(self):
        self.page = 1
        self.updatePage()

    def updatePage(self, page = None):
        self.page = page if page != None else self.page
        self.stackedWidget.setCurrentIndex(page if page != None else self.page)

class SystemTrayApp(QSystemTrayIcon):
    def __init__(self, icon, parent):
        QSystemTrayIcon.__init__(self, icon, parent)
        menu = QMenu(parent)

        quit = menu.addAction('Quit')
        quit.triggered.connect(sys.exit)

        self.setContextMenu(menu)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    MainWindow = QMainWindow()
    window = GUI(MainWindow)

    tray = SystemTrayApp(QIcon('icon.png'), MainWindow)
    window.setupUi(MainWindow)
    window.selfService(app)

    if not friendCode:
        window.state = False
        MainWindow.show()
        app.exec_()

    client = Client(friendCode, config)
    client.connect()
    threading.Thread(target = client.background, daemon = True).start()
    while not client:
        pass
    window.state = True
    tray.show()

    sys.exit(app.exec_())
