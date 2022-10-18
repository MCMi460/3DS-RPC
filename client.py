import requests

host = 'http://127.0.0.1'
port = '2277'

def APIget(route:str, content:dict = {}):
    return requests.get(host + ':' + port + '/' + route, data = content)

def APIpost(route:str, content:dict = {}):
    return requests.post(host + ':' + port + '/' + route, data = content)

def main():
    fc = 0
    r = APIpost('user/c/%s' % fc)
    print(r.content)

if __name__ == '__main__':
    main()
