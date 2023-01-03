# Created by Deltaion Lee (MCMi460) on Github

import requests, os, sys, time
import xmltodict, json
import pickle
sys.path.append('../')
from api import *
import pypresence
from typing import Literal, get_args

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

local = False
version = 0.21

host = 'https://3ds.mi460.dev' # Change the host as you'd wish
if local:
    host = 'http://127.0.0.1:2277'

## The below contains 3ds.mi460.dev-specific information
## You will have to provide your own 'bot' FC if you are planning
## on running your own front and backend.
convertFriendCodeToPrincipalId(botFC) # A quick verification check

_REGION = Literal['US', 'JP', 'GB', 'KR', 'TW', 'ALL']
path = getAppPath()
privateFile = os.path.join(path, 'private.txt')

class APIException(Exception):
    pass

class TitleIDMatchError(Exception):
    pass

class GameMatchError(Exception):
    pass

class Client():
    def __init__(self, region: _REGION, friendCode: str, saveTitleFiles:bool = True):
        ### Maintain typing ###
        assert region in get_args(_REGION), '\'%s\' does not match _REGION' % region # Region assertion
        friendCode = str(convertPrincipalIdtoFriendCode(convertFriendCodeToPrincipalId(friendCode))).zfill(12) # Friend Code check
        with open(privateFile, 'w') as file: # Save FC to file
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
        self.region = (self.region,)
        if self.region[0] == 'ALL':
            self.region = list(get_args(_REGION))
            del self.region[-1]
        databasePath = os.path.join(path, 'databases.dat')
        if os.path.isfile(databasePath):
            with open(databasePath, 'rb') as file:
                t = pickle.loads(file.read())
                self.titleDatabase = t[0]
                self.titlesToUID = t[1]
        else:
            self.titleDatabase = []
            self.titlesToUID = []

            bar = ProgressBar() # Create progress bar

            for region in self.region:
                self.titleDatabase.append(
                    xmltodict.parse(requests.get('https://samurai.ctr.shop.nintendo.net/samurai/ws/%s/titles?shop_id=1&limit=5000&offset=0' % region, verify = False).text)
                )
                bar.update(.5 / len(self.region)) # Update progress bar
                self.titlesToUID += requests.get('https://raw.githubusercontent.com/hax0kartik/3dsdb/master/jsons/list_%s.json' % region, stream = True).json()
                bar.update(.5 / len(self.region)) # Update progress bar

            bar.end() # End the progress bar

        # Save databases to file
        if saveTitleFiles and not os.path.isfile(databasePath):
            with open(databasePath, 'wb') as file:
                file.write(pickle.dumps(
                    (self.titleDatabase,
                    self.titlesToUID)
                ))
            print('[Saved database to file]')

    # Get from API
    def APIget(self, route:str, content:dict = {}):
        return requests.get(host + '/api/' + route, data = content, headers = {'User-Agent':'3DS-RPC/%s' % version,})

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
            for region in self.titleDatabase:
                for title in region['eshop']['contents']['content']:
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
                # buttons = [{'label': 'Label', 'url': 'http://DOMAIN.WHATEVER'},]
                # eShop URL could be https://api.qrserver.com/v1/create-qr-code/?data=ESHOP://{uid}
                # But... that wouldn't be very convenient. It's unfortunate how Nintendo does not have an eShop website for the 3DS
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
    if not os.path.isfile(privateFile):
        print('Please take this time to add the bot\'s FC to your target 3DS\' friends list.\nBot FC: %s' % '-'.join(botFC[i:i+4] for i in range(0, len(botFC), 4)))
        input('[Press enter to continue]')
        friendCode = input('Please enter your 3DS\' friend code\n> \033[0;35m')
        print('\033[0m', end = '')
    else:
        with open(privateFile, 'r') as file:
            js = json.loads(file.read())
            friendCode = js['friendCode']
            region = js.get('region')
    if not region:
        region = input('Please enter your 3DS\' region [%s]\n\033[93m(You may enter \'ALL\' if you are planning to play with multiple regions\' games)\033[0m\n> \033[0;35m' % ', '.join(get_args(_REGION)))
        print('\033[0m', end = '')
        if region == 'ALL':
            r = input('- \033[91mEnabling ALL regions may take a few minutes to download. Is this agreeable?\033[0m\n- > \033[0;35m')
            if not r.lower().startswith('y'):
                return
        print('\033[0m')

    try:
        client = Client(region, friendCode)
    except (AssertionError, FriendCodeValidityError) as e:
        if os.path.isfile(privateFile):
            os.remove(privateFile)
        raise e
    while True:
        client.loop()
        time.sleep(30)

if __name__ == '__main__':
    main()
