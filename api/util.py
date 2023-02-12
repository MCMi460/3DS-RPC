# Created by Deltaion Lee (MCMi460) on Github

import os, sys
import sqlite3
import time
import threading
if os.name == 'nt':
    import pyreadline3
else:
    import readline
import typing

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
    terminalSize = os.get_terminal_size(0).columns - 2
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
        'price_on_retail': '$??.??',
        'release_date_on_eshop': '????-??-??',
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
        if game:
            break
    if not game:
        _pass = _template
        # raise GameMatchError('unknown game: %s' % uid)
    if _pass:
        game = _pass

    for key in _template.keys():
        if not key in game.keys():
            game[key] = _template[key]

    # Support browsers' security stuff
    game['icon_url'] = game['icon_url'].replace('https://kanzashi-ctr.cdn.nintendo.net/i/', '/cdn/i/')
    game['banner_url'] = game['banner_url'].replace('https://kanzashi-ctr.cdn.nintendo.net/i/', '/cdn/i/')

    return game

class Console():
    def __init__(self, client: object, *, prefix:str = '/'):
        self.prefix = prefix
        self.client = client
        self.commands = {}
        for func in dir(self):
            if callable(getattr(self, func)) and not func.startswith('_'):
                function = getattr(self, func)
                self.commands[func] = {
                    'function': function,
                    'docstring': str(function.__doc__).strip(),
                }

        self.tip = ('Type \'help\' to view the configuration menu', Color.YELLOW)

    def _main(self):
        self._log(*self.tip)
        while True:
            userInput = input(Color.DEFAULT + '> ' + Color.PURPLE).strip().lower()
            args = userInput.split(' ')

            try:
                self.commands[args[0]]['function'](*args[1:])
            except KeyError:
                self._missingCommand(userInput)

    def _log(self, text:str, color:str = Color.DEFAULT):
        text = color + str(text)
        print(text)
        return text

    def _missingCommand(self, command:str):
        return self._log('\'%s\' is not a real command!' % command, Color.RED), self._log(*self.tip)

    def exit(self):
        """
        Quits application
        """
        sys.exit(Color.RED + 'Exiting...')

    def help(self):
        """
        Shows a formatted list of all available commands
        """
        return self._log('\n'.join(( '%s: %s' % (key, self.commands[key]['docstring']) for key in self.commands.keys())), Color.YELLOW)

    def clear(self):
        """
        Clears the console
        """
        return print('\033[H\033[J', end = '')

    def status(self):
        """
        Shows your current status
        """
        text = [
            '%s: %s' % ('Exception', self.client.userData['Exception']),
            '%s: %s' % ('Friend Code', self.client.userData['User']['friendCode']),
            '%s: %s' % ('Online', self.client.userData['User']['online']),
            '%s: %s' % ('Message', self.client.userData['User']['message']),
        ]
        if self.client.userData['User']['username']:
            text.append('%s: %s' % ('Username', self.client.userData['User']['username']))
            text.append('%s: %s' % ('Mii', self.client.userData['User']['mii']['face']))
        if self.client.userData['User']['online']:
            text.append('%s: %s' % ('Game', self.client.userData['User']['Presence']['game']['name']))
        return self._log('\n'.join(text), Color.BLUE)

    def discord(self, directive:typing.Literal['connect', 'disconnect'] = 'connect', pipe:int = 0):
        """
        Utility for connecting to Discord
        self, directive:['connect', 'disconnect'] = 'connect', pipe:int = 0
        Pipe refers to which Discord client to connect to. May be rather fickle.
        """
        if directive == 'connect':
            self._log('Attempting to connect to Discord...', Color.YELLOW)
            self.client.connect(pipe)
        else:
            self.client.disconnect()
        return self._log('Done', Color.BLUE)

    def log(self):
        """
        Shows activity log
        """
        return self._log('\n'.join(self.client.gameLog), Color.BLUE)

# Exception handling
def APIExcept(r):
    text = r.text
    if '429' in r.text:
        text = 'You have reached your rate-limit for this resource.'
    elif '500' in r.text:
        text = 'The frontend is offline.'
    raise APIException(text)

class APIException(Exception):
    pass

class TitleIDMatchError(Exception):
    pass

class GameMatchError(Exception):
    pass
