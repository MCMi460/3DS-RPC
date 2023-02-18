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
  background: qlineargradient(spread:repeat, y1:0.0, y2:0.02, y3:0.04, y4:0.06, y5:0.08, y6:0.1, y7:0.12, y8:0.14, y9:0.16, y10:0.18, y11:0.2, y12:0.22, y13:0.24, y14:0.26, y15:0.28, y16:0.3, y17:0.32, y18:0.34, y19:0.36, y20:0.38, y21:0.4, y22:0.42, y23:0.44, y24:0.46, y25:0.48, y26:0.5, y27:0.52, y28:0.54, y29:0.56, y30:0.58, y31:0.6, y32:0.62, y33:0.64, y34:0.66, y35:0.68, y36:0.7, y37:0.72, y38:0.74, y39:0.76, y40:0.78, y41:0.8, y42:0.82, y43:0.84, y44:0.86, y45:0.88, y46:0.9, y47:0.92, y48:0.94, y49:0.96, y50:0.98, y51:1 stop:0 rgba(218, 218, 215, 255), stop:0.0932642 rgba(218, 218, 215, 255), stop:0.108808 rgba(226, 226, 231, 255), stop:0.259067 rgba(226, 226, 231, 255), stop:0.274611 rgba(218, 218, 215, 255), stop:0.450777 rgba(218, 218, 215, 255), stop:0.46114 rgba(226, 226, 231, 255), stop:0.601036 rgba(226, 226, 231, 255), stop:0.61658 rgba(218, 218, 215, 255), stop:0.777202 rgba(218, 218, 215, 255), stop:0.782383 rgba(226, 226, 231, 255), stop:0.896373 rgba(226, 226, 231, 255), stop:0.901554 rgba(218, 218, 215, 255));
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
  background: transparent;
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
def loadPix(url):
    _pixmap = QPixmap()
    _pixmap.loadFromData(requests.get(url).content)
    return _pixmap
def up(_label,image):
    _label.clear()
    if isinstance(image,str):
        image = loadPix(image)
    _label.setPixmap(image)

class GUI(Ui_MainWindow):
    def __init__(self, MainWindow):
        self.MainWindow = MainWindow
        self.MainWindow.setFixedSize(600,600)

    def selfService(self, app):
        self.app = app
        self.MainWindow.setStyleSheet(style)
        self.assignVariables()
        self.page = 0
        self.updatePage()

        self.MainWindow.closeEvent = self.closeEvent

        if self.state and client.userData['User']['username']:
            self.stylize()
        self.pushButton_4.clicked.connect(sys.exit)
        self.pushButton_3.clicked.connect(lambda a : self.updatePage(3))
        self.pushButton_5.clicked.connect(lambda a : self.updatePage(2))

        self.state = False
        threading.Thread(target = self.grabCode, daemon = True).start()

    def assignVariables(self):
        self.button2 = self.groupBox_2.findChild(QPushButton, 'pushButton_2')
        self.button2.clicked.connect(lambda a : self.updatePage(1))

        self.button = self.groupBox.findChild(QPushButton, 'pushButton')
        self.button.clicked.connect(self.changeState)

        self.lineEdit = self.groupBox.findChild(QLineEdit, 'lineEdit')

        self.label5 = self.groupBox_2.findChild(QLabel, 'label_5')
        self.label5.setText('-'.join(botFC[i:i+4] for i in range(0, len(botFC), 4)))

    def stylize(self):
        global client
        # Push button
        closeButton = """
        QPushButton {
          background: qlineargradient(spread:pad, x1:0, y1:1, x2:0, y2:0, stop:0 #414247, stop:1 #717274);
          border-radius: 0px;
          border-top-left-radius: 41px;
          border-top-right-radius: 41px;
          padding-bottom: 25px;
        }
        QPushButton:hover {
          background: qlineargradient(spread:pad, x1:0, y1:1, x2:0, y2:0, stop:0 #9093a1, stop:1 #717274);
        }
        """
        self.pushButton_4.setStyleSheet(closeButton)
        classicButton = """
        QPushButton {
          color: #000;
          background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:2, stop:0 #fff, stop:1 #b0b0b8);
          border: 1px solid #b0b0b8;
        }
        QPushButton:hover {
          background: qlineargradient(spread:pad, x1:0, y1:1, x2:0, y2:0, stop:0 #9093a1, stop:1 #717274);
        }
        """
        self.pushButton_3.setStyleSheet(classicButton.replace('QPushButton {','QPushButton {padding-top: 25px;'))
        self.pushButton_5.setStyleSheet(classicButton)
        friendCard = """
        QGroupBox {
          background: #fff;
          background: qlineargradient(spread:pad, x1:0, y1:1, x2:0, y2:0, stop:0 rgb(255, 198, 147), stop:1 rgb(254, 245, 239));
          border: 2px solid #fff;
          border-radius: 0px;
        }
        QLabel {
          color: #E39240;
          font-weight: bold;
        }
        """
        if not client.userData['User']['online']:
            friendCard = friendCard.replace('rgb(255, 198, 147)','#B7B7B7').replace('#E39240', '#AAA6A3')
        self.friendCard.setStyleSheet(friendCard)
        self.namePlate.setStyleSheet("""
        QGroupBox {
          background-color: #fff;
          border-radius: 0px;
          border-top-left-radius: 15px;
          border-top-right-radius: 15px;
        }
        QLabel {
          font-size: 30px;
          color: #882D12;
          font-weight: normal;
        }
        """)

        # Update dynamic elements
        self.username.setText(client.userData['User']['username'])
        self.status.setText('Online' if client.userData['User']['online'] else 'Offline')
        self.miiLabel.setScaledContents(True)
        up(self.miiLabel,client.userData['User']['mii']['face'])

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

    def updatePage(self, page = None):
        self.page = page if page != None else self.page
        self.stackedWidget.setCurrentIndex(page if page != None else self.page)

class SystemTrayApp(QSystemTrayIcon):
    def __init__(self, icon, parent):
        QSystemTrayIcon.__init__(self, icon, parent)
        menu = QMenu(parent)
        self.parent = parent

        reopen = menu.addAction('Show')
        reopen.triggered.connect(self.reopen)

        quit = menu.addAction('Quit')
        quit.triggered.connect(sys.exit)

        self.setContextMenu(menu)

    def reopen(self):
        self.parent.show()
        self.hide()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    MainWindow = QMainWindow()
    window = GUI(MainWindow)

    tray = SystemTrayApp(QIcon('icon.png'), MainWindow)
    window.state = False
    window.setupUi(MainWindow)
    window.selfService(app)

    if not friendCode:
        MainWindow.show()
        app.exec_()

    client = Client(friendCode, config)
    client.connect()
    threading.Thread(target = client.background, daemon = True).start()
    while not client.userData:
        pass
    window.state = True
    window.setupUi(MainWindow)
    window.selfService(app)
    window.updatePage(2)
    MainWindow.show()

    sys.exit(app.exec_())
