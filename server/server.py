# Created by Deltaion Lee (MCMi460) on Github

from flask import Flask, make_response, request, redirect, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
import sqlite3, requests, sys, os, time, json
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

@app.errorhandler(429)
def ratelimit_handler(e):
    return 'You have exceeded your rate-limit'

# Create entry in database with friendCode
def createUser(friendCode:int):
    try:
        convertFriendCodeToPrincipalId(friendCode)
        db.session.execute('INSERT INTO friends (friendCode, online, titleID, updID, lastAccessed) VALUES (\'%s\', %s, %s, %s, %s)' % (str(friendCode).zfill(12), False, '0', '0', time.time() + 300))
        db.session.commit()
    except Exception as e:
        if 'UNIQUE constraint failed: friends.friendCode' in str(e):
            db.session.execute('UPDATE friends SET lastAccessed = %s WHERE friendCode = \'%s\'' % (time.time(), friendCode))
            db.session.commit()

def sendNotification(notification:dict, friendCode:int):
    result = db.session.execute('SELECT notifications FROM friends WHERE friendCode = \'%s\'' % friendCode)
    result = result.fetchone()
    if result[0]:
        result = result[0] + '|'
    else:
        result = ''
    result = result + json.dumps(notification)
    db.session.execute('UPDATE friends SET notifications = \'%s\' WHERE friendCode = \'%s\'' % (result, friendCode))
    db.session.commit()

def clearNotifications(friendCode:int):
    db.session.execute('UPDATE friends SET notifications = NULL WHERE friendCode = \'%s\'' % friendCode)
    db.session.commit()

def checkUser(friendCode:int):
    result = db.session.execute('SELECT * FROM friends WHERE friendCode = \'%s\'' % friendCode)
    result = result.fetchone()
    if not result:
        return False
    return True

# Index page
@app.route('/')
def index():
    fc = request.cookies.get('friendCode')
    data = {
        'registered': '|Not logged in',
    }
    if fc:
        result = db.session.execute('SELECT * FROM friends WHERE friendCode = \'%s\'' % fc)
        result = result.fetchone()
        data['registered'] = (('Logged in as|%s' % (result[6] if result[6] else 'Loading...')) if result != None else '|Not logged in')
    response = make_response(render_template('dist/index.html', data = data))
    if fc and not result:
        response.set_cookie('friendCode', '')
    return response

# Index page
@app.route('/index.html')
def index2():
    return index()

# Settings page
@app.route('/settings.html')
def settings():
    fc = request.cookies.get('friendCode')
    data = {
        'registered': '|Not logged in',
    }
    if fc:
        result = db.session.execute('SELECT * FROM friends WHERE friendCode = \'%s\'' % fc)
        result = result.fetchone()
        data['registered'] = (('Logged in as|%s' % (result[6] if result[6] else 'Loading...')) if result != None else '|Not logged in')
    else:
        return redirect('/login.html')
    if fc and not result:
        response = make_response(redirect('/login.html'))
        response.set_cookie('friendCode', '')
        return response
    response = make_response(render_template('dist/settings.html', data = data))
    return response

# Login page
@app.route('/login.html')
def loginPage():
    fc = request.cookies.get('friendCode')
    response = make_response(render_template('dist/login.html'))
    if fc and not checkUser(fc):
        response.set_cookie('friendCode', '')
    return response

# Register page
@app.route('/register.html')
def register():
    fc = request.cookies.get('friendCode')
    response = make_response(render_template('dist/register.html'))
    if fc and not checkUser(fc):
        response.set_cookie('friendCode', '')
    return response

# Activity page
@app.route('/activity.html')
def activity():
    fc = request.cookies.get('friendCode')
    data = {
        'registered': '|Not logged in',
    }
    if fc:
        result = db.session.execute('SELECT * FROM friends WHERE friendCode = \'%s\'' % fc)
        result = result.fetchone()
        data['registered'] = (('Logged in as|%s' % (result[6] if result[6] else 'Loading...')) if result != None else '|Not logged in')
    else:
        return redirect('/login.html')
    if fc and not result:
        response = make_response(redirect('/login.html'))
        response.set_cookie('friendCode', '')
        return response
    response = make_response(render_template('dist/activity.html', data = data))
    return response

# Invalid page
@app.route('/invalid.html')
def invalid():
    return render_template('dist/invalid.html')

# Grab presence from friendCode
@app.route('/user/<int:friendCode>/', methods=['GET'])
@limiter.limit('3/minute')
def userPresence(friendCode:int):
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
@app.route('/f/<int:friendCode>', methods=['GET'])
@limiter.limit('2/minute')
def addFriend(friendCode:int):
    fc = request.cookies.get('friendCode')
    if not fc:
        response = make_response(redirect('/login.html'))
        response.headers['redirectFrom'] = friendCode
        return response
    try:
        convertFriendCodeToPrincipalId(fc)
    except:
        return redirect('/invalid.html')
    sendNotification({
        'sender': fc,
    }, friendCode)
    return 'Successfully sent friend request from %s to %s' % (fc, friendCode)

# Login
@app.route('/login', methods=['POST'])
@limiter.limit('2/minute')
def login():
    try:
        fc = request.form['fc']
    except:
        return 'wat'
    try:
        convertFriendCodeToPrincipalId(fc)
        createUser(fc)
        response = make_response(redirect('/'))
        response.set_cookie('friendCode', fc)
        return response
    except:
        return redirect('/invalid.html')

# Logout
@app.route('/logout')
def logout():
    response = make_response(redirect('/'))
    response.set_cookie('friendCode', '')
    return response

if __name__ == '__main__':
    if local:
        app.run(host = '0.0.0.0', port = port)
    else:
        import gevent.pywsgi
        server = gevent.pywsgi.WSGIServer(('0.0.0.0', port), app)
        server.serve_forever()
