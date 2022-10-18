import requests, os, sys
import xmltodict
from api import *
from api.private import *

host = 'http://127.0.0.1'
port = '2277'

titleDatabase = xmltodict.parse(requests.get('http://3dsdb.com/xml.php').text)

def APIget(route:str, content:dict = {}):
    return requests.get(host + ':' + port + '/' + route, data = content)

def APIpost(route:str, content:dict = {}):
    return requests.post(host + ':' + port + '/' + route, data = content)

def main():
    path = os.path.expanduser('~/Documents/3DS-RPC/')
    if not os.path.isdir(path):
        os.mkdir(path)
    fc = privFriend
    #r = APIpost('user/c/%s' % fc)
    #print(r.text)
    r = APIget('user/%s' % fc)
    presence = r.json()['User']['Presence']
    if r.json()['User']['online'] and presence:
        for release in titleDatabase['releases']['release']:
            if hex(int(presence['titleID']))[2:] in release['titleid'].lower():
                print(release)
                break

if __name__ == '__main__':
    main()
