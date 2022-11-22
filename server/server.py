# Created by Deltaion Lee (MCMi460) on Github

from flask import Flask, make_response, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
import sqlite3, requests, sys, os, time
import gevent.pywsgi
sys.path.append('../')
from api import *

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.abspath('sqlite/fcLibrary.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
limiter = Limiter(app, key_func = get_remote_address)

local = False
port = 2277
version = 0.1
agent = '3DS-RPC/'

@app.errorhandler(429)
def ratelimit_handler(e):
    return 'You have exceeded your rate-limit'

# Create entry in database with friendCode
def createUser(friendCode:int) -> dict:
    try:
        convertFriendCodeToPrincipalId(friendCode)
        db.session.execute('INSERT INTO friends (friendCode, online, titleID, updID, lastAccessed) VALUES (%s, %s, %s, %s, %s)' % (friendCode, False, '0', '0', time.time()))
        db.session.commit()
    except Exception as e:
        if 'UNIQUE constraint failed: friends.friendCode' in str(e):
            db.session.execute('UPDATE friends SET lastAccessed = %s WHERE friendCode = %s' % (time.time(), friendCode))
            db.session.commit()

# Grab presence from friendCode
@app.route('/user/<int:friendCode>/', methods=['GET'])
@limiter.limit('3/minute')
def userPresence(friendCode:int):
    createUser(friendCode)
    try:
        userAgent = request.headers['User-Agent']
        if float(userAgent.replace(agent, '')) < version:
            raise Exception('client is behind v%s' % version)
        principalId = convertFriendCodeToPrincipalId(friendCode)
        result = db.session.execute('SELECT * FROM friends WHERE friendCode = %s' % friendCode)
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
                'friendCode': convertPrincipalIdtoFriendCode(principalId),
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
        server = gevent.pywsgi.WSGIServer(('0.0.0.0', port), app)
        server.serve_forever()
