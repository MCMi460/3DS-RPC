# Created by Deltaion Lee (MCMi460) on Github
# Based from NintendoClients' `examples/3ds/friends.py`

from nintendo import nasc
from nintendo.nex import backend, friends, settings, streams
from nintendo.nex import common
from enum import Enum
import anyio, time, sqlite3, sys, traceback
sys.path.append('../')
from api.private import SERIAL_NUMBER, MAC_ADDRESS, DEVICE_CERT, DEVICE_NAME, REGION, LANGUAGE, NINTENDO_PID, PRETENDO_PID, PID_HMAC, NINTENDO_NEX_PASSWORD, PRETENDO_NEX_PASSWORD
from api import *
from api.love2 import *

import logging
logging.basicConfig(level=logging.INFO)

delay = 2
since = 0
quicker = 6
begun = time.time()
startDBTime(begun)

network:int = 0

class NetworkIDsToName(Enum): # i mean it is horrible, but technically it allows somewhat easier addition of networks (if that ever happens, which i doubt)
	nintendo = 0
	pretendo = 1


async def main():
	while True:
		time.sleep(1)
		print('Grabbing new friends...')
		with sqlite3.connect('sqlite/fcLibrary.db') as con:
			cursor = con.cursor()
			cursor.execute('SELECT friendCode, lastAccessed FROM ' + NetworkIDsToName(network).name + "_friends")
			result = cursor.fetchall()
			if not result:
				continue

			list_ = [ (convertFriendCodeToPrincipalId(f[0]), f[1]) for f in result ]
			lst = [ f[0] for f in list_ ]

			for i in range(0, len(lst), 100):
				rotation = lst[i:i+100]

				try:
					client = nasc.NASCClient()
					client.set_title(0x0004013000003202, 20) # to be honest, this should be seperate between networks, so if one eg, gets banned, you still get to keep the friend code for the other network, but i'm lazy.
					client.set_locale(REGION, LANGUAGE)

					if network == 0: # Nintendo Network
						client.set_url("nasc.nintendowifi.net")
						PID = NINTENDO_PID
						NEX_PASSWORD = NINTENDO_NEX_PASSWORD
						ACCESS_KEY:str = "ridfebb9"
						
					elif network == 1:
						client.set_url("nasc.pretendo.cc")
						client.context.set_authority(None)
						PID = PRETENDO_PID
						NEX_PASSWORD = PRETENDO_NEX_PASSWORD
						ACCESS_KEY:str = "9f2b4678"
						
					else:
						raise Exception(network + " is not a valid network \"id\"")
					
					client.set_device(SERIAL_NUMBER, MAC_ADDRESS, DEVICE_CERT, DEVICE_NAME)
					client.set_user(PID , PID_HMAC)
					
					response = await client.login(0x3200)

					s = settings.load('friends')
					s.configure(ACCESS_KEY, 20000)
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
								time.sleep(delay / quicker)
								await friends_client.remove_friend_by_principal_id(friend.pid)
							print('Removed %s friends' % str(len(removables)))

							removeList = []
							cleanUp = []
							time.sleep(delay)
							await friends_client.add_friend_by_principal_ids(0, rotation)

							time.sleep(delay)
							t = await friends_client.get_all_friends()
							if len(t) < len(rotation):
								for ID in rotation:
									if ID not in [ f.pid for f in t ]:
										removeList.append(ID)
							x = t
							t = []
							for t1 in x:
								if t1.pid in rotation:
									t.append(t1)
								else:
									cleanUp.append(t1.pid)

							for remover in removeList:
								cursor.execute('DELETE FROM ' + NetworkIDsToName(network).name + "_friends" + ' WHERE friendCode = ?', (str(convertPrincipalIdtoFriendCode(remover)).zfill(12),))
								cursor.execute('DELETE FROM discordFriends WHERE friendCode = ? AND network = ?', (str(convertPrincipalIdtoFriendCode(remover)).zfill(12), str(network)))
							con.commit()

							if len(t) > 0:
								time.sleep(delay)
								f = await friends_client.get_friend_presence([ e.pid for e in t ])
								users = []
								for game in f:
									# game.unk == principalId
									users.append(game.pid)
									#print(game.__dict__)
									#print(game.presence.__dict__)
									#print(game.presence.game_key.__dict__)
									gameDescription = game.presence.game_mode_description
									if not gameDescription: gameDescription = ''
									joinable = bool(game.presence.join_availability_flag)

									cursor.execute('UPDATE ' + NetworkIDsToName(network).name + "_friends" + ' SET online = ?, titleID = ?, updID = ?, joinable = ?, gameDescription = ?, lastOnline = ? WHERE friendCode = ?', (True, game.presence.game_key.title_id, game.presence.game_key.title_version, joinable, gameDescription, time.time(), str(convertPrincipalIdtoFriendCode(users[-1])).zfill(12)))
								for user in [ h for h in rotation if not h in users ]:
									cursor.execute('UPDATE ' + NetworkIDsToName(network).name + "_friends" + ' SET online = ?, titleID = ?, updID = ? WHERE friendCode = ?', (False, 0, 0, str(convertPrincipalIdtoFriendCode(user)).zfill(12)))

								con.commit()

								# I just do not understand what I'm doing wrong with get_friend_mii_list
								# The docs do not specify much
								# And no matter how many trials I do with varying inputs, nothing works
								# I do not give up, but until I figure it out, the slower method (get_friend_mii)
								# will have to do.

								for ti in t:
									work = False
									for l in list_:
										if l[0] == ti.pid and time.time() - l[1] <= 600:
											work = True
									if not work:
										continue

									time.sleep(delay)

									ti.friend_code = 0 # A cursed (but operable) 'hack'
									try:
										j1 = await friends_client.get_friend_persistent_info([ti.pid,])
									except:
										continue
									comment = j1[0].message
									jeuFavori = 0
									username = ''
									face = ''
									if not comment.endswith(' '):
										# Get user's mii + username from mii
										m = await friends_client.get_friend_mii([ti,])
										username = m[0].mii.name
										mii_data = m[0].mii.mii_data
										obj = MiiData()
										obj.decode(obj.convert(io.BytesIO(mii_data)))
										face = obj.mii_studio()['data']

										# Get user's favorite game
										jeuFavori = j1[0].game_key.title_id
									else:
										comment = ''
									cursor.execute('UPDATE ' + NetworkIDsToName(network).name + "_friends" + ' SET username = ?, message = ?, mii = ?, jeuFavori = ? WHERE friendCode = ?', (username, comment, face, jeuFavori, str(convertPrincipalIdtoFriendCode(ti.pid)).zfill(12)))
									con.commit()

							for friend in rotation + cleanUp:
								time.sleep(delay / quicker)
								await friends_client.remove_friend_by_principal_id(friend)
				except Exception as e:
					print('An error occurred!\n%s' % e)
					print(traceback.format_exc())
					time.sleep(2)
def invalidArgument(): 
	print("Missing or Invalid Network Selection!") # Probs a better way to do these prints, but oh well, if it works, it works
	print("")
	print("Valid options are (seperated by commas):")
	print("nintendo, 0,")
	print("pretendo, 1")
	exit()
	
if __name__ == '__main__':
	try:
		if len(sys.argv) <= 1:
			invalidArgument()
		if sys.argv[1].isnumeric(): # number check!
			if (int(sys.argv[1]) in [e.value for e in NetworkIDsToName]):
				network = int(sys.argv[1])
			else:
				invalidArgument()
		else:
			if (sys.argv[1] in [e.name for e in NetworkIDsToName]):
				network = int(NetworkIDsToName[sys.argv[1]].value)
			else:
				invalidArgument()
				
		anyio.run(main)
	except (KeyboardInterrupt, Exception) as e:
		startDBTime(0)
		print(e)