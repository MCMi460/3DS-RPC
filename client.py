import requests, os, sys, time
import xmltodict, json
from api import *
from api.private import *
import pypresence
from typing import Literal, get_args

port = '2277'
host = 'http://127.0.0.1' + (':' + port if port else '')

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

        # Region and FC variables
        self.region = region
        self.friendCode = friendCode

        # Try signing in
        ## If there is an error other than the user's account not existing, then error
        try:
            self.signUp()
        except APIException as ex:
            if not 'UNIQUE constraint failed: friends.friendCode' in str(ex):
                raise ex

        # Pull databases
        self.titleDatabase = xmltodict.parse(requests.get('https://samurai.ctr.shop.nintendo.net/samurai/ws/%s/titles?shop_id=1&limit=5000&offset=0' % self.region, verify = False).text)
        self.titlesToUID = requests.get('https://raw.githubusercontent.com/hax0kartik/3dsdb/master/jsons/list_%s.json' % self.region).json()

        # Connect to Discord
        self.connect()
        # Discord-related variables
        self.currentGame = {'@id': None}

    # Get from API
    def APIget(self, route:str, content:dict = {}):
        return requests.get(host + '/' + route, data = content)

    # Post to API
    def APIpost(self, route:str, content:dict = {}):
        return requests.post(host + '/' + route, data = content)

    # Connect to PyPresence
    def connect(self):
        self.rpc = pypresence.Presence('1023094010383970304')
        self.rpc.connect()

    def signUp(self):
        r = self.APIpost('user/c/%s' % self.friendCode)
        try:
            r = r.json()
        except:
            raise APIException(r.content)
        if r['Exception']:
            raise APIException(r['Exception'])

    def fetch(self):
        r = self.APIget('user/%s' % self.friendCode)
        try:
            r = r.json()
        except:
            raise APIException(r.content)
        if r['Exception']:
            raise APIException(r['Exception'])
        return r

    def loop(self):
        userData = self.fetch()
        presence = userData['User']['Presence']

        if userData['User']['online'] and presence:
            uid = None
            tid = hex(int(presence['titleID']))[2:].zfill(16).upper()
            for game in self.titlesToUID:
                if game['TitleID'] == tid:
                    uid = game['UID']
                    break
            if not uid:
                raise TitleIDMatchError('unknown title id: %s' % tid)

            game = None
            #print(self.titleDatabase)
            for title in self.titleDatabase['eshop']['contents']['content']:
                if title['title']['@id'] == uid:
                    game = title['title']
                    break
            if not game:
                raise GameMatchError('unknown game: %s' % uid)

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
        time.sleep(30)

def main():
    # Create directory for logging and friend code saving
    path = getAppPath()
    if not os.path.isdir(path):
        os.mkdir(path)
    privateFile = os.path.join(path, 'private.txt')
    if not os.path.isfile(privateFile):
        friendCode = input('Please enter your 3DS\' friend code\n> ')
        with open(privateFile, 'w') as file:
            file.write(json.dumps({
                'friendCode': friendCode,
            }))
    else:
        with open(privateFile, 'r') as file:
            friendCode = json.loads(file.read())['friendCode']

    client = Client('US', friendCode)
    while True:
        client.loop()

if __name__ == '__main__':
    main()
