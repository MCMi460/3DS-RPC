# Created by Deltaion Lee (MCMi460) on Github

import os, sys
import sqlite3

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

class ProgressBar(): # Written with help from https://stackoverflow.com/a/3160819/11042767
    def __init__(self, width:int = terminalSize):
        self.width = width
        sys.stdout.write('[%s]' % (' ' * self.width))
        sys.stdout.flush()
        sys.stdout.write('\r[')

        self.progress = 0

    def update(self, fraction:float):
        fraction = int(fraction * self.width)
        self.progress += fraction
        for n in range(fraction):
            sys.stdout.write('-')
            sys.stdout.flush()

    def end(self):
        for n in range(self.width - self.progress):
            sys.stdout.write('-')
            sys.stdout.flush()
        sys.stdout.write(']\n')
