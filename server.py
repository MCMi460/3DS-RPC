from flask import Flask
import sqlite3
from api import *

app = Flask(__name__)

def accessDB():
    con = sqlite3.connect('sqlite/fcLibrary.db')
    cursor = con.cursor()
    return con, cursor

@app.route('/user/<int:friendCode>/', methods=['GET'])
def userPresence(friendCode:int):
    #cursor.execute('SELECT titleID FROM friends WHERE friendCode = %s' % friendCode)
    return "Hello World!"

@app.route('/user/c/<int:friendCode>/', methods=['POST'])
def createUser(friendCode:int) -> bool:
    con, cursor = accessDB()
    try:
        #cursor.execute('SELECT COUNT(1) FROM friends WHERE friendCode = %s' % friendCode)
        #if cursor.fetchone()[0] != 0:
            #raise Exception()
        cursor.execute('INSERT INTO friends (friendCode, online, titleID, updID) VALUES (%s, %s, %s, %s)' % (friendCode, False, '0', '0'))
        con.commit()
        return 'True'
    except:
        return 'False'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2277)
