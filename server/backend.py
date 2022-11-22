# Created by Deltaion Lee (MCMi460) on Github
# Based from NintendoClients' `examples/3ds/friends.py`

from nintendo import nasc
from nintendo.nex import backend, friends, settings, streams
from nintendo.games import Friends3DS
import anyio, time, sqlite3, sys
sys.path.append('../')
from api.private import SERIAL_NUMBER, MAC_ADDRESS, DEVICE_CERT, DEVICE_NAME, REGION, LANGUAGE, PID, PID_HMAC, NEX_PASSWORD
from api import *

import logging
logging.basicConfig(level=logging.INFO)

delay = 2
since = 0

async def main():
	while True:
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

				while True:
					try:
						if time.time() - since > 3600:
							break
						time.sleep(delay)

						print('Grabbing new friends...')
						con = sqlite3.connect('sqlite/fcLibrary.db')
						cursor = con.cursor()

						cursor.execute('SELECT friendCode, lastAccessed FROM friends')
						result = cursor.fetchall()
						if not result:
							continue
						removeList = []
						for row in result:
							if time.time() - row[1] > 31:
								removeList.append(row[0])
						for remover in removeList:
							cursor.execute('DELETE FROM friends WHERE friendCode = %s' % remover)
						con.commit()

						cursor.execute('SELECT friendCode FROM friends')
						result = cursor.fetchall()
						if not result:
							continue
						lst = [ convertFriendCodeToPrincipalId(f[0]) for f in result ]
						# Obviously change the above lines, but the premise remains
						#lst = [ convertFriendCodeToPrincipalId(privFriend), ] # Debug purposes currently
						#print(lst)

						for i in range(0, len(lst), 100):
							rotation = lst[i:i+100]

							removeList = []
							time.sleep(delay)
							await friends_client.add_friend_by_principal_ids(0, rotation)

							time.sleep(delay)
							t = await friends_client.get_all_friends()
							if len(t) < len(rotation):
								for ID in rotation:
									if ID not in [ f.unk1 for f in t ]:
										removeList.append(ID)

							for remover in removeList:
								cursor.execute('DELETE FROM friends WHERE friendCode = %s' % convertPrincipalIdtoFriendCode(remover))
							con.commit()

							if len(t) > 0:
								time.sleep(delay)
								f = await friends_client.get_friend_presence([ e.unk1 for e in t ])
								users = []
								for game in f:
									# game.unk == principalId
									users.append(game.unk)
									cursor.execute('UPDATE friends SET online = %s, titleID = %s, updID = %s WHERE friendCode = %s' % (True, game.presence.game_key.title_id, game.presence.game_key.title_version, convertPrincipalIdtoFriendCode(users[-1])))
								for user in [ h for h in rotation if not h in users ]:
									cursor.execute('UPDATE friends SET online = %s, titleID = %s, updID = %s WHERE friendCode = %s' % (False, 0, 0, convertPrincipalIdtoFriendCode(user)))
								con.commit()

							time.sleep(delay)
							for friend in rotation:
								await friends_client.remove_friend_by_principal_id(friend)
					except RuntimeError as e:
						print('An error occurred!\n%s' % e)
						break

if __name__ == '__main__':
	anyio.run(main)
