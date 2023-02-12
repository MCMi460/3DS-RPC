# Created by Deltaion Lee (MCMi460) on Github

import requests, os, sys, time
import xmltodict, json
import pickle
import asyncio, threading
sys.path.append('../')
from api import *
import pypresence

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

local = False
version = 0.31

host = 'https://3ds.mi460.dev' # Change the host as you'd wish
if local:
    host = 'http://127.0.0.1:2277'

## The below contains 3ds.mi460.dev-specific information
## You will have to provide your own 'bot' FC if you are planning
## on running your own front and backend.
convertFriendCodeToPrincipalId(botFC) # A quick verification check

_REGION = typing.Literal['ALL', 'US', 'JP', 'GB', 'KR', 'TW']
path = getAppPath()
privateFile = os.path.join(path, 'private.txt')

class Client():
    def __init__(self, friendCode: str, *, GUI: bool = False):
        ### Maintain typing ###
        friendCode = str(convertPrincipalIdtoFriendCode(convertFriendCodeToPrincipalId(friendCode))).zfill(12) # Friend Code check
        with open(privateFile, 'w') as file: # Save FC to file
            file.write(json.dumps({
                'friendCode': friendCode,
            }))

        # FC variables
        self.friendCode = friendCode

        # Client-config
        self.GUI = GUI
        self.connected = False

        # Discord-related variables
        self.currentGame = {'@id': None}

        # Game logging
        self.gameLog = []

    # Get from API
    def APIget(self, route:str, content:dict = {}):
        return requests.get(host + '/api/' + route, data = content, headers = {'User-Agent':'3DS-RPC/%s' % version,})

    # Post to API
    def APIpost(self, route:str, content:dict = {}):
        return requests.post(host + '/api/' + route, data = content, headers = {'User-Agent':'3DS-RPC/%s' % version,})

    # Connect to PyPresence
    def connect(self, pipe:int = 0):
        self.rpc = pypresence.Presence('1023094010383970304', pipe = pipe)
        self.rpc.connect()
        self.connected = True

    # Disconnect
    def disconnect(self):
        try:self.rpc.clear()
        except:pass
        try:self.rpc.close()
        except:pass
        self.rpc = None
        self.connected = False

    def login(self):
        r = self.APIpost('user/create/%s' % self.friendCode)
        try:
            r = r.json()
        except:
            APIExcept(r)
        if r['Exception']:
            if not 'UNIQUE constraint failed: friends.friendCode' in r['Exception']['Error']:
                raise APIException(r['Exception'])
        return r

    def fetch(self):
        r = self.APIget('user/%s' % self.friendCode)
        try:
            r = r.json()
        except:
            APIExcept(r)
        if r['Exception']:
            if 'not recognized' in r['Exception']['Error']:
                print('%sRemember, the bot\'s friend code is as follows:\n%s%s' % (Color.YELLOW, '-'.join(botFC[i:i+4] for i in range(0, len(botFC), 4)), Color.DEFAULT))
            raise APIException(r['Exception'])
        return r

    def loop(self):
        userData = self.fetch();self.userData = userData
        presence = userData['User']['Presence']

        _pass = None
        if userData['User']['online'] and presence:

            game = presence['game']

            log = 'Update'
            if self.currentGame != game:
                log += ' [%s -> %s]' % (self.currentGame['@id'], game['@id'])
                self.currentGame = game
                self.start = int(time.time())
            kwargs = {
                'details': game['name'],
                'start': self.start,
                # buttons = [{'label': 'Label', 'url': 'http://DOMAIN.WHATEVER'},]
                # eShop URL could be https://api.qrserver.com/v1/create-qr-code/?data=ESHOP://{uid}
                # But... that wouldn't be very convenient. It's unfortunate how Nintendo does not have an eShop website for the 3DS
                # Include View Profile setting?
                # Certainly something when presence['joinable'] == True
            }
            if game['icon_url']:
                kwargs['large_image'] = game['icon_url'].replace('/cdn/i/', host + '/cdn/i/')
                kwargs['large_text'] = game['name']
            if presence['gameDescription']:
                kwargs['state'] = presence['gameDescription']
            if userData['User']['username']:
                kwargs['buttons'] = [{'label': 'Profile', 'url': host + '/user/' + userData['User']['friendCode']},]
            if self.connected:self.rpc.update(**kwargs)
        else:
            log = 'Clear [%s -> %s]' % (self.currentGame['@id'], None)
            self.currentGame = {'@id': None}
            if self.connected:self.rpc.clear()
        self.gameLog.append(log)

    def background(self):
        try:
            if self.GUI:
                asyncio.set_event_loop(asyncio.new_event_loop())

                import nest_asyncio
                nest_asyncio.apply()
                threading.Thread(target = __import__('IPython').embed, daemon = True).start()

                self.connect() # Connect to Discord
                # Consider removing this here ^^ @MCMi460

            self.login() # Create account if not yet existent
            while True:
                self.loop()
                time.sleep(30) # Wait 30 seconds between calls
        except Exception as e:
            print(Color.RED + 'Failed')
            print(e)
            os._exit(0)

def main():
    friendCode = None

    # Create directory for logging and friend code saving
    if not os.path.isdir(path):
        os.mkdir(path)
    if not os.path.isfile(privateFile):
        print('%sPlease take this time to add the bot\'s FC to your target 3DS\' friends list.\n%sBot FC: %s%s' % (Color.YELLOW, Color.DEFAULT, Color.BLUE, '-'.join(botFC[i:i+4] for i in range(0, len(botFC), 4))))
        input('%s[Press enter to continue]%s' % (Color.GREEN, Color.DEFAULT))
        friendCode = input('Please enter your 3DS\' friend code\n> %s' % Color.PURPLE)
        print(Color.DEFAULT, end = '')
    else:
        with open(privateFile, 'r') as file:
            js = json.loads(file.read())
            friendCode = js['friendCode']

    try:
        client = Client(friendCode)
    except (AssertionError, FriendCodeValidityError) as e:
        if os.path.isfile(privateFile):
            os.remove(privateFile)
        raise e

    threading.Thread(target = client.background, daemon = True).start() # Start client background

    # Begin main thread for user configuration
    con = Console(client)
    try:
        con.discord('connect')
    except Exception as e:
        con._log('\'%s\'\nFailed to connect to Discord! Try again with the \'discord\' command' % e, Color.RED)
    con._main()

if __name__ == '__main__':
    main()
