# Created by Deltaion Lee (MCMi460) on Github

from enum import IntEnum
from flask import Flask, make_response, request, redirect, render_template, send_file
from flask_limiter import Limiter
from flask_sqlalchemy import SQLAlchemy
import sqlite3, requests, sys, os, time, json, multiprocessing, datetime, xmltodict, pickle, secrets

from sqlalchemy import create_engine, select, update, insert, delete
from sqlalchemy.orm import Session

from database import start_db_time, Friend, DiscordFriends, Discord, Config

sys.path.append('../')
from api import *
from api.love2 import *
from api.private import CLIENT_ID, CLIENT_SECRET, HOST
from api.public import pretendoBotFC, nintendoBotFC
from api.networks import NetworkType, nameToNetworkType

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.abspath('sqlite/fcLibrary.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
#db1 = SQLAlchemy(app)

engine = create_engine('sqlite:///' + os.path.abspath('sqlite/fcLibrary.db'))

limiter = Limiter(app, key_func = lambda : request.access_route[-1])

API_ENDPOINT:str = 'https://discord.com/api/v10'

local = False
port = 2277
version = 0.31
agent = '3DS-RPC/'

startTime = time.time() # Frontend
start_db_time(0, NetworkType.NINTENDO)
start_db_time(0, NetworkType.PRETENDO)
startTime2Nintendo = 0 # Nintendo Backend
startTime2Pretendo = 0 # Pretendo Backend

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
cdnLimit = '60/minute'
togglerLimit = '5/minute'

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
def createUser(friendCode:int, network:NetworkType, addNewInstance:bool = False):
    if int(friendCode) == int(pretendoBotFC):
        raise Exception('invalid FC')
    if int(friendCode) == int(nintendoBotFC):
        raise Exception('invalid FC')
    try:
        convertFriendCodeToPrincipalId(friendCode)
        if not addNewInstance:
            raise Exception('UNIQUE constraint failed: friends.friendCode')
        with Session(engine) as session:
            session.add(Friend(
                friend_code=str(friendCode).zfill(12),
                network=network,
                online=False,
                title_id='0',
                upd_id='0',
                last_accessed=time.time() + 300,
                account_creation=time.time(),
                last_online=time.time(),
                favorite_game=0
            ))
            session.commit()
    except Exception as e:
        if 'UNIQUE constraint failed: friends.friendCode' in str(e): # TODO: Make this check work with ORM & combined network friendslists
            with Session(engine) as session:
                stmt = (
                    select(Friend)
                    .where(Friend.friend_code == str(friendCode).zfill(12))
                    .where(Friend.network == network)
                    )
                friend = session.scalar(stmt)
                friend.last_accessed = time.time()
                session.commit()

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
    with Session(engine) as session:
        stmt = select(Discord).where(Discord.id == ID)
        result = session.scalar(stmt)
    return result.token

def userFromToken(token:str):
    with Session(engine) as session:
        stmt = select(Discord).where(Discord.token == token)
        result = session.scalar(stmt)
    if not result:
        raise Exception('invalid token!')
    return result

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
        with Session(engine) as session:
            session.add(Discord(
                id=user['id'],
                refresh=response['refresh_token'],
                bearer=response['access_token'],
                session='',
                token=token,
                last_accessed=0,
                generation_date=time.time()
            ))
            session.commit()
    except Exception as e:
        if 'UNIQUE constraint failed' in str(e): # TODO: Fix this constraint check to whatever ORM accepts
            old_token = tokenFromID(user['id'])

            discord_user = userFromToken(old_token)
            discord_user.refresh = response['refresh_token']
            discord_user.bearer = response['access_token']
            discord_user.generation_date = time.time()
            discord_user.token = token

            session.commit()
    return token, user['username'], ('https://cdn.discordapp.com/avatars/%s/%s.%s' % (user['id'], user['avatar'], 'gif' if user['avatar'].startswith('a_') else 'png') if user['avatar'] else '')

def deleteDiscordUser(ID:int):
    with Session(engine) as session:
        session.delete(session.get(Discord, ID))
        session.delete(session.get(DiscordFriends, ID))
        session.commit()

def getConnectedConsoles(ID:int):
    session = Session(engine)

    stmt = select(DiscordFriends).where(DiscordFriends.id == ID)
    result = session.scalars(stmt).all()
    
    return [ (result.friend_code, result.active, result.network) for result in result ]

def sidenav():
    session = Session(engine)
    startTimeNintendo = session.get(Config, NetworkType.NINTENDO).backend_uptime
    startTimePretendo = session.get(Config, NetworkType.PRETENDO).backend_uptime

    status = 'Offline'
    if startTimeNintendo != 0 and startTimePretendo != 0:
        status = 'Operational'
    elif (startTimeNintendo != 0 and startTimePretendo == 0) or (startTimeNintendo == 0 and startTimePretendo != 0):
        status = 'Semi-Operational'

    data = {
        'uptime': str(datetime.timedelta(seconds= int(time.time() - startTime))),
        'nintendo-uptime-backend': ('Nintendo Backend has been up for %s...' % str(datetime.timedelta(seconds= int(time.time() - int(startTimeNintendo)))) if not startTimeNintendo == 0 else 'Nintendo Backend: Offline'),          
        'pretendo-uptime-backend': ('Pretendo Backend has been up for %s...' % str(datetime.timedelta(seconds= int(time.time() - int(startTimePretendo)))) if not startTimePretendo == 0 else 'Pretendo Backend: Offline'),
        'status': status,
    }
    return data

def userAgentCheck():
    userAgent = request.headers['User-Agent']
    try:
        if float(userAgent.replace(agent, '')) != version:
            raise Exception('client is not v%s' % version)
    except:
        raise Exception('this client is invalid')

def getPresence(friendCode:int, network:NetworkType, *, createAccount:bool = True, ignoreUserAgent = False, ignoreBackend = False):
    try:
        if not ignoreUserAgent:
            userAgentCheck()

        session = Session(engine)

        startTime = session.get(Config, network).backend_uptime
        if startTime == 0 and not ignoreBackend and not disableBackendWarnings:
            raise Exception('Backend currently offline. please try again later')
        
        friendCode = str(friendCode).zfill(12)
        if createAccount:
            createUser(friendCode, network, False)
        principalId = convertFriendCodeToPrincipalId(friendCode)

        stmt = (
            select(Friend)
            .where(Friend.friend_code == friendCode)
            .where(Friend.network == network)
            )
        result = session.scalar(stmt)

        if not result:
            raise Exception('friendCode not recognized\nHint: You may not have added the bot as a friend')
        if result.online:
            presence = {
                'titleID': result.title_id,
                'updateID': result.upd_id,
                'joinable': result.joinable,
                'gameDescription': result.game_description,
                'game': getTitle(result.title_id, titlesToUID, titleDatabase),
                'disclaimer': 'all information regarding the title (User/Presence/game) is downloaded from Nintendo APIs',
            }
        else:
            presence = {}
        mii = result.mii
        if mii:
            mii = MiiData().mii_studio_url(mii)
        return {
            'Exception': False,
            'User': {
                'principalId': principalId,
                'friendCode': str(convertPrincipalIdtoFriendCode(principalId)).zfill(12),
                'online': result.online,
                'Presence': presence,
                'username': result.username,
                'message': result.message,
                'mii': mii,
                'accountCreation': result.account_creation,
                'lastAccessed': result.last_accessed,
                'lastOnline': result.last_online,
                'favoriteGame': result.favorite_game,
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
    session = Session(engine)

    stmt = (
        select(Friend)
        .where(Friend.online == True)
        .where(Friend.username != None)
        .order_by(Friend.last_accessed.desc())
        )
    results = session.scalars(stmt).all()
    num = len(results)
    data = sidenav()
    data['active'] = [ ({
        'mii':MiiData().mii_studio_url(user.mii),
        'username':user.username,
        'game': getTitle(user.title_id, titlesToUID, titleDatabase),
        'friendCode': user.friend_code.zfill(12),
        'joinable': user.joinable,
        'network': user.network.lower_name(),
    }) for user in results if user.username ]
    data['active'] = data['active'][:2]

    stmt = (
        select(Friend)
        .where(Friend.username != None)
        .order_by(Friend.account_creation.desc())
        .limit(6)
        )
    results = session.scalars(stmt).all()

    data['new'] = [ ({
        'mii':MiiData().mii_studio_url(user.mii),
        'username': user.username,
        'game': getTitle(user.title_id, titlesToUID, titleDatabase) if user.online and user.title_id != 0 else '',
        'friendCode': user.friend_code.zfill(12),
        'joinable': user.joinable,
        'network': user.network.lower_name(),
    }) for user in results if user.username ]
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
@app.route('/settings')
def settings():
    if not request.cookies.get('token'):
        return redirect('/connect')
    data = {
        'consoles': [],
    }
    data = sidenav()
    try:
        session = Session(engine)

        stmt = select(Discord).where(Discord.token == request.cookies['token'])
        result = session.scalar(stmt)
    except Exception as e:
        if 'invalid token' in str(e):
            response = make_response(redirect('/'))
            response.set_cookie('token', '', expires = 0)
            response.set_cookie('user', '', expires = 0)
            response.set_cookie('pfp', '', expires = 0)
            return response
        return redirect('/')

    data['profileButton'] = result.show_profile_button
    data['smallImage'] = result.show_small_image

    response = make_response(render_template('dist/settings.html', data = data))
    return response

@app.route('/settings.html')
def settingsRedirect():
    return redirect('/settings')

# Roster page
@app.route('/roster')
def roster():
    session = Session(engine)

    stmt = (
        select(Friend)
        .where(Friend.username)
        .order_by(Friend.account_creation.desc())
        .limit(8)
    )
    results = session.scalars(stmt).all()

    data = sidenav()

    data['title'] = 'New Users'
    data['users'] = [ ({
        'mii':MiiData().mii_studio_url(user.mii),
        'username':user.username,
        'game': getTitle(user.title_id, titlesToUID, titleDatabase),
        'friendCode': user.friend_code.zfill(12),
        'joinable': user.joinable,
        'network': user.network.lower_name(),
    }) for user in results if user.username ]

    response = make_response(render_template('dist/users.html', data = data))
    return response

# Active page
@app.route('/active')
def active():
    session = Session(engine)

    stmt = (
        select(Friend)
        .where(Friend.username)
        .where(Friend.online)
        .order_by(Friend.account_creation.desc())
    )
    results = session.scalars(stmt).all()

    data = sidenav()
    data['title'] = 'Active Users'

    data['users'] = [ ({
        'mii':MiiData().mii_studio_url(user.mii),
        'username':user.username,
        'game': getTitle(user.title_id, titlesToUID, titleDatabase),
        'friendCode': user.friend_code.zfill(12),
        'joinable': user.joinable,
        'network': user.network.lower_name(),
    }) for user in results if user[6] ]

    response = make_response(render_template('dist/users.html', data = data))
    return response

# Register page
@app.route('/register.html')
def register():
    
    network = request.args.get('network')
    if network is None:
        return make_response(render_template('dist/registerselectnetwork.html'))

    try:
        network = NetworkType[network.upper()]
        response = make_response(render_template('dist/register.html', data = {
            'botFC': '-'.join(network.friend_code()[i:i+4] for i in range(0, len(network.friend_code()), 4)),
            'network': network
        }))
        return response
    except:
        return make_response(render_template('dist/registerselectnetwork.html'))

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
        'network': request.args.get('network')
    }
    return render_template('dist/success.html', data = data)

# Consoles page
@app.route('/consoles')
def consoles():
    if not request.cookies.get('token'):
        return redirect('/connect')
    data = {
        'consoles': [],
    }
    try:
        id = userFromToken(request.cookies['token']).id
    except Exception as e:
        if 'invalid token' in str(e):
            response = make_response(redirect('/'))
            response.set_cookie('token', '', expires = 0)
            response.set_cookie('user', '', expires = 0)
            response.set_cookie('pfp', '', expires = 0)
            return response
        return redirect('/')
    session = Session(engine)
    for console, active, network_type in getConnectedConsoles(id):
        network = NetworkType(network_type)
        stmt = (
            select(Friend)
            .where(Friend.friend_code == console)
            .where(Friend.network == network)
        )
        result = session.scalar(stmt)
        data['consoles'].append({
            'fc': '-'.join(console[i:i+4] for i in range(0, 12, 4)),
            'username': result.username,
            'active': active,
            'network': network.lower_name()
        })
    data.update(sidenav())
    response = render_template('dist/consoles.html', data = data)
    return response

@app.route('/user/<string:friendCode>/')
def userPage(friendCode:str):
    network: NetworkType

    try:
        network = nameToNetworkType(request.args.get('network'))

        userData = getPresence(int(friendCode.replace('-', '')), network, createAccount= False, ignoreUserAgent = True, ignoreBackend = True)
        if userData['Exception'] or not userData['User']['username']:
            raise Exception(userData['Exception'])
    except:
        return render_template('dist/404.html')

    if not userData['User']['online'] or not userData['User']['Presence']:
        userData['User']['Presence']['game'] = None
    userData['User']['favoriteGame'] = getTitle(userData['User']['favoriteGame'], titlesToUID, titleDatabase)
    userData['User']['network'] = network.lower_name()
    if userData['User']['favoriteGame']['name'] == 'Home Screen':
        userData['User']['favoriteGame'] = None
    for i in ('accountCreation','lastAccessed','lastOnline'):
        if userData['User'][i] == 0:
            userData['User'][i] = 'Never'
        elif time.time() - userData['User'][i] > 86400:
            userData['User'][i] = datetime.datetime.fromtimestamp(userData['User'][i]).strftime('%b %d, %Y')
        elif time.time() - userData['User'][i] > 600:
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
def newUser(friendCode:int, network:int=-1, userCheck:bool = True):
    try:
        if userCheck:
            userAgentCheck()
        if network == -1:
            network = NetworkType.NINTENDO

            request_arg = request.data.decode('utf-8').split(',')[0]
            if request_arg.isnumeric():
                network = NetworkType(request_arg.upper())
        createUser(friendCode, network, True)
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
def userPresence(friendCode:int, network:str="nintendo", *, createAccount:bool = True, ignoreUserAgent = False, ignoreBackend = False):
    return getPresence(friendCode, nameToNetworkType(network), createAccount=createAccount, ignoreUserAgent = ignoreUserAgent, ignoreBackend = ignoreBackend)

# Alias
@app.route('/api/u/<int:friendCode>/', methods=['GET'])
@limiter.limit(userPresenceLimit)
def userAlias(friendCode:int):
    network = 0
    if request.args.get('network') != None:
        network = nameToNetworkType(request.args.get('network'))
    return userPresence(friendCode, network)

# Alias
@app.route('/api/u/c/<int:friendCode>/', methods=['POST'])
@limiter.limit(newUserLimit)
def newAlias1(friendCode:int):
    network = NetworkType.NINTENDO
    if (request.data.decode('utf-8').split(','))[0] != None:
        network = nameToNetworkType((request.data.decode('utf-8').split(','))[0])
    return newUser(friendCode, network)

# Alias
@app.route('/api/user/c/<int:friendCode>/', methods=['POST'])
@limiter.limit(newUserLimit)
def newAlias2(friendCode:int):
    network = NetworkType.NINTENDO
    if (request.data.decode('utf-8').split(','))[0] != None:
        network = nameToNetworkType((request.data.decode('utf-8').split(','))[0])
    return newUser(friendCode, network)

# Alias
@app.route('/api/u/create/<int:friendCode>/', methods=['POST'])
@limiter.limit(newUserLimit)
def newAlias3(friendCode:int):
    network = NetworkType.NINTENDO
    if (request.data.decode('utf-8').split(','))[0] != None:
        network = nameToNetworkType((request.data.decode('utf-8').split(','))[0])
    return newUser(friendCode, network)

# Toggle
@app.route('/api/toggle/<int:friendCode>/', methods=['POST'])
@limiter.limit(togglerLimit)
def toggler(friendCode:int):
    network = NetworkType.NINTENDO
    if request.data.decode('utf-8').split(',')[2] != None:
        network = nameToNetworkType(request.data.decode('utf-8').split(',')[2])
    try:
        fc = str(convertPrincipalIdtoFriendCode(convertFriendCodeToPrincipalId(friendCode))).zfill(12)
    except:
        return 'failure!\nthat is not a real friendCode!'
    session = Session(engine)
    stmt = (
        select(Friend)
        .where(Friend.friend_code == fc)
        .where(Friend.network == network)
    )
    result = session.scalar(stmt)
    if not result:
        return 'failure!\nthat is not an existing friendCode!'
    
    f = request.data.decode('utf-8').split(',')
    token = f[0]
    active = bool(int(f[1]))
    id = userFromToken(token).id
    stmt = (
        select(DiscordFriends)
        .where(DiscordFriends.id == id)
        .where(DiscordFriends.friend_code == fc)
        .where(DiscordFriends.network == network)
    )
    result = session.scalar(stmt)

    if not result:
        stmt = select(DiscordFriends).where(DiscordFriends.id == id)
        allFriends = session.scalars(stmt).all()
        if len(allFriends) >= 10:
            return 'failure!\nyou can\'t have more than ten consoles added at one time!'
        
    if active:
        session.execute(
            update(DiscordFriends)
            .where(DiscordFriends.active)
            .where(DiscordFriends.id == id)
            .values(active = False)
        )
    if result:
        session.execute(
            update(DiscordFriends)
            .where(DiscordFriends.friend_code == fc)
            .where(DiscordFriends.network == network)
            .where(DiscordFriends.id == id)
            .values(active=active)
        )
    else:
        session.execute(
            insert(DiscordFriends)
            .values(id=id, friend_code=fc, active=active, network=network)
        )
    session.commit()
    return 'success!'

# Delete
@app.route('/api/delete/<int:friendCode>/', methods=['POST'])
@limiter.limit(togglerLimit)
def deleter(friendCode:int):
    session = Session(engine)
    fc = str(convertPrincipalIdtoFriendCode(convertFriendCodeToPrincipalId(friendCode))).zfill(12)
    if not ',' in request.data.decode('utf-8'): # Old API compatiblity. In the future this should be depercated.
        token = request.data.decode('utf-8')
        id = userFromToken(token).id
        
        session.execute(
            delete(DiscordFriends)
            .where(DiscordFriends.friend_code == fc)
            .where(DiscordFriends.network == NetworkType.NINTENDO)
            .where(DiscordFriends.id == id)
        )
        session.commit()

        return 'success!'

    data = request.data.decode('utf-8').split(',')
    token = data[0]
    network = nameToNetworkType(data[1])
    id = userFromToken(token).id

    session.execute(
            delete(DiscordFriends)
            .where(DiscordFriends.friend_code == fc)
            .where(DiscordFriends.network == network)
            .where(DiscordFriends.id == id)
        )
    # the following is optional, this deletes the friend data if you remove the console, and no one else is using the fc.
    result = session.scalar(
        select(DiscordFriends)
        .where(DiscordFriends.friend_code == fc)
        .where(DiscordFriends.network == network)
    )
    if result == None:
        session.execute(
            delete(Friend)
            .where(Friend.friend_code == fc)
            .where(Friend.network == network)
        )
    # end of optional
    session.commit()
    return 'success!'

# Toggle one
@app.route('/api/settings/<string:which>/', methods=['POST'])
@limiter.limit(togglerLimit)
def settingsToggler(which:str):
    toggle = bool(int(request.data.decode('utf-8')))
    if not which in ('smallImage', 'profileButton'):
        return 'failure!'
    if which == 'smallImage':
        which = 'show_small_image'
    else:
        which = 'show_profile_button'
    try:
        session = Session(engine)
        
        session.execute(
            update(Discord)
            .where(Discord.token == request.cookies['token'])
            .values({getattr(Discord, which): toggle})
        )

        session.commit() 
    except:
        return 'failure!'
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
        if request.form['network'] is None:
            network = NetworkType.NINTENDO
        else:
            network = NetworkType(int(request.form['network']))
        newUser(fc, network, False)
    except:
        return redirect('/failure.html')
    return redirect(f'/success.html?fc={fc}&network={network.lower_name()}')

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
            deleteDiscordUser(userFromToken(request.cookies['token']).id)
    return redirect('/404.html')

if __name__ == '__main__':
    cacheTitles()
    if local:
        app.run(host = '0.0.0.0', port = port)
    else:
        import gevent.pywsgi
        server = gevent.pywsgi.WSGIServer(('0.0.0.0', port), app)
        server.serve_forever()
