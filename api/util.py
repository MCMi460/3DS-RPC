# Created by Deltaion Lee (MCMi460) on Github

import os, sys
import sqlite3
import time
import threading

def getAppPath(): # Credit to @HotaruBlaze
    applicationPath = os.path.expanduser('~/Documents/3DS-RPC')
    # Windows allows you to move your UserProfile subfolders, Such as Documents, Videos, Music etc.
    # However os.path.expanduser does not actually check and assumes it's in the default location.
    # This tries to correctly resolve the Documents path and fallbacks to default if it fails.
    if os.name == 'nt':
        try:
            import ctypes.wintypes
            CSIDL_PERSONAL = 5 # My Documents
            SHGFP_TYPE_CURRENT = 0 # Get current, not default value
            buf=ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
            applicationPath = os.path.join(buf.value,'3DS-RPC')
        except:pass
    return applicationPath

def startDBTime(time):
    with sqlite3.connect('sqlite/fcLibrary.db') as con:
    	cursor = con.cursor()
    	cursor.execute('DELETE FROM config')
    	cursor.execute('INSERT INTO config (BACKEND_UPTIME) VALUES (%s)' % (time,))
    	con.commit()

try:
    terminalSize = os.get_terminal_size().columns - 2
except OSError:
    terminalSize = 40

class Color:
    DEFAULT = '\033[0m'
    RED = '\033[91m'
    PURPLE = '\033[0;35m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'

class ProgressBar(): # Written with help from https://stackoverflow.com/a/3160819/11042767
    def __init__(self, width:int = terminalSize):
        self.width = width
        sys.stdout.write('[%s]' % (' ' * self.width))
        sys.stdout.flush()
        sys.stdout.write('\r[')

        self.progress = 0
        self.close = True

    def update(self, fraction:float):
        fraction = int(fraction * self.width)
        self.progress += fraction
        def loop(self):
            for n in range(fraction):
                self.close = False
                sys.stdout.write('#')
                sys.stdout.flush()
                time.sleep(0.1)
                self.close = False
            self.close = True
        threading.Thread(target = loop, args = (self,)).start()

    def end(self): # Can take up time on main thread to finish
        for n in range(self.width - self.progress):
            sys.stdout.write('#')
            sys.stdout.flush()
        for i in range(10):
            while not self.close:
                time.sleep(0.2)
        sys.stdout.write(']\n')

# Get image url from title ID
def getTitle(titleID, titlesToUID, titleDatabase):
    _pass = None

    uid = None
    tid = hex(int(titleID))[2:].zfill(16).upper()
    _template = {
        'name': 'Unknown 3DS App',
        'icon_url': '',
        'banner_url': '',
        'publisher': {
            'name': 'Unknown',
        },
        'star_rating_info': {
            'score': '??',
        },
        'display_genre': '??',
        '@id': tid,
    }
    for game in titlesToUID:
        if game['TitleID'] == tid:
            uid = game['UID']
            break
    if not uid:
        if tid == ''.zfill(16):
            _pass = _template
            _pass['name'] = 'Home Screen'
        else:
            _pass = _template
        # raise TitleIDMatchError('unknown title id: %s' % tid)

    game = None
    for region in titleDatabase:
        for title in region['eshop']['contents']['content']:
            if title['title']['@id'] == uid:
                game = title['title']
                break
    if not game:
        _pass = _template
        # raise GameMatchError('unknown game: %s' % uid)
    if _pass:
        game = _pass

    # Support browsers' security stuff
    game['icon_url'] = game['icon_url'].replace('https://kanzashi-ctr.cdn.nintendo.net/i/', '/cdn/i/')
    game['banner_url'] = game['banner_url'].replace('https://kanzashi-ctr.cdn.nintendo.net/i/', '/cdn/i/')

    return game

class APIException(Exception):
    pass

class TitleIDMatchError(Exception):
    pass

class GameMatchError(Exception):
    pass
