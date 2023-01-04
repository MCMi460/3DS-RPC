# Created by Deltaion Lee (MCMi460) on Github

from flask import Flask, make_response, request, redirect, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
import sqlite3, requests, sys, os, time, json, multiprocessing, datetime
sys.path.append('../')
from api import *

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.abspath('sqlite/fcLibrary.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
limiter = Limiter(app, key_func = get_remote_address)

local = False
port = 2277
version = 0.3
agent = '3DS-RPC/'

startTime = time.time() # Frontend
startDBTime(0)
startTime2 = 0 # Backend

@app.errorhandler(429)
def ratelimit_handler(e):
    return 'You have exceeded your rate-limit. Please wait a bit before trying that again.'

@app.errorhandler(404)
def handler404(e):
    return render_template('dist/404.html')

# Create entry in database with friendCode
def createUser(friendCode:int, addNewInstance:bool = False):
    if int(friendCode) == int(botFC):
        raise Exception('invalid FC')
    try:
        convertFriendCodeToPrincipalId(friendCode)
        if not addNewInstance:
            raise Exception('UNIQUE constraint failed: friends.friendCode')
        db.session.execute('INSERT INTO friends (friendCode, online, titleID, updID, lastAccessed) VALUES (\'%s\', %s, %s, %s, %s)' % (str(friendCode).zfill(12), False, '0', '0', time.time() + 300))
        db.session.commit()
    except Exception as e:
        if 'UNIQUE constraint failed: friends.friendCode' in str(e):
            db.session.execute('UPDATE friends SET lastAccessed = %s WHERE friendCode = \'%s\'' % (time.time(), str(friendCode).zfill(12)))
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

# Index page
@app.route('/')
def index():
    response = make_response(render_template('dist/index.html', data = sidenav()))
    return response

# Index page
@app.route('/index.html')
def indexHTML():
    return index()

# Index page
@app.route('/settings.html')
def settings():
    response = make_response(render_template('dist/settings.html', data = sidenav()))
    return response

# Create entry in database with friendCode
@app.route('/api/user/create/<int:friendCode>/', methods=['POST'])
@limiter.limit('2/minute')
def newUser(friendCode:int):
    try:
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
@limiter.limit('3/minute')
def userPresence(friendCode:int):
    try:
        userAgent = request.headers['User-Agent']
        try:
            if float(userAgent.replace(agent, '')) != version:
                raise Exception('client is not v%s' % version)
        except:
            raise Exception('this client is invalid')
        result = db.session.execute('SELECT BACKEND_UPTIME FROM config')
        result = result.fetchone()
        startTime2 = result[0]
        if startTime2 == 0:
            raise Exception('backend currently offline. please try again later')
        friendCode = str(friendCode).zfill(12)
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
            }
        else:
            presence = {}
        return {
            'Exception': False,
            'User': {
                'principalId': principalId,
                'friendCode': str(convertPrincipalIdtoFriendCode(principalId)).zfill(12),
                'online': bool(result[1]),
                'Presence': presence,
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

if __name__ == '__main__':
    if local:
        app.run(host = '0.0.0.0', port = port)
    else:
        import gevent.pywsgi
        server = gevent.pywsgi.WSGIServer(('0.0.0.0', port), app)
        server.serve_forever()
