# Created by Deltaion Lee (MCMi460) on Github

import requests, os, sys, time
import xmltodict, json
import pickle
import asyncio, threading
try:
    from api import *
except:
    sys.path.append('../')
    from api import *
import pypresence

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

local = False
version = 0.31

host = 'https://3dsrpc.com' # Change the host as you'd wish
if local:
    host = 'http://127.0.0.1:2277'

## The below contains 3dsrpc.com-specific information
## You will have to provide your own 'bot' FC if you are planning
## on running your own front and backend.
friend_code_to_principal_id(nintendoBotFC) # A quick verification check

_REGION = typing.Literal['ALL', 'US', 'JP', 'GB', 'KR', 'TW']
path = getAppPath()
privateFile = os.path.join(path, 'private.txt')
logFile = os.path.join(path, 'logs.txt')

# Config template
configTemplate = {
    'friendCode': '',
    'showElapsed': True,
    'showProfileButton': False,
    'showSmallImage': False,
    'fetchTime': 30,
}

def log(text:str):
    with open(logFile, 'a') as file:
        file.write('%s: %s\n' % (time.time(), text.replace('\n',' ')))
    print(Color.RED + text)

class Client():
    def __init__(self, friendCode: str, config:dict, *, GUI = None):
        ### Maintain typing ###
        friendCode = str(principal_id_to_friend_code(friend_code_to_principal_id(friendCode))).zfill(12) # Friend Code check
        with open(privateFile, 'w') as file: # Save FC and config to file
            js = configTemplate
            js['friendCode'] = friendCode
            for key in config.keys():
                if key in configTemplate.keys():
                    js[key] = config[key]
            file.write(json.dumps(js))

        # FC variables
        self.friendCode = friendCode

        # Client-config
        self.connected = False
        self.userData = {}

        # Discord-related variables
        self.currentGame = {'@id': None}
        self.showElapsed = js['showElapsed']
        self.showProfileButton = js['showProfileButton']
        self.showSmallImage = js['showSmallImage']
        self.fetchTime = js['fetchTime']

        # Game logging
        self.gameLog = []

        # GUI-related
        self.GUI = GUI

    # Reflect to config file
    def reflectConfig(self):
        with open(privateFile, 'w') as file:
            js = configTemplate
            for key in js.keys():
                js[key] = self.__dict__[key]
            file.write(json.dumps(js))

    # Get from API
    def APIget(self, route:str, content:dict = {}):
        return requests.get(host + '/api/' + route, data = content, headers = {'User-Agent':'3DS-RPC/%s' % version,})

    # Post to API
    def APIpost(self, route:str, content:dict = {}):
        return requests.post(host + '/api/' + route, data = content, headers = {'User-Agent':'3DS-RPC/%s' % version,})

    # Connect to PyPresence
    def connect(self, pipe:str = '0'):
        try:
            self.rpc = pypresence.Presence('1023094010383970304', pipe = pipe)
            self.rpc.connect()
        except Exception as e:
            if self.GUI:
                self.GUI.error(str(e), traceback.format_exc())
            else:
                raise e
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
                print('%sRemember, the bot\'s friend code is as follows:\n%s%s' % (Color.YELLOW, '-'.join(nintendoBotFC[i:i+4] for i in range(0, len(nintendoBotFC), 4)), Color.DEFAULT))
            raise APIException(r['Exception'])
        return r

    def loop(self):
        userData = self.fetch();self.userData = userData
        presence = userData['User']['Presence']

        _pass = None
        if userData['User']['online'] and presence:

            game = presence['game']

            logger = 'Update'
            if self.currentGame != game:
                logger += ' [%s -> %s]' % (self.currentGame['@id'], game['@id'])
                self.currentGame = game
                self.start = int(time.time())
            kwargs = {
                'details': game['name'],
                # buttons = [{'label': 'Label', 'url': 'http://DOMAIN.WHATEVER'},]
                # eShop URL could be https://api.qrserver.com/v1/create-qr-code/?data=ESHOP://{uid}
                # But... that wouldn't be very convenient. It's unfortunate how Nintendo does not have an eShop website for the 3DS
                # Include View Profile setting?
                # Certainly something when presence['joinable'] == True
            }
            if game['icon_url']:
                kwargs['large_image'] = game['icon_url'].replace('/cdn/', host + '/cdn/')
                kwargs['large_text'] = game['name']
            if presence['gameDescription']:
                kwargs['state'] = presence['gameDescription']
            if self.showProfileButton and userData['User']['username']:
                kwargs['buttons'] = [{'label': 'Profile', 'url': host + '/user/' + userData['User']['friendCode']},]
            if self.showElapsed:
                kwargs['start'] = self.start
            if self.showSmallImage and userData['User']['username'] and game['icon_url']:
                kwargs['small_image'] = userData['User']['mii']['face']
                kwargs['small_text'] = '-'.join(userData['User']['friendCode'][i:i+4] for i in range(0, 12, 4))
            for key in list(kwargs): # Blatant rip from OpenEmuRPC (also made by me. Check it out if you want)
                if isinstance(kwargs[key], str) and not 'image' in key:
                    if len(kwargs[key]) < 2:
                        del kwargs[key]
                    elif len(kwargs[key]) > 128:
                        kwargs[key] = kwargs[key][:128]
            if self.connected:self.rpc.update(**kwargs)
            if self.GUI:self.GUI.update(kwargs)
        else:
            logger = 'Clear [%s -> %s]' % (self.currentGame['@id'], None)
            self.currentGame = {'@id': None}
            if self.connected:self.rpc.clear()
            if self.GUI:self.GUI.update(None)
        self.gameLog.append(logger)

    def background(self):
        try:
            self.login() # Create account if not yet existent
            while True:
                self.loop()
                time.sleep(self.fetchTime) # Wait 30 seconds between calls
        except Exception as e:
            if self.GUI:
                self.GUI.error(str(e), traceback.format_exc())
            else:
                log('Failed\n' + str(e))
                print(traceback.format_exc())
                os._exit(0)

def main():
    friendCode = None

    # Create directory for logging and friend code saving
    if not os.path.isdir(path):
        os.mkdir(path)
    try:
        if os.path.isfile(privateFile):
            with open(privateFile, 'r') as file:
                js = json.loads(file.read())
                friendCode = js['friendCode']
                config = js
                del config['friendCode']
        else:
            raise Exception()
    except:
        print('%sPlease take this time to add the bot\'s FC to your target 3DS\' friends list.\n%sBot FC: %s%s' % (Color.YELLOW, Color.DEFAULT, Color.BLUE, '-'.join(nintendoBotFC[i:i+4] for i in range(0, 12, 4))))
        input('%s[Press enter to continue]%s' % (Color.GREEN, Color.DEFAULT))
        friendCode = input('Please enter your 3DS\' friend code\n> %s' % Color.PURPLE)
        config = {}
        print(Color.DEFAULT, end = '')

    try:
        client = Client(friendCode, config)
    except (AssertionError, FriendCodeValidityError) as e:
        if os.path.isfile(privateFile):
            os.remove(privateFile)
        raise e

    # Begin main thread for user configuration
    con = Console(client)
    try:
        client.connect()
    except Exception as e:
        con._log('\'%s\'\nFailed to connect to Discord! Try again with the \'discord\' command' % e, Color.RED)

    threading.Thread(target = client.background, daemon = True).start() # Start client background

    con._main() # Begin main loop for console program

if __name__ == '__main__':
    main()
