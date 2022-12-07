# Created by Deltaion Lee (MCMi460) on Github

from flask import Flask, make_response, request, redirect, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
import sqlite3, requests, sys, os, time, json, random, string, hashlib, secrets, urllib
sys.path.append('../')
from api import *

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.abspath('sqlite/fcLibrary.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
limiter = Limiter(app, key_func = get_remote_address)

local = False
port = 2277
version = 0.2
agent = '3DS-RPC/'

notificationTypes = (
    'friendRequest',
    'friendRequestResponse',
    'gameInvite',
    'gameInviteResponse',
)

@app.errorhandler(429)
def ratelimit_handler(e):
    return 'You have exceeded your rate-limit. Please wait a bit before trying that again.'

# Create entry in database with friendCode
def createUser(friendCode:int):
    if int(friendCode) == int(botFC):
        raise Exception('invalid FC')
    try:
        convertFriendCodeToPrincipalId(friendCode)
        db.session.execute('INSERT INTO friends (friendCode, online, titleID, updID, lastAccessed) VALUES (\'%s\', %s, %s, %s, %s)' % (str(friendCode).zfill(12), False, '0', '0', time.time() + 300))
        db.session.commit()
    except Exception as e:
        if 'UNIQUE constraint failed: friends.friendCode' in str(e):
            db.session.execute('UPDATE friends SET lastAccessed = %s WHERE friendCode = \'%s\'' % (time.time(), str(friendCode).zfill(12)))
            db.session.commit()

def sendNotification(notification:dict, friendCode:int):
    result = db.session.execute('SELECT notifications FROM friends WHERE friendCode = \'%s\'' % str(friendCode).zfill(12))
    result = result.fetchone()
    if result[0]:
        result = ('' if not result[0] else result[0]) + '|'
        if json.dumps(notification) in result:
            return
    elif not result[0]:
        result = ''
    else:
        raise Exception()
    result = result + json.dumps(notification)
    db.session.execute('UPDATE friends SET notifications = \'%s\' WHERE friendCode = \'%s\'' % (result, str(friendCode).zfill(12)))
    db.session.commit()

def authentication(friendCode:int):
    createUser(friendCode)
    authString = ''.join(random.choice(string.ascii_letters) for i in range(16))
    try:
        convertFriendCodeToPrincipalId(friendCode)
        db.session.execute('INSERT INTO auth (friendCode, tempAuth) VALUES (\'%s\', \'%s\')' % (str(friendCode).zfill(12), authString))
        db.session.commit()
    except Exception as e:
        if 'UNIQUE constraint failed: auth.friendCode' in str(e):
            db.session.execute('UPDATE auth SET tempAuth = \'%s\' WHERE friendCode = \'%s\'' % (authString, str(friendCode).zfill(12)))
            db.session.commit()
    return authString

def checkAuthentication(friendCode:int, authString:str):
    createUser(friendCode)
    result = db.session.execute('SELECT tempAuth FROM auth WHERE friendCode = \'%s\'' % str(friendCode).zfill(12))
    result = result.fetchone()
    if not result or result[0] != authString:
        return False
    result2 = db.session.execute('SELECT message FROM friends WHERE friendCode = \'%s\'' % str(friendCode).zfill(12))
    result2 = result2.fetchone()
    if result[0] == result2[0] == authString:
        return True
    return False

def checkVerification(friendCode:int):
    result = db.session.execute('SELECT password FROM auth WHERE friendCode = \'%s\'' % str(friendCode).zfill(12))
    result = result.fetchone()
    if not result:
        return False
    if not result[0]:
        return False
    return True

def clearNotifications(friendCode:int):
    db.session.execute('UPDATE friends SET notifications = NULL WHERE friendCode = \'%s\'' % str(friendCode).zfill(12))
    db.session.commit()

def checkUser(friendCode:int):
    result = db.session.execute('SELECT * FROM friends WHERE friendCode = \'%s\'' % str(friendCode).zfill(12))
    result = result.fetchone()
    if not result:
        return False
    return True

def createAccount(friendCode:int, password:str):
    h = hashlib.md5(password.encode('utf-8')).hexdigest()
    key = secrets.token_urlsafe(64)
    db.session.execute('UPDATE auth SET password = \'%s\', token = \'%s\', tempAuth = NULL WHERE friendCode = \'%s\'' % (h, key,str(friendCode).zfill(12)))
    db.session.commit()
    return key

def updateToken(friendCode:int):
    key = secrets.token_urlsafe(64)
    db.session.execute('UPDATE auth SET token = \'%s\' WHERE friendCode = \'%s\'' % (key, str(friendCode).zfill(12)))
    db.session.commit()
    return key

def verifyAccount(friendCode:int, password:str):
    h = hashlib.md5(password.encode('utf-8')).hexdigest()
    result = db.session.execute('SELECT password FROM auth WHERE friendCode = \'%s\'' % str(friendCode).zfill(12))
    result = result.fetchone()
    if not result:
        return False
    if not result[0]:
        return False
    if result[0] == h:
        return updateToken(friendCode)
    return False

def getFCFromKey(key):
    result = db.session.execute('SELECT friendCode FROM auth WHERE token = \'%s\'' % str(key))
    try:
        return result.fetchone()[0]
    except:
        return None

# Index page
@app.route('/')
def index():
    key = request.cookies.get('token')
    data = {
        'registered': '|Not logged in',
    }
    if key:
        fc = getFCFromKey(key)
        if fc:
            result = db.session.execute('SELECT * FROM friends WHERE friendCode = \'%s\'' % fc)
            result = result.fetchone()
            data['registered'] = (('Logged in as|%s' % (result[6] if result[6] else 'Loading...')) if result != None else '|Not logged in')
        response = make_response(render_template('dist/index.html', data = data))
        if fc and not result:
            response.set_cookie('token', '')
    else:
        response = make_response(render_template('dist/index.html', data = data))
    return response

# Index page
@app.route('/index.html')
def index2():
    return index()

# Settings page
@app.route('/settings.html')
def settings():
    key = request.cookies.get('token')
    data = {
        'registered': '|Not logged in',
        'fc': 0,
    }
    if key:
        fc = getFCFromKey(key)
        if fc:
            result = db.session.execute('SELECT * FROM friends WHERE friendCode = \'%s\'' % fc)
            result = result.fetchone()
            data['registered'] = (('Logged in as|%s' % (result[6] if result[6] else 'Loading...')) if result != None else '|Not logged in')
            data['fc'] = '-'.join(str(fc)[i:i+4] for i in range(0, len(str(fc)), 4))
        else:
            return redirect('/login.html')
        if fc and not result:
            response = make_response(redirect('/login.html'))
            response.set_cookie('token', '')
            return response
        response = make_response(render_template('dist/settings.html', data = data))
    else:
        return redirect('/login.html')
    return response

# Login page
@app.route('/login.html')
def loginPage():
    key = request.cookies.get('token')
    if key and getFCFromKey(key):
        return redirect('/')
    redirectURL = request.args.get('redirectFrom')
    data = {}
    if redirectURL:
        data = {
            'redirectFrom': '?redirectFrom=' + urllib.parse.quote_plus(redirectURL),
        }
    return render_template('dist/login.html', data = data)

# Register page
@app.route('/register.html')
def registerPage():
    key = request.cookies.get('token')
    if key and getFCFromKey(key):
        return redirect('/settings.html')
    return render_template('dist/register.html')

# Auth page
@app.route('/auth.html', methods=['POST'])
@limiter.limit('2/minute')
def authPage():
    try:
        fc = request.form['fc']
        fc = str(convertPrincipalIdtoFriendCode(convertFriendCodeToPrincipalId(fc))).zfill(12)
        if checkVerification(fc):
            raise Exception()
    except:
        return redirect('/invalid.html')
    try:
        authString = authentication(fc)
        data = {
            'fc': fc,
            'authString': authString,
            'nextPage': '/password.html?fc=%s&authString=%s' % (fc, authString),
        }
        response = make_response(render_template('dist/auth.html', data = data))
    except:
        return redirect('/500.html')
    return response

# Auth page
@app.route('/password.html')
@limiter.limit('1/minute')
def passPage():
    try:
        fc = request.args['fc']
        fc = convertPrincipalIdtoFriendCode(convertFriendCodeToPrincipalId(fc))
        authString = request.args['authString']
    except:
        return redirect('/invalid.html')
    try:
        if not checkAuthentication(fc, authString):
            raise Exception()
        data = {
            'nextPage': '/register?authString=%s&fc=%s' % (authString, fc),
        }
        response = make_response(render_template('dist/password.html', data = data))
    except:
        return redirect('/invalid2.html')
    return response

# Activity page
@app.route('/activity.html')
def activity():
    key = request.cookies.get('token')
    data = {
        'registered': '|Not logged in',
    }
    if key:
        fc = getFCFromKey(key)
        if fc:
            result = db.session.execute('SELECT * FROM friends WHERE friendCode = \'%s\'' % fc)
            result = result.fetchone()
            data['registered'] = (('Logged in as|%s' % (result[6] if result[6] else 'Loading...')) if result != None else '|Not logged in')
        else:
            return redirect('/login.html')
    else:
        return redirect('/login.html')
    if fc and not result:
        response = make_response(redirect('/login.html'))
        response.set_cookie('token', '')
        return response
    response = make_response(render_template('dist/activity.html', data = data))
    return response

# Invalid page
@app.route('/invalid.html')
def invalid():
    return render_template('dist/invalid.html')

# Invalid2 page
@app.route('/invalid2.html')
def invalid2():
    return render_template('dist/invalid2.html')

# Invalid3 page
@app.route('/invalid3.html')
def invalid3():
    return render_template('dist/invalid3.html')

# Invalid4 page
@app.route('/invalid4.html')
def invalid4():
    return render_template('dist/invalid4.html')

# 500 page
@app.route('/500.html')
def fiveHundred():
    return render_template('dist/500.html')

# Terms page
@app.route('/terms.html')
def terms():
    return redirect('https://github.com/MCMi460/3DS-RPC/blob/main/TERMS.md')

# Grab presence from friendCode
@app.route('/user/<int:friendCode>/', methods=['GET'])
@limiter.limit('3/minute')
def userPresence(friendCode:int):
    friendCode = str(friendCode).zfill(12)
    createUser(friendCode)
    try:
        userAgent = request.headers['User-Agent']
        try:
            if float(userAgent.replace(agent, '')) < version:
                raise Exception('client is behind v%s' % version)
        except:
            raise Exception('this client is invalid')
        principalId = convertFriendCodeToPrincipalId(friendCode)
        result = db.session.execute('SELECT * FROM friends WHERE friendCode = \'%s\'' % friendCode)
        result = result.fetchone()
        if not result:
            raise Exception('friendCode not recognized\nHint: You may not have added the bot as a friend')
        if result[1] != 0:
            presence = {
                'titleID': result[2],
                'updateID': result[3],
            }
        else:
            presence = {}
        #if result[5]:
            #clearNotifications(friendCode)
        return {
            'Exception': False,
            'User': {
                'principalId': principalId,
                'friendCode': convertPrincipalIdtoFriendCode(principalId),
                'online': bool(result[1]),
                'Presence': presence,
                'notifications': result[5],
            }
        }
    except Exception as e:
        return {
            'Exception': {
                'Error': str(e),
            }
        }

# Make Nintendo's cert a 'secure' cert
@app.route('/cdn/i/<string:file>/', methods=['GET'])
@limiter.limit('5/minute')
def cdnImage(file:str):
    response = make_response(requests.get('https://kanzashi-ctr.cdn.nintendo.net/i/%s' % file, verify = False).content)
    response.headers['Content-Type'] = 'image/jpeg'
    return response

# Send friend request notification to user
@app.route('/f/<int:friendCode>/', methods=['GET'])
@limiter.limit('2/minute')
def addFriend(friendCode:int):
    key = request.cookies.get('token')
    if not key:
        response = make_response(redirect('/login.html' + '?redirectFrom=' + urllib.parse.quote_plus('f/' + str(friendCode))))
        return response
    try:
        fc = getFCFromKey(key)
        fc = str(convertPrincipalIdtoFriendCode(convertFriendCodeToPrincipalId(fc))).zfill(12)
        friendCode = str(convertPrincipalIdtoFriendCode(convertFriendCodeToPrincipalId(friendCode))).zfill(12)
    except:
        return redirect('/invalid.html')
    try:
        sendNotification({
            'sender': fc,
            'type': notificationTypes.index('friendRequest'),
        }, friendCode)
    except:
        return 'Failed'
    return 'Successfully sent friend request from %s to %s' % (fc, friendCode)

# Login
@app.route('/login', methods=['POST'])
@limiter.limit('2/minute')
def login():
    try:
        fc = request.form['fc']
        password = request.form['password']
    except:
        return 'wat'
    try:
        fc = convertPrincipalIdtoFriendCode(convertFriendCodeToPrincipalId(fc))
        createUser(fc)
    except:
        return redirect('/invalid.html')
    try:
        key = verifyAccount(fc, password)
        if not key:
            raise Exception()
        redirectURL = request.args.get('redirectFrom')
        url = '/'
        if redirectURL:
            url = url + redirectURL
        response = make_response(redirect(url))
        response.set_cookie('token', str(key))
        return response
    except:
        return redirect('/invalid4.html')

# Register
@app.route('/register', methods=['POST'])
@limiter.limit('1/minute')
def register():
    try:
        password = request.form['password']
        fc = request.args['fc']
        authString = request.args['authString']
        fc = convertPrincipalIdtoFriendCode(convertFriendCodeToPrincipalId(fc))
        if checkVerification(fc):
            return redirect('/invalid2.html')
        if len(password) < 5 or len(password) > 32 or not password.isalnum():
            return redirect('/invalid3.html')
        createAccount(fc, password)
    except:
        return 'Invalid registration'
    try:
        return redirect('/login.html')
    except:
        return redirect('/invalid.html')

# Logout
@app.route('/logout')
def logout():
    response = make_response(redirect('/'))
    response.set_cookie('token', '')
    return response

if __name__ == '__main__':
    if local:
        app.run(host = '0.0.0.0', port = port)
    else:
        import gevent.pywsgi
        server = gevent.pywsgi.WSGIServer(('0.0.0.0', port), app)
        server.serve_forever()
