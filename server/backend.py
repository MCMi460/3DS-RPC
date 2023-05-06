# Created by Deltaion Lee (MCMi460) on Github
# Based from NintendoClients' `examples/3ds/friends.py`

from nintendo import nasc
from nintendo.nex import backend, friends, settings, streams
from nintendo.nex import common
import anyio, time, sqlite3, sys, traceback, secrets, requests, json, pickle
sys.path.append('../')
from api.private import SERIAL_NUMBER, MAC_ADDRESS, DEVICE_CERT, DEVICE_NAME, REGION, LANGUAGE, PID, PID_HMAC, NEX_PASSWORD, CLIENT_ID, CLIENT_SECRET, HOST
from api import *
from api.love2 import *

import logging
logging.basicConfig(level=logging.INFO)

delay = 2
since = 0
begun = time.time()
startDBTime(begun)

API_ENDPOINT:str = 'https://discord.com/api/v10'

with open('./cache/databases.dat', 'rb') as file:
	t = pickle.loads(file.read())
	titleDatabase = t[0]
	titlesToUID = t[1]

class Session:
	def retire(refresh):
		with sqlite3.connect('sqlite/fcLibrary.db') as con:
			cursor = con.cursor()
			cursor.execute('UPDATE discord SET session = ? WHERE refresh = ?', ('', refresh))
			con.commit()

	def create(refresh, session):
		with sqlite3.connect('sqlite/fcLibrary.db') as con:
			cursor = con.cursor()
			cursor.execute('UPDATE discord SET session = ? WHERE refresh = ?', (session, refresh))
			con.commit()
		return session

	def update(session):
		with sqlite3.connect('sqlite/fcLibrary.db') as con:
			cursor = con.cursor()
			cursor.execute('UPDATE discord SET lastAccessed = ? WHERE session = ?', (time.time(), session))
			con.commit()

def updatePresence(bearer, refresh, session, lastAccessed, generationDate, userData):
	if time.time() - lastAccessed >= 1000:
		session = Session.retire(refresh)
	elif time.time() - lastAccessed <= 30:
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
		Session.create(refresh, r.json()['token'])
		Session.update(r.json()['token'])

def resetPresence(bearer, refresh, session, lastAccessed, generationDate):
	if not session:
		return
	elif time.time() - lastAccessed <= 30:
		print('[MANUAL RATE LIMITED]')
		return
	Session.update(session)
	headers = {
	    'Authorization': 'Bearer %s' % bearer,
		'Content-Type': 'application/json',
	}
	data = {
		'token': session,
	}
	r = requests.post('%s/users/@me/headless-sessions/delete' % API_ENDPOINT, data = json.dumps(data), headers = headers)
	r.raise_for_status()
	Session.create(refresh, '') # Reset session

def refreshBearer(refresh:str, access:str, generationDate:int, ID:int):
	if time.time() - generationDate < 604800 - 300:
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
	with sqlite3.connect('sqlite/fcLibrary.db') as con:
		cursor = con.cursor()
		cursor.execute('UPDATE discord SET refresh = ?, bearer = ?, generationDate = ? WHERE refresh = ?', (response['refresh_token'], response['access_token'], time.time(), refresh))
		con.commit()
	return True

def deleteDiscordUser(ID:int):
	print('[DELETING %s]' % ID)
	with sqlite3.connect('sqlite/fcLibrary.db') as con:
		cursor = con.cursor()
		cursor.execute('DELETE FROM discord WHERE ID = ?', (ID,))
		cursor.execute('DELETE FROM discordFriends WHERE ID = ?', (ID,))
		con.commit()

async def main():
	while True:
		time.sleep(1)
		print('Grabbing new friends...')
		with sqlite3.connect('sqlite/fcLibrary.db') as con:
			cursor = con.cursor()

			cursor.execute('SELECT friendCode, lastAccessed FROM friends')
			result = cursor.fetchall()
			if not result:
				continue

			list_ = [ (convertFriendCodeToPrincipalId(f[0]), f[1]) for f in result ]
			lst = [ f[0] for f in list_ ]

			for i in range(0, len(lst), 100):
				rotation = lst[i:i+100]

				try:
					client = nasc.NASCClient()
					client.set_title(0x0004013000003202, 20)
					client.set_device(SERIAL_NUMBER, MAC_ADDRESS, DEVICE_CERT, DEVICE_NAME)
					client.set_locale(REGION, LANGUAGE)
					client.set_user(PID, PID_HMAC)

					response = await client.login(0x3200)

					s = settings.load('friends')
					s.configure("ridfebb9", 20000)
					async with backend.connect(s, response.host, response.port) as be:
						async with be.login(str(PID), NEX_PASSWORD) as client:
							friends_client = friends.FriendsClientV1(client)
							if time.time() - begun < 30:
								time.sleep(delay)
								await friends_client.update_comment('3dsrpc.com')
							since = time.time()

							if time.time() - since > 3600:
								break

							time.sleep(delay)
							print('Cleaning out to zero')
							removables = await friends_client.get_all_friends()
							for friend in removables:
								time.sleep(delay / 4)
								await friends_client.remove_friend_by_principal_id(friend.unk1)
							print('Removed %s friends' % str(len(removables)))

							removeList = []
							cleanUp = []
							time.sleep(delay)
							await friends_client.add_friend_by_principal_ids(0, rotation)

							time.sleep(delay)
							t = await friends_client.get_all_friends()
							if len(t) < len(rotation):
								for ID in rotation:
									if ID not in [ f.unk1 for f in t ]:
										removeList.append(ID)
							x = t
							t = []
							for t1 in x:
								if t1.unk1 in rotation:
									t.append(t1)
								else:
									cleanUp.append(t1.unk1)

							for remover in removeList:
								cursor.execute('DELETE FROM friends WHERE friendCode = ?', (str(convertPrincipalIdtoFriendCode(remover)).zfill(12),))
							con.commit()

							cursor.execute('SELECT * FROM discord')
							di = cursor.fetchall()
							for dn in di:
								try:
									if refreshBearer(dn[1], dn[2], dn[6], dn[0]):
										time.sleep(delay)
								except:
									deleteDiscordUser(dn[0])

							if len(t) > 0:
								time.sleep(delay)
								f = await friends_client.get_friend_presence([ e.unk1 for e in t ])
								users = []
								for game in f:
									# game.unk == principalId
									users.append(game.unk)
									#print(game.__dict__)
									#print(game.presence.__dict__)
									#print(game.presence.game_key.__dict__)
									gameDescription = game.presence.game_mode_description
									if not gameDescription: gameDescription = ''
									joinable = bool(game.presence.join_availability_flag)

									cursor.execute('SELECT * FROM discordFriends WHERE friendCode = ? AND active = ?', (str(convertPrincipalIdtoFriendCode(users[-1])).zfill(12), True))
									v = cursor.fetchall()
									for r in v:
										cursor.execute('SELECT * FROM friends WHERE friendCode = ?', (str(convertPrincipalIdtoFriendCode(users[-1])).zfill(12),))
										v2 = list(cursor.fetchone())
										try:
											v2[2] = int(v2[2])
										except:
											break
										cursor.execute('SELECT * FROM discord WHERE ID = ?', (r[0],))
										v3 = cursor.fetchone()
										if not v2[1] or v2[2] != game.presence.game_key.title_id or not v3[3] or time.time() - v3[5] >= 60:
											principalId = convertFriendCodeToPrincipalId(v2[0])
											presence = {
											    'gameDescription': gameDescription,
											    'game': getTitle(game.presence.game_key.title_id, titlesToUID, titleDatabase),
											}
											mii = v2[8]
											if mii:
											    mii = MiiData().mii_studio_url(mii)
											print('[UPDATING %s]' % v2[0])
											try:
												updatePresence(v3[2], v3[1], v3[3], v3[5], v3[6], {
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
												deleteDiscordUser(v3[0])
											time.sleep(delay)

									cursor.execute('UPDATE friends SET online = ?, titleID = ?, updID = ?, joinable = ?, gameDescription = ?, lastOnline = ? WHERE friendCode = ?', (True, game.presence.game_key.title_id, game.presence.game_key.title_version, joinable, gameDescription, time.time(), str(convertPrincipalIdtoFriendCode(users[-1])).zfill(12)))
								for user in [ h for h in rotation if not h in users ]:

									cursor.execute('SELECT * FROM discordFriends WHERE friendCode = ?', (str(convertPrincipalIdtoFriendCode(user)).zfill(12),))
									v = cursor.fetchall()
									for r in v:
										cursor.execute('SELECT * FROM friends WHERE friendCode = ?', (str(convertPrincipalIdtoFriendCode(user)).zfill(12),))
										v2 = list(cursor.fetchone())
										cursor.execute('SELECT * FROM discord WHERE ID = ?', (r[0],))
										v3 = cursor.fetchone()
										if v2[1] or v3[3]:
											print('[RESETTING %s]' % v2[0])
											try:
												resetPresence(v3[2], v3[1], v3[3], v3[5], v3[6])
											except:
												deleteDiscordUser(v3[0])
											time.sleep(delay)

									cursor.execute('UPDATE friends SET online = ?, titleID = ?, updID = ? WHERE friendCode = ?', (False, 0, 0, str(convertPrincipalIdtoFriendCode(user)).zfill(12)))

								con.commit()

								# I just do not understand what I'm doing wrong with get_friend_mii_list
								# The docs do not specify much
								# And no matter how many trials I do with varying inputs, nothing works
								# I do not give up, but until I figure it out, the slower method (get_friend_mii)
								# will have to do.

								for ti in t:
									work = False
									for l in list_:
										if l[0] == ti.unk1 and time.time() - l[1] <= 300:
											work = True
									if not work:
										continue

									time.sleep(delay)

									ti.unk2 = 0 # A cursed (but operable) 'hack'
									try:
										j1 = await friends_client.get_friend_persistent_info([ti.unk1,])
									except:
										continue
									comment = j1[0].message
									jeuFavori = 0
									username = ''
									face = ''
									if not comment.endswith(' '):
										# Get user's mii + username from mii
										m = await friends_client.get_friend_mii([ti,])
										username = m[0].mii.unk1
										mii_data = m[0].mii.mii_data
										obj = MiiData()
										obj.decode(obj.convert(io.BytesIO(mii_data)))
										face = obj.mii_studio()['data']

										# Get user's favorite game
										jeuFavori = j1[0].game_key.title_id
									else:
										comment = ''
									cursor.execute('UPDATE friends SET username = ?, message = ?, mii = ?, jeuFavori = ? WHERE friendCode = ?', (username, comment, face, jeuFavori, str(convertPrincipalIdtoFriendCode(ti.unk1)).zfill(12)))
									con.commit()

							for friend in rotation + cleanUp:
								time.sleep(delay / 4)
								await friends_client.remove_friend_by_principal_id(friend)
				except Exception as e:
					print('An error occurred!\n%s' % e)
					print(traceback.format_exc())
					time.sleep(2)

if __name__ == '__main__':
	try:
		anyio.run(main)
	except (KeyboardInterrupt, Exception) as e:
		startDBTime(0)
		print(e)
