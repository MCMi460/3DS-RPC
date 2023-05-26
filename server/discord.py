import time, sqlite3, sys, secrets, requests, json, pickle
sys.path.append('../')
from api import *
from api.love2 import *
from api.private import CLIENT_ID, CLIENT_SECRET, HOST

API_ENDPOINT:str = 'https://discord.com/api/v10'

with open('./cache/databases.dat', 'rb') as file:
	t = pickle.loads(file.read())
	titleDatabase = t[0]
	titlesToUID = t[1]

class Session():
	def __init__(self, con, cursor):
		self.con = con
		self.cursor = cursor

	def retire(self, refresh):
		self.cursor.execute('UPDATE discord SET session = ? WHERE refresh = ?', ('', refresh))
		self.con.commit()

	def create(self, refresh, session):
		self.cursor.execute('UPDATE discord SET session = ? WHERE refresh = ?', (session, refresh))
		self.con.commit()
		return session

	def update(self, session):
		self.cursor.execute('UPDATE discord SET lastAccessed = ? WHERE session = ?', (time.time(), session))
		self.con.commit()

class Discord():
	def __init__(self, con, cursor):
		self.con = con
		self.cursor = cursor

	def updatePresence(self, bearer, refresh, session, lastAccessed, generationDate, userData):
		if time.time() - lastAccessed >= 1000:
			session = Session(self.con, self.cursor).retire(refresh)
		elif time.time() - lastAccessed <= 15:
			print('[MANUAL RATE LIMITED]')
			return
		data = {
			'activities': [
				{
					'type': 0,
					'application_id': CLIENT_ID,
					'assets': {
					},
					'platform': 'desktop',
				},
			],
		}
		presence = userData['User']['Presence']
		if presence:
			game = presence['game']
			data['activities'][0]['name'] = game['name'] + ' (3DS)'
			if game['icon_url']:
				data['activities'][0]['assets']['large_image'] = game['icon_url'].replace('/cdn/i/', HOST + '/cdn/i/')
				data['activities'][0]['assets']['large_text'] = game['name']
			if presence['gameDescription']:
				data['activities'][0]['details'] = presence['gameDescription']
			if userData['User']['username']:
				data['activities'][0]['buttons'] = [{'label': 'Profile', 'url': HOST + '/user/' + userData['User']['friendCode']},]
			if userData['User']['username'] and game['icon_url']:
				data['activities'][0]['assets']['small_image'] = userData['User']['mii']['face']
				data['activities'][0]['assets']['small_text'] = '-'.join(userData['User']['friendCode'][i:i+4] for i in range(0, 12, 4))
			if session:
				data['token'] = session
			headers = {
			    'Authorization': 'Bearer %s' % bearer,
				'Content-Type': 'application/json',
			}
			for key in list(data['activities'][0]):
				if isinstance(data['activities'][0][key], str) and not 'image' in key:
					if len(data['activities'][0][key]) > 128:
						data['activities'][0][key] = data['activities'][0][key][:128]
			r = requests.post('%s/users/@me/headless-sessions' % API_ENDPOINT, data = json.dumps(data), headers = headers)
			r.raise_for_status()
			Session(self.con, self.cursor).create(refresh, r.json()['token'])
			Session(self.con, self.cursor).update(r.json()['token'])

	def resetPresence(self, bearer, refresh, session, lastAccessed, generationDate):
		if not session:
			print('[NO SESSION TO RESET]')
			return
		elif time.time() - lastAccessed <= 30:
			print('[MANUAL RATE LIMITED]')
			return
		Session(self.con, self.cursor).update(session)
		headers = {
		    'Authorization': 'Bearer %s' % bearer,
			'Content-Type': 'application/json',
		}
		data = {
			'token': session,
		}
		r = requests.post('%s/users/@me/headless-sessions/delete' % API_ENDPOINT, data = json.dumps(data), headers = headers)
		r.raise_for_status()
		Session(self.con, self.cursor).create(refresh, '') # Reset session

	def refreshBearer(self, refresh:str, access:str, generationDate:int, ID:int):
		if time.time() - generationDate < 604800 - 1800: # 30 minutes before the token expires
			return False
		print('[REFRESH BEARER %s]' % ID)
		data = {
			'client_id': '%s' % CLIENT_ID,
			'client_secret': '%s' % CLIENT_SECRET,
			'grant_type': 'refresh_token',
			'refresh_token': refresh,
		}
		headers = {
			'Content-Type': 'application/x-www-form-urlencoded',
		}
		r = requests.post('%s/oauth2/token' % API_ENDPOINT, data = data, headers = headers)
		r.raise_for_status()
		response = r.json()
		self.cursor = con.cursor()
		self.cursor.execute('UPDATE discord SET refresh = ?, bearer = ?, generationDate = ? WHERE refresh = ?', (response['refresh_token'], response['access_token'], time.time(), refresh))
		self.con.commit()
		return True

	def deleteDiscordUser(self, ID:int):
		print('[DELETING %s]' % ID)
		self.cursor.execute('DELETE FROM discord WHERE ID = ?', (ID,))
		self.cursor.execute('DELETE FROM discordFriends WHERE ID = ?', (ID,))
		self.con.commit()

	def deactivateDiscordUser(self, ID:int):
		print('[DEACTIVATING %s]' % ID)
		self.cursor.execute('DELETE FROM discord WHERE ID = ?', (ID,))
		self.cursor.execute('DELETE FROM discordFriends WHERE ID = ?', (ID,))
		self.con.commit()

delay = 2

while True:
	time.sleep(delay)

	with sqlite3.connect('sqlite/fcLibrary.db') as con:
		cursor = con.cursor()

		discord = Discord(con, cursor)

		cursor.execute('SELECT * FROM discord')
		group = cursor.fetchall()
		for dn in group:
			try:
				if discord.refreshBearer(dn[1], dn[2], dn[6], dn[0]):
					time.sleep(delay * 2)
			except:
				#discord.deleteDiscordUser(dn[0])
				discord.deactivateDiscordUser(dn[0])

		wait = time.time()

		while time.time() - wait <= 1200:

			cursor.execute('SELECT * FROM discordFriends WHERE active = ?', (True,))
			v = cursor.fetchall()
			print('[BATCH OF %s USERS]' % len(v))
			if len(v) < 1:
				time.sleep(delay)
				continue
			for r in v:
				print('[RUNNING %s - %s]' % (r[0], r[1]))
				cursor.execute('SELECT * FROM friends WHERE friendCode = ?', (r[1],))
				v2 = cursor.fetchone()
				cursor.execute('SELECT * FROM discord WHERE ID = ?', (r[0],))
				v3 = cursor.fetchone()
				if time.time() - v3[5] >= 60:
					print(v2[0])
					principalId = convertFriendCodeToPrincipalId(v2[0])
					if not v2[1]:
						try:
							print('[RESETTING %s]' % v2[0])
							discord.resetPresence(v3[2], v3[1], v3[3], v3[5], v3[6])
						except:
							discord.deleteDiscordUser(v3[0])
					else:
						presence = {
							'gameDescription': v2[10],
							'game': getTitle(v2[2], titlesToUID, titleDatabase),
						}
						mii = v2[8]
						if mii:
							mii = MiiData().mii_studio_url(mii)
						print('[UPDATING %s]' % v2[0])
						try:
							discord.updatePresence(v3[2], v3[1], v3[3], v3[5], v3[6], {
								'User': {
									'friendCode': str(convertPrincipalIdtoFriendCode(principalId)).zfill(12),
									'online': bool(v2[1]),
									'Presence': presence,
									'username': v2[6],
									'mii': mii,
									'lastAccessed': v2[4],
								}
							})
						except:
							discord.deleteDiscordUser(v3[0])
				else:
					print('[WAIT]')
				time.sleep(delay)
