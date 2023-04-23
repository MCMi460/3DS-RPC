# Created by Deltaion Lee (MCMi460) on Github

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from layout import Ui_MainWindow
from client import *
from client import _REGION

import webbrowser

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
with open('./layout/style.qss', 'r') as file:
    style = file.read()
offlineStyle = style.replace('#FFC693', '#B7B7B7').replace('#E39240', '#AAA6A3')

def loadPix(url):
    _pixmap = QPixmap()
    _pixmap.loadFromData(requests.get(url, verify = False).content)
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
        self.closeButton.clicked.connect(sys.exit)
        self.settingsButton.clicked.connect(lambda a : self.updatePage(3))
        self.okButton.clicked.connect(lambda a : self.updatePage(2))

        self.state = False
        threading.Thread(target = self.grabCode, daemon = True).start()

    def assignVariables(self):
        self.continueButton.clicked.connect(lambda a : self.updatePage(1))

        self.loginButton.clicked.connect(self.changeState)

        self.botFCLabel.setText('-'.join(botFC[i:i+4] for i in range(0, len(botFC), 4)))

    def stylize(self):
        self.updateColor()

        # Update dynamic elements
        self.setFontText(self.username, client.userData['User']['username'])
        self.miiLabel.setScaledContents(True)
        self.gameIcon.setScaledContents(True)
        up(self.miiLabel, client.userData['User']['mii']['face'])

        # Update others
        self.friendCard.mouseReleaseEvent = lambda event : self.openLink(host + '/user/%s' % client.userData['User']['friendCode'])

    def updateColor(self):
        self.MainWindow.setStyleSheet('')
        if not client.userData['User']['online']:
            self.MainWindow.setStyleSheet(offlineStyle)
        else:
            self.MainWindow.setStyleSheet(style)
        self.MainWindow.update()

        self.status.setText('Online' if client.userData['User']['online'] else 'Offline')

    def setFontText(self, label, text):
        label.setText(text)
        i = 21
        width = 30000
        while label.width() < width:
            i -= 1
            font = QFont('Arial', i)
            label.setFont(font)
            metric = QFontMetricsF(label.font())
            width = metric.width(label.text())

    def openLink(self, url:str):
        webbrowser.open(url)

    def closeEvent(self, event):
        if friendCode and client:
            event.ignore()
            self.MainWindow.hide()
            tray.show()
        elif friendCode:
            event.accept()
            self.app.quit()
        else:
            sys.exit()

    def grabCode(self):
        global friendCode, client, config
        if friendCode:
            return
        friendCode = str(convertPrincipalIdtoFriendCode(convertFriendCodeToPrincipalId(self.waitUntil()))).zfill(12)

    def waitUntil(self):
        while not self.state:
            pass
        return self.fcInput.text().strip()

    def changeState(self):
        self.state = True
        while not friendCode:
            pass
        self.MainWindow.close()

    def updatePage(self, page = None):
        self.page = page if page != None else self.page
        self.stackedWidget.setCurrentIndex(page if page != None else self.page)

    def update(self, data):
        if data:
            self.gamePlate.show()
            game = client.userData['User']['Presence']['game']
            self.gamePlate.mouseReleaseEvent = lambda a : self.openLink('https://www.google.com/search?q=%s' % '+'.join((game['name'] + ' ' + game['publisher']['name']).split(' ')))
            if data['large_image'] and not local:
                up(self.gameIcon, data['large_image'])
            self.setFontText(self.gameName, data['details'])
        else:
            self.gamePlate.hide()
        self.updateColor()

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

    client = Client(friendCode, config, GUI = window.update)
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
