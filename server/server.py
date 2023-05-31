# Created by Deltaion Lee (MCMi460) on Github

from flask import Flask, make_response, request, redirect, render_template, send_file
from flask_limiter import Limiter
from flask_sqlalchemy import SQLAlchemy
import sqlite3, requests, sys, os, time, json, multiprocessing, datetime, xmltodict, pickle, secrets
sys.path.append('../')
from api import *
from api.love2 import *
from api.private import CLIENT_ID, CLIENT_SECRET, HOST

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.abspath('sqlite/fcLibrary.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
limiter = Limiter(app, key_func = lambda : request.access_route[-1])

API_ENDPOINT:str = 'https://discord.com/api/v10'

local = False
port = 2277
version = 0.31
agent = '3DS-RPC/'

startTime = time.time() # Frontend
startDBTime(0)
startTime2 = 0 # Backend

@app.errorhandler(404)
def handler404(e):
    return render_template('dist/404.html')

disableBackendWarnings = False
try:
    if sys.argv[1] == 'ignoreBackend' and local:
        disableBackendWarnings = True
except:pass
if local:
    HOST = 'http://localhost:2277'

# Limiter limits
userPresenceLimit = '3/minute'
newUserLimit = '2/minute'
cdnLimit = '30/minute'

# Database files
titleDatabase = []
titlesToUID = []

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

# Create title cache
def cacheTitles():
    global titleDatabase, titlesToUID

    # Pull databases
    databasePath = './cache/'
    if not os.path.exists(databasePath):
        os.mkdir(databasePath)
    databasePath = os.path.join(databasePath, 'databases.dat')
    if os.path.isfile(databasePath):
        with open(databasePath, 'rb') as file:
            t = pickle.loads(file.read())
            titleDatabase = t[0]
            titlesToUID = t[1]
    else:
        titleDatabase = []
        titlesToUID = []

        bar = ProgressBar() # Create progress bar

        for region in ['US', 'JP', 'GB', 'KR', 'TW']:
            titleDatabase.append(
                xmltodict.parse(requests.get('https://samurai.ctr.shop.nintendo.net/samurai/ws/%s/titles?shop_id=1&limit=5000&offset=0' % region, verify = False).text)
            )
            bar.update(.5 / 5) # Update progress bar
            titlesToUID += requests.get('https://raw.githubusercontent.com/hax0kartik/3dsdb/master/jsons/list_%s.json' % region).json()
            bar.update(.5 / 5) # Update progress bar

        bar.end() # End the progress bar

        # Save databases to file
        with open(databasePath, 'wb') as file:
            file.write(pickle.dumps(
                (titleDatabase,
                titlesToUID)
            ))
        print('[Saved database to file]')

# Create entry in database with friendCode
def createUser(friendCode:int, addNewInstance:bool = False):
    if int(friendCode) == int(botFC):
        raise Exception('invalid FC')
    try:
        convertFriendCodeToPrincipalId(friendCode)
        if not addNewInstance:
            raise Exception('UNIQUE constraint failed: friends.friendCode')
        db.session.execute('INSERT INTO friends (friendCode, online, titleID, updID, lastAccessed, accountCreation, lastOnline, jeuFavori) VALUES (\'%s\', %s, %s, %s, %s, %s, %s, %s)' % (str(friendCode).zfill(12), False, '0', '0', time.time() + 300, time.time(), time.time(), 0))
        db.session.commit()
    except Exception as e:
        if 'UNIQUE constraint failed: friends.friendCode' in str(e):
            db.session.execute('UPDATE friends SET lastAccessed = %s WHERE friendCode = \'%s\'' % (time.time(), str(friendCode).zfill(12)))
            db.session.commit()

def fetchBearerToken(code:str):
    data = {
        'client_id': '%s' % CLIENT_ID,
        'client_secret': '%s' % CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': '%s/authorize' % HOST,
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    r = requests.post('%s/oauth2/token' % API_ENDPOINT, data = data, headers = headers)
    r.raise_for_status()
    return r.json()

def refreshBearer(token:str):
    user = userFromToken(token)
    data = {
        'client_id': '%s' % CLIENT_ID,
        'client_secret': '%s' % CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': user[1],
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    r = requests.post('%s/oauth2/token' % API_ENDPOINT, data = data, headers = headers)
    r.raise_for_status()
    token, user, pfp = createDiscordUser('', r.json())
    return token, user, pfp

def tokenFromID(ID:int):
    result = db.session.execute('SELECT * FROM discord WHERE ID = %s' % ID)
    result = result.fetchone()
    return result[4]

def userFromToken(token:str):
    result = db.session.execute('SELECT * FROM discord WHERE token = \'%s\'' % token)
    result = result.fetchone()
    if not result:
        raise Exception('invalid token!')
    return result[0:4]

def createDiscordUser(code:str, response:dict = None):
    if not response:
        response = fetchBearerToken(code)
    headers = {
        'Authorization': 'Bearer %s' % response['access_token'],
    }
    new = requests.get('https://discord.com/api/users/@me', headers = headers)
    user = new.json()
    token = secrets.token_hex(20)
    try:
        db.session.execute('INSERT INTO discord (ID, refresh, bearer, session, token, lastAccessed, generationDate) VALUES (%s, \'%s\', \'%s\', \'%s\', \'%s\', %s, %s)' % (user['id'], response['refresh_token'], response['access_token'], '', token, 0, time.time()))
        db.session.commit()
    except Exception as e:
        if 'UNIQUE constraint failed' in str(e):
            token = tokenFromID(user['id'])
            db.session.execute('UPDATE discord SET refresh = \'%s\', bearer = \'%s\', generationDate = %s WHERE token = \'%s\'' % (response['refresh_token'], response['access_token'], time.time(), token))
            db.session.commit()
    return token, user['username'], ('https://cdn.discordapp.com/avatars/%s/%s.%s' % (user['id'], user['avatar'], 'gif' if user['avatar'].startswith('a_') else 'png') if user['avatar'] else '')

def deleteDiscordUser(ID:int):
    db.session.execute('DELETE FROM discord WHERE ID = %s' % ID)
    db.session.execute('DELETE FROM discordFriends WHERE ID = %s' % ID)
    db.session.commit()

def getConnectedConsoles(ID:int):
    result = db.session.execute('SELECT * FROM discordFriends WHERE ID = %s' % ID)
    result = result.fetchall()
    return [ (result[1], bool(result[2])) for result in result ]

def sidenav():
    result = db.session.execute('SELECT BACKEND_UPTIME FROM config')
    result = result.fetchone()
    startTime2 = result[0]
    data = {
        'uptime': str(datetime.timedelta(seconds= int(time.time() - startTime))),
        'uptime-backend': ( 'Backend has been up for %s...' % str(datetime.timedelta(seconds= int(time.time() - int(startTime2)))) if not startTime2 == 0 else 'Backend: Offline' ),
        'status': 'Operational' if startTime2 != 0 else 'Offline',
    }
    return data

def userAgentCheck():
    userAgent = request.headers['User-Agent']
    try:
        if float(userAgent.replace(agent, '')) != version:
            raise Exception('client is not v%s' % version)
    except:
        raise Exception('this client is invalid')

def getPresence(friendCode:int, *, créerCompte:bool = True, ignoreUserAgent = False, ignoreBackend = False):
    try:
        if not ignoreUserAgent:
            userAgentCheck()
        result = db.session.execute('SELECT BACKEND_UPTIME FROM config')
        result = result.fetchone()
        startTime2 = result[0]
        if startTime2 == 0 and not ignoreBackend and not disableBackendWarnings:
            raise Exception('backend currently offline. please try again later')
        friendCode = str(friendCode).zfill(12)
        if créerCompte:
            createUser(friendCode, False)
        principalId = convertFriendCodeToPrincipalId(friendCode)
        result = db.session.execute('SELECT * FROM friends WHERE friendCode = \'%s\'' % friendCode)
        result = result.fetchone()
        if not result:
            raise Exception('friendCode not recognized\nHint: You may not have added the bot as a friend')
        if result[1] != 0:
            presence = {
                'titleID': result[2],
                'updateID': result[3],
                'joinable': bool(result[9]),
                'gameDescription': result[10],
                'game': getTitle(result[2], titlesToUID, titleDatabase),
                'disclaimer': 'all information regarding the title (User/Presence/game) is downloaded from Nintendo APIs',
            }
        else:
            presence = {}
        mii = result[8]
        if mii:
            mii = MiiData().mii_studio_url(mii)
        return {
            'Exception': False,
            'User': {
                'principalId': principalId,
                'friendCode': str(convertPrincipalIdtoFriendCode(principalId)).zfill(12),
                'online': bool(result[1]),
                'Presence': presence,
                'username': result[6],
                'message': result[7],
                'mii': mii,
                'accountCreation': result[5],
                'lastAccessed': result[4],
                'lastOnline': result[11],
                'favoriteGame': result[12],
            }
        }
    except Exception as e:
        return {
            'Exception': {
                'Error': str(e),
            }
        }

##################
# NON-API ROUTES #
##################

# Index page
@app.route('/')
def index():
    results = db.session.execute('SELECT * FROM friends WHERE online = True ORDER BY lastAccessed DESC LIMIT 6')
    results = results.fetchall()
    num = len(results)
    data = sidenav()

    data['active'] = [ ({
        'mii':MiiData().mii_studio_url(user[8]),
        'username':user[6],
        'game': getTitle(user[2], titlesToUID, titleDatabase),
        'friendCode': str(user[0]).zfill(12),
        'joinable': bool(user[9]),
    }) for user in results if user[6] and int(user[2]) != 0 ]
    for e in data['active']:
        if not e['game']['icon_url']:
            data['active'].remove(e)
    data['active'] = data['active'][:2]

    results = db.session.execute('SELECT * FROM friends ORDER BY accountCreation DESC LIMIT 6')
    results = results.fetchall()
    data['new'] = [ ({
        'mii':MiiData().mii_studio_url(user[8]),
        'username':user[6],
        'game': getTitle(user[2], titlesToUID, titleDatabase) if bool(user[1]) and int(user[2]) != 0 else '',
        'friendCode': str(user[0]).zfill(12),
        'joinable': bool(user[9]),
    }) for user in results if user[6] ]
    data['new'] = data['new'][:2]

    data['num'] = num

    response = make_response(render_template('dist/index.html', data = data))
    return response

# Index page
@app.route('/index.html')
def indexHTML():
    return index()

# Favicon
@app.route('/favicon.ico')
def favicon():
    return send_file('static/assets/img/favicon.ico')

# Settings page
@app.route('/settings.html')
def settings():
    response = make_response(render_template('dist/settings.html', data = sidenav()))
    return response

# Roster page
@app.route('/roster')
def roster():
    results = db.session.execute('SELECT * FROM friends ORDER BY accountCreation DESC LIMIT 8')
    results = results.fetchall()
    data = sidenav()
    data['title'] = 'New Users'

    data['users'] = [ ({
        'mii':MiiData().mii_studio_url(user[8]),
        'username':user[6],
        'game': getTitle(user[2], titlesToUID, titleDatabase),
        'friendCode': str(user[0]).zfill(12),
        'joinable': bool(user[9]),
    }) for user in results if user[6] ]

    response = make_response(render_template('dist/users.html', data = data))
    return response

# Active page
@app.route('/active')
def active():
    results = db.session.execute('SELECT * FROM friends WHERE online = True ORDER BY lastAccessed DESC')
    results = results.fetchall()
    data = sidenav()
    data['title'] = 'Active Users'

    data['users'] = [ ({
        'mii':MiiData().mii_studio_url(user[8]),
        'username':user[6],
        'game': getTitle(user[2], titlesToUID, titleDatabase),
        'friendCode': str(user[0]).zfill(12),
        'joinable': bool(user[9]),
    }) for user in results if user[6] ]

    response = make_response(render_template('dist/users.html', data = data))
    return response

# Register page
@app.route('/register.html')
def register():
    response = make_response(render_template('dist/register.html', data = {'botFC':'-'.join(botFC[i:i+4] for i in range(0, len(botFC), 4))}))
    return response

# Register page redirect
@app.route('/register')
def registerPage():
    return register()

# Connection page
@app.route('/connect')
def connect():
    return render_template('dist/connect.html', data = {'local':local})

@app.route('/discord')
def discordConnect():
    return redirect('/connect')

# Failure page
@app.route('/failure.html')
def failure():
    return render_template('dist/failure.html')

# Success page
@app.route('/success.html')
def success():
    data = {
        'url': 'user/' + request.args.get('fc'),
        'fc': request.args.get('fc'),
    }
    return render_template('dist/success.html', data = data)

# Consoles page
@app.route('/consoles')
def consoles():
    if not request.cookies.get('token'):
        return redirect('/')
    data = {
        'consoles': [],
    }
    try:
        id = userFromToken(request.cookies['token'])[0]
    except Exception as e:
        if 'invalid token' in str(e):
            response = make_response(redirect('/'))
            response.set_cookie('token', '', expires = 0)
            response.set_cookie('user', '', expires = 0)
            response.set_cookie('pfp', '', expires = 0)
            return response
    for console, active in getConnectedConsoles(id):
        result = db.session.execute('SELECT * FROM friends WHERE friendCode = \'%s\'' % console)
        result = result.fetchone()
        data['consoles'].append({
            'fc': '-'.join(console[i:i+4] for i in range(0, 12, 4)),
            'username': result[6],
            'active': active,
        })
    data.update(sidenav())
    response = render_template('dist/consoles.html', data = data)
    return response

@app.route('/user/<string:friendCode>/')
def userPage(friendCode:str):
    try:
        userData = getPresence(int(friendCode.replace('-', '')), créerCompte = False, ignoreUserAgent = True, ignoreBackend = True)
        if userData['Exception'] or not userData['User']['username']:
            raise Exception(userData['Exception'])
    except:
        return render_template('dist/404.html')
    if not userData['User']['online'] or not userData['User']['Presence']:
        userData['User']['Presence']['game'] = None
    userData['User']['favoriteGame'] = getTitle(userData['User']['favoriteGame'], titlesToUID, titleDatabase)
    if userData['User']['favoriteGame']['name'] == 'Home Screen':
        userData['User']['favoriteGame'] = None
    for i in ('accountCreation','lastAccessed','lastOnline'):
        if userData['User'][i] == 0:
            userData['User'][i] = 'Never'
        elif time.time() - userData['User'][i] > 86400:
            userData['User'][i] = datetime.datetime.fromtimestamp(userData['User'][i]).strftime('%b %d, %Y')
        elif time.time() - userData['User'][i] > 300:
            s = str(datetime.timedelta(seconds = int(time.time() - userData['User'][i]))).split(':')
            userData['User'][i] = s[0] + 'h, ' + s[1] + 'm, ' + s[2] + 's ago'
        else:
            userData['User'][i] = 'Just now'
    #print(userData) # COMMENT/DELETE THIS BEFORE COMMITTING
    userData.update(sidenav())
    response = make_response(render_template('dist/user.html', data = userData))
    return response

@app.route('/terms')
def terms():
    return redirect('https://github.com/MCMi460/3DS-RPC/blob/main/TERMS.md')

##############
# API ROUTES #
##############

# Create entry in database with friendCode
@app.route('/api/user/create/<int:friendCode>/', methods=['POST'])
@limiter.limit(newUserLimit)
def newUser(friendCode:int, userCheck:bool = True):
    try:
        if userCheck:
            userAgentCheck()
        createUser(friendCode, True)
        return {
            'Exception': False,
        }
    except Exception as e:
        return {
            'Exception': {
                'Error': str(e),
            }
        }

# Grab presence from friendCode
@app.route('/api/user/<int:friendCode>/', methods=['GET'])
@limiter.limit(userPresenceLimit)
def userPresence(friendCode:int, *, créerCompte:bool = True, ignoreUserAgent = False, ignoreBackend = False):
    return getPresence(friendCode, créerCompte = créerCompte, ignoreUserAgent = ignoreUserAgent, ignoreBackend = ignoreBackend)

# Alias
@app.route('/api/u/<int:friendCode>/', methods=['GET'])
@limiter.limit(userPresenceLimit)
def userAlias(friendCode:int):
    return userPresence(friendCode)

# Alias
@app.route('/api/u/c/<int:friendCode>/', methods=['POST'])
@limiter.limit(newUserLimit)
def newAlias1(friendCode:int):
    return newUser(friendCode)

# Alias
@app.route('/api/user/c/<int:friendCode>/', methods=['POST'])
@limiter.limit(newUserLimit)
def newAlias2(friendCode:int):
    return newUser(friendCode)

# Alias
@app.route('/api/u/create/<int:friendCode>/', methods=['POST'])
@limiter.limit(newUserLimit)
def newAlias3(friendCode:int):
    return newUser(friendCode)

# Toggle
@app.route('/api/toggle/<int:friendCode>/', methods=['POST'])
@limiter.limit(userPresenceLimit)
def toggler(friendCode:int):
    fc = str(convertPrincipalIdtoFriendCode(convertFriendCodeToPrincipalId(friendCode))).zfill(12)
    result = db.session.execute('SELECT * FROM friends WHERE friendCode = \'%s\'' % fc)
    result = result.fetchone()
    if not result:
        return 'failure!'
    f = request.data.decode('utf-8').split(',')
    token = f[0]
    active = bool(int(f[1]))
    id = userFromToken(token)[0]
    if active:
        db.session.execute('UPDATE discordFriends SET active = %s WHERE active = %s AND ID = %s' % (False, True, id))
        db.session.commit()
    result = db.session.execute('SELECT * FROM discordFriends WHERE ID = %s AND friendCode = \'%s\'' % (id, fc))
    result = result.fetchone()
    if result:
        db.session.execute('UPDATE discordFriends SET active = %s WHERE friendCode = \'%s\' AND ID = %s' % (active, fc, id))
        db.session.commit()
    else:
        db.session.execute('INSERT INTO discordFriends (ID, friendCode, active) VALUES (%s, \'%s\', %s)' % (id, fc, active))
        db.session.commit()
    return 'success!'

# Delete
@app.route('/api/delete/<int:friendCode>/', methods=['POST'])
@limiter.limit(userPresenceLimit)
def deleter(friendCode:int):
    fc = str(convertPrincipalIdtoFriendCode(convertFriendCodeToPrincipalId(friendCode))).zfill(12)
    token = request.data.decode('utf-8')
    id = userFromToken(token)[0]
    db.session.execute('DELETE FROM discordFriends WHERE friendCode = \'%s\' AND ID = %s' % (fc, id))
    db.session.commit()
    return 'success!'

# Make Nintendo's cert a 'secure' cert
@app.route('/cdn/i/<string:file>/', methods=['GET'])
@limiter.limit(cdnLimit)
def cdnImage(file:str):
    response = make_response(requests.get('https://kanzashi-ctr.cdn.nintendo.net/i/%s' % file, verify = False).content)
    response.headers['Content-Type'] = 'image/jpeg'
    return response

# Local image cache
@app.route('/cdn/l/<string:file>/', methods=['GET'])
@limiter.limit(cdnLimit)
def localImageCdn(file:str):
    file = hex(int(file, 16)).replace('0x', '').zfill(16).upper()
    return send_file('cache/' + file + '.png')

# Login route
@app.route('/login', methods=['POST'])
@limiter.limit(newUserLimit)
def login():
    try:
        fc = str(convertPrincipalIdtoFriendCode(convertFriendCodeToPrincipalId(request.form['fc']))).zfill(12)
        newUser(fc, False)
    except:
        return redirect('/failure.html')
    return redirect(f'/success.html?fc={fc}')

# Discord route
@app.route('/authorize')
@limiter.limit(newUserLimit)
def authorize():
    if not request.args.get('code'):
        return render_template('dist/404.html')
    token, user, pfp = createDiscordUser(request.args['code'])
    response = make_response(redirect('/consoles'))
    response.set_cookie('token', token, expires = datetime.datetime.now() + datetime.timedelta(days = 30))
    response.set_cookie('user', user, expires = datetime.datetime.now() + datetime.timedelta(days = 30))
    response.set_cookie('pfp', pfp, expires = datetime.datetime.now() + datetime.timedelta(days = 30))
    return response

@app.route('/refresh')
def refresh():
    if local:
        try:
            token, user, pfp = refreshBearer(request.cookies['token'])
            response = make_response(redirect('/consoles'))
            response.set_cookie('token', token, expires = datetime.datetime.now() + datetime.timedelta(days = 30))
            response.set_cookie('user', user, expires = datetime.datetime.now() + datetime.timedelta(days = 30))
            response.set_cookie('pfp', pfp, expires = datetime.datetime.now() + datetime.timedelta(days = 30))
            return response
        except:
            deleteDiscordUser(userFromToken(request.cookies['token'])[0])
    return redirect('/404.html')

if __name__ == '__main__':
    cacheTitles()
    if local:
        app.run(host = '0.0.0.0', port = port)
    else:
        import gevent.pywsgi
        server = gevent.pywsgi.WSGIServer(('0.0.0.0', port), app)
        server.serve_forever()
