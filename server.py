from flask import Flask, make_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sqlite3, requests
from api import *

app = Flask(__name__)
limiter = Limiter(app, key_func = get_remote_address)

@app.errorhandler(429)
def ratelimit_handler(e):
    return 'You have exceeded your rate-limit'

def accessDB():
    con = sqlite3.connect('sqlite/fcLibrary.db')
    cursor = con.cursor()
    return con, cursor

# Grab presence from friendCode
@app.route('/user/<int:friendCode>/', methods=['GET'])
@limiter.limit('3/minute')
def userPresence(friendCode:int):
    con, cursor = accessDB()
    try:
        principalId = convertFriendCodeToPrincipalId(friendCode)
        cursor.execute('SELECT * FROM friends WHERE friendCode = %s' % friendCode)
        result = cursor.fetchone()
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

# Create entry in database with friendCode
@app.route('/user/c/<int:friendCode>/', methods=['POST'])
@limiter.limit('2/minute')
def createUser(friendCode:int):
    con, cursor = accessDB()
    try:
        convertFriendCodeToPrincipalId(friendCode)
        cursor.execute('INSERT INTO friends (friendCode, online, titleID, updID) VALUES (%s, %s, %s, %s)' % (friendCode, False, '0', '0'))
        con.commit()
        return {
            'Exception': False,
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
    app.run(host = '0.0.0.0', port = 2277)
