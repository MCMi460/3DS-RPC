# Created by Deltaion Lee (MCMi460) on Github
# Based from NintendoClients' `examples/3ds/friends.py`

from nintendo import nasc
from nintendo.nex import backend, friends, settings, streams
from nintendo.games import Friends3DS
from nintendo.nex import common
import anyio, time, sqlite3, sys
sys.path.append('../')
from api.private import SERIAL_NUMBER, MAC_ADDRESS, DEVICE_CERT, DEVICE_NAME, REGION, LANGUAGE, PID, PID_HMAC, NEX_PASSWORD
from api import *

import logging
logging.basicConfig(level=logging.INFO)

delay = 2
since = 0
startDBTime(time.time())

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
			list = []
			for row in result:
				# Below is commented out for a constant and continuous loop
				#if time.time() - row[1] <= 30:
				list.append(row[0])

			lst = [ convertFriendCodeToPrincipalId(f) for f in list ]

			for i in range(0, len(lst), 100):
				rotation = lst[i:i+100]

				try:
					client = nasc.NASCClient()
					client.set_title(Friends3DS.TITLE_ID_USA, Friends3DS.LATEST_VERSION)
					client.set_device(SERIAL_NUMBER, MAC_ADDRESS, DEVICE_CERT, DEVICE_NAME)
					client.set_locale(REGION, LANGUAGE)
					client.set_user(PID, PID_HMAC)

					response = await client.login(Friends3DS.GAME_SERVER_ID)

					s = settings.load('friends')
					s.configure(Friends3DS.ACCESS_KEY, Friends3DS.NEX_VERSION)
					async with backend.connect(s, response.host, response.port) as be:
						async with be.login(str(PID), NEX_PASSWORD) as client:
							friends_client = friends.FriendsClientV1(client)
							await friends_client.update_comment('github/MCMi460')
							since = time.time()

							if time.time() - since > 3600:
								break
							time.sleep(delay)

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
							for t1 in t:
								if not t1.unk1 in rotation:
									cleanUp.append(t1.unk1)
									t.remove(t1)

							for remover in removeList:
								cursor.execute('DELETE FROM friends WHERE friendCode = \'%s\'' % str(convertPrincipalIdtoFriendCode(remover)).zfill(12))
							con.commit()

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
									joinable = bool(game.presence.join_availability_flag)

									cursor.execute('UPDATE friends SET online = %s, titleID = %s, updID = %s, joinable = %s, gameDescription = \'%s\' WHERE friendCode = \'%s\'' % (True, game.presence.game_key.title_id, game.presence.game_key.title_version, joinable, gameDescription, str(convertPrincipalIdtoFriendCode(users[-1])).zfill(12)))
								for user in [ h for h in rotation if not h in users ]:
									cursor.execute('UPDATE friends SET online = %s, titleID = %s, updID = %s WHERE friendCode = \'%s\'' % (False, 0, 0, str(convertPrincipalIdtoFriendCode(user)).zfill(12)))

								con.commit()

								# I just do not understand what I'm doing wrong with get_friend_mii_list
								# The docs do not specify much
								# And no matter how many trials I do with varying inputs, nothing works
								# I do not give up, but until I figure it out, the slower method (get_friend_mii)
								# will have to do.
								# Here is where I left off:
								#
								#t2 = []
								#for ti in t:
								#	fff = FriendInfo()
								#	fff.unk1 = ti.unk1
								#	fff.unk2 = common.DateTime(int(time.time()))
								#	t2.append(fff)
								#try:
								#	m = await friends_client.get_friend_mii_list(t2) # PythonCore::ConversionError
								#except Exception as e:
								#	print(logging.exception("message"))
								#

								for ti in t:
									time.sleep(delay)
									j1 = await friends_client.get_friend_comment([ti,])
									username = ''
									face = ''
									if not j1[0].comment.endswith(' '):
										m = await friends_client.get_friend_mii([ti,])
										username = m[0].mii.unk1
										mii_data = m[0].mii.mii_data
										obj = MiiData()
										obj.decode(obj.convert(io.BytesIO(mii_data)))
										face = obj.mii_studio()['face']
									else:
										j1[0].comment = ''
									cursor.execute('UPDATE friends SET username = \'%s\', message = \'%s\', mii = \'%s\' WHERE friendCode = \'%s\'' % (username, j1[0].comment, face, str(convertPrincipalIdtoFriendCode(ti.unk1)).zfill(12)))

								con.commit()

							time.sleep(delay)
							for friend in rotation + cleanUp:
								await friends_client.remove_friend_by_principal_id(friend)
				except Exception as e:
					print('An error occurred!\n%s' % e)
					time.sleep(2)

if __name__ == '__main__':
	try:
		anyio.run(main)
	except (KeyboardInterrupt, Exception) as e:
		startDBTime(0)
		print(e)
