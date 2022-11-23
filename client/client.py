# Created by Deltaion Lee (MCMi460) on Github

import requests, os, sys, time
import xmltodict, json
sys.path.append('../')
from api import *
import pypresence
from typing import Literal, get_args

local = True
version = 0.2

host = 'https://3ds.mi460.dev' # Change the host as you'd wish
if local:
    host = 'http://127.0.0.1:2277'

## The below contains 3ds.mi460.dev-specific information
## You will have to provide your own 'bot' FC if you are planning
## on running your own front and backend.
botFC = str(233790548638) # FC == Friendcode
convertFriendCodeToPrincipalId(botFC) # A quick verification check

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

_REGION = Literal['US', 'JP', 'GB', 'KR', 'TW']
path = getAppPath()

class APIException(Exception):
    pass

class TitleIDMatchError(Exception):
    pass

class GameMatchError(Exception):
    pass

class Client():
    def __init__(self, region: _REGION, friendCode: str):
        ### Maintain typing ###
        assert region in get_args(_REGION), '\'%s\' does not match _REGION' % region # Region assertion
        convertFriendCodeToPrincipalId(friendCode) # Friend Code check
        with open(os.path.join(path, 'private.txt'), 'w') as file: # Save FC to file
            file.write(json.dumps({
                'friendCode': friendCode,
                'region': region,
            }))

        # Region and FC variables
        self.region = region
        self.friendCode = friendCode

        # Connect to Discord
        self.connect()
        # Discord-related variables
        self.currentGame = {'@id': None}

        # Pull databases
        self.titleDatabase = xmltodict.parse(requests.get('https://samurai.ctr.shop.nintendo.net/samurai/ws/%s/titles?shop_id=1&limit=5000&offset=0' % self.region, verify = False).text)
        self.titlesToUID = requests.get('https://raw.githubusercontent.com/hax0kartik/3dsdb/master/jsons/list_%s.json' % self.region).json()
        ## Warning; the above does not account for games being played by a user who has removed the region lock on their system
        ## Please consider fixing this in the future, @MCMi460

    # Get from API
    def APIget(self, route:str, content:dict = {}):
        return requests.get(host + '/' + route, data = content, headers = {'User-Agent':'3DS-RPC/%s' % version,})

    # Connect to PyPresence
    def connect(self):
        self.rpc = pypresence.Presence('1023094010383970304')
        self.rpc.connect()

    def fetch(self):
        r = self.APIget('user/%s' % self.friendCode)
        try:
            r = r.json()
        except:
            raise APIException(r.content)
        if r['Exception']:
            if 'not recognized' in r['Exception']['Error']:
                print('\033[93mRemember, the bot\'s friend code is as follows:\n%s\033[0m' % '-'.join(botFC[i:i+4] for i in range(0, len(botFC), 4)))
            raise APIException(r['Exception'])
        return r

    def loop(self):
        userData = self.fetch()
        presence = userData['User']['Presence']
        if userData['User']['notifications']:
            notifications = [ json.loads(n) for n in userData['User']['notifications'].split('|') ]
        else:
            notifications = []

        _pass = None
        if userData['User']['online'] and presence:
            uid = None
            tid = hex(int(presence['titleID']))[2:].zfill(16).upper()
            _template = {
                'name': 'Unknown 3DS App',
                'icon_url': 'logo',
                '@id': tid,
            }
            for game in self.titlesToUID:
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
            for title in self.titleDatabase['eshop']['contents']['content']:
                if title['title']['@id'] == uid:
                    game = title['title']
                    break
            if not game:
                _pass = _template
                # raise GameMatchError('unknown game: %s' % uid)
            if _pass:
                game = _pass

            print('Update', end = '')
            if self.currentGame != game:
                print(' [%s -> %s]' % (self.currentGame['@id'], game['@id']), end = '')
                self.currentGame = game
                self.start = int(time.time())
            print()
            self.rpc.update(
                details = game['name'],
                large_image = game['icon_url'].replace('https://kanzashi-ctr.cdn.nintendo.net/i/', host + '/cdn/i/'),
                large_text = game['name'],
                start = self.start,
                #buttons = [{'label': 'Nintendo eShop', 'url': game[]},]
                # eShop URL could be https://api.qrserver.com/v1/create-qr-code/?data=ESHOP://{uid}
                # But that's dumb so no
            )
        else:
            print('Clear [%s -> %s]' % (self.currentGame['@id'], None))
            self.currentGame = {'@id': None}
            self.rpc.clear()

def main():
    friendCode = None
    region = None

    # Create directory for logging and friend code saving
    if not os.path.isdir(path):
        os.mkdir(path)
    privateFile = os.path.join(path, 'private.txt')
    if not os.path.isfile(privateFile):
        print('Please take this time to add the bot\'s FC to your target 3DS\' friends list.\nBot FC: %s' % '-'.join(botFC[i:i+4] for i in range(0, len(botFC), 4)))
        input('[Press enter to continue]')
        friendCode = input('Please enter your 3DS\' friend code\n> ')
    else:
        with open(privateFile, 'r') as file:
            js = json.loads(file.read())
            friendCode = js['friendCode']
            region = js.get('region')
    if not region:
        region = input('Please enter your 3DS\' region [%s]\n> ' % ', '.join(get_args(_REGION)))

    client = Client(region, friendCode)
    while True:
        client.loop()
        time.sleep(30)

if __name__ == '__main__':
    main()
