# Based from NintendoClients' `examples/3ds/friends.py`

from nintendo import nasc
from nintendo.nex import backend, friends, settings, streams
from nintendo.games import Friends3DS
import anyio, time, sqlite3
from private import SERIAL_NUMBER, MAC_ADDRESS, DEVICE_CERT, DEVICE_NAME, REGION, LANGUAGE, PID, PID_HMAC, NEX_PASSWORD, privFriend
from . import *

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

		s = settings.load("friends")
		s.configure(Friends3DS.ACCESS_KEY, Friends3DS.NEX_VERSION)
		async with backend.connect(s, response.host, response.port) as be:
			async with be.login(str(PID), NEX_PASSWORD) as client:
				friends_client = friends.FriendsClientV1(client)
				await friends_client.update_comment("github/MCMi460")
				since = time.time()

				while True:
					time.sleep(delay)

					# con = sqlite3.connect('fcLibrary.db')
					# cursor = con.cursor()

					# cursor.execute('SELECT friendCode FROM friends')
					# lst = cursor.fetchall()
					# Obviously change the above lines, but the premise remains
					lst = [ convertFriendCodeToPrincipalId(privFriend), ] # Debug purposes currently

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

						time.sleep(delay)
						if len(t) < 1:
							continue
						f = await friends_client.get_friend_presence([ e.unk1 for e in t ])
						for game in f:
							# game.unk == principalId
							print(game.__dict__)
							print(game.presence.__dict__)
							print(game.presence.game_key.__dict__)

						time.sleep(delay)
						for friend in rotation:
							await friends_client.remove_friend_by_principal_id(friend)

						# for remover in removeList:
						# 	cursor.execute('DELETE FROM friends WHERE friendCode = %s' % remover)
						#	con.commit()

					if time.time() - since > 3600:
						break

anyio.run(main)
