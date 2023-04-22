# Created by Deltaion Lee (MCMi460) on Github

from flask import Flask, make_response, request, redirect, render_template
from flask_limiter import Limiter
from flask_sqlalchemy import SQLAlchemy
import sqlite3, requests, sys, os, time, json, multiprocessing, datetime, xmltodict, pickle
sys.path.append('../')
from api import *
from api.love2 import *

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.abspath('sqlite/fcLibrary.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
limiter = Limiter(app, key_func = lambda : request.access_route[-1])

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
        db.session.execute('INSERT INTO friends (friendCode, online, titleID, updID, lastAccessed, accountCreation, lastOnline, jeuFavori) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (str(friendCode).zfill(12), False, '0', '0', time.time() + 300, time.time(), time.time(), 0))
        db.session.commit()
    except Exception as e:
        if 'UNIQUE constraint failed: friends.friendCode' in str(e):
            db.session.execute('UPDATE friends SET lastAccessed = ? WHERE friendCode = ?', (time.time(), str(friendCode).zfill(12)))
            db.session.commit()

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
        result = db.session.execute('SELECT * FROM friends WHERE friendCode = ?', (friendCode,))
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
    results = db.session.execute('SELECT * FROM friends WHERE online = True ORDER BY lastAccessed DESC LIMIT 2')
    results = results.fetchall()
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

    results = db.session.execute('SELECT * FROM friends ORDER BY accountCreation DESC LIMIT 2')
    results = results.fetchall()
    data['new'] = [ ({
        'mii':MiiData().mii_studio_url(user[8]),
        'username':user[6],
        'game': getTitle(user[2], titlesToUID, titleDatabase) if bool(user[1]) and int(user[2]) != 0 else '',
        'friendCode': str(user[0]).zfill(12),
        'joinable': bool(user[9]),
    }) for user in results if user[6] ]

    response = make_response(render_template('dist/index.html', data = data))
    return response

# Index page
@app.route('/index.html')
def indexHTML():
    return index()

# Settings page
@app.route('/settings.html')
def settings():
    response = make_response(render_template('dist/settings.html', data = sidenav()))
    return response

# Register page
@app.route('/register.html')
def register():
    response = make_response(render_template('dist/register.html', data = {'botFC':'-'.join(botFC[i:i+4] for i in range(0, len(botFC), 4))}))
    return response

# Failure page
@app.route('/failure.html')
def failure():
    return render_template('dist/failure.html')

# Success page
@app.route('/success.html')
def success():
    data = {
        'url': 'user/' + request.args.get('fc'),
    }
    return render_template('dist/success.html', data = data)

@app.route('/user/<string:friendCode>/')
def userPage(friendCode:str):
    try:
        userData = getPresence(int(friendCode.replace('-', '')), créerCompte = False, ignoreUserAgent = True, ignoreBackend = True)
        if userData['Exception'] or not userData['User']['username']:
            raise Exception(userData['Exception'])
    except:
        return render_template('dist/404.html')
    if userData['User']['online'] and userData['User']['Presence']:
        userData['User']['Presence']['game'] = getTitle(userData['User']['Presence']['titleID'], titlesToUID, titleDatabase)
    else:
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

# Make Nintendo's cert a 'secure' cert
@app.route('/cdn/i/<string:file>/', methods=['GET'])
@limiter.limit(cdnLimit)
def cdnImage(file:str):
    response = make_response(requests.get('https://kanzashi-ctr.cdn.nintendo.net/i/%s' % file, verify = False).content)
    response.headers['Content-Type'] = 'image/jpeg'
    return response

# Login route
@app.route('/login', methods=['POST'])
def login():
    try:
        fc = str(convertPrincipalIdtoFriendCode(convertFriendCodeToPrincipalId(request.form['fc']))).zfill(12)
        newUser(fc, False)
    except:
        return redirect('/failure.html')
    return redirect(f'/success.html?fc={fc}')

if __name__ == '__main__':
    cacheTitles()
    if local:
        app.run(host = '0.0.0.0', port = port)
    else:
        import gevent.pywsgi
        server = gevent.pywsgi.WSGIServer(('0.0.0.0', port), app)
        server.serve_forever()
