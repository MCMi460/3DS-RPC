import time, sys, secrets, requests, json, pickle
sys.path.append('../')
from api import *
from api.love2 import *
from api.private import CLIENT_ID, CLIENT_SECRET, HOST
from api.networks import NetworkType

from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.orm import Session
from database import DiscordFriends, Friend
from database import Discord as DiscordTable

API_ENDPOINT:str = 'https://discord.com/api/v10'

with open('./cache/databases.dat', 'rb') as file:
	t = pickle.loads(file.read())
	titleDatabase = t[0]
	titlesToUID = t[1]

engine = create_engine('sqlite:///' + os.path.abspath('sqlite/fcLibrary.db'))

class DiscordSession():
	def retire(self, refresh):
		with Session(engine) as session:
			session.execute(
				update(DiscordTable)
				.where(DiscordTable.refresh)
				.values(refresh=refresh)
			)
			session.commit()

	def create(self, refresh, discord_session):
		with Session(engine) as session:
			session.execute(
				update(DiscordTable)
				.where(DiscordTable.refresh)
				.values(session=discord_session)
			)
			session.commit()
		return discord_session

	def update(self, discord_session):
		with Session(engine) as session:
			session.execute(
				update(DiscordTable)
				.where(DiscordTable.last_accessed == time.time())
				.values(discord_session)
			)
			session.commit()

class Discord():
	def updatePresence(self, bearer:str, refresh:str, session:str, lastAccessed:int, generationDate:int, userData, config, network:NetworkType):
		if time.time() - lastAccessed >= 1000:
			session = DiscordSession(self.con, self.cursor).retire(refresh)
		elif time.time() - lastAccessed <= 30:
			print('[MANUAL RATE LIMITED]')
			return False
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
				data['activities'][0]['assets']['large_image'] = game['icon_url'].replace('/cdn/', HOST + '/cdn/')
				data['activities'][0]['assets']['large_text'] = game['name']
			if presence['gameDescription']:
				data['activities'][0]['details'] = presence['gameDescription']
			if userData['User']['username'] and bool(config[0]):
				data['activities'][0]['buttons'] = [{'label': 'Profile', 'url': HOST + '/user/' + userData['User']['friendCode'] + '/?network=' + network.lower_name()},]
			if userData['User']['username'] and game['icon_url'] and bool(config[1]):
				data['activities'][0]['assets']['small_image'] = userData['User']['mii']['face']
				data['activities'][0]['assets']['small_text'] = '-'.join(userData['User']['friendCode'][i:i+4] for i in range(0, 12, 4)) + ' on ' + network.lower_name().capitalize()
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
			DiscordSession(self.con, self.cursor).create(refresh, r.json()['token'])
			DiscordSession(self.con, self.cursor).update(r.json()['token'])
			return True

	def resetPresence(self, bearer, refresh, session, lastAccessed, generationDate):
		if not session:
			print('[NO SESSION TO RESET]')
			return False
		elif time.time() - lastAccessed <= 30:
			print('[MANUAL RATE LIMITED]')
			return False
		DiscordSession(self.con, self.cursor).update(session)
		headers = {
		    'Authorization': 'Bearer %s' % bearer,
			'Content-Type': 'application/json',
		}
		data = {
			'token': session,
		}
		r = requests.post('%s/users/@me/headless-sessions/delete' % API_ENDPOINT, data = json.dumps(data), headers = headers)
		r.raise_for_status()
		DiscordSession(self.con, self.cursor).create(refresh, '') # Reset session
		return True

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
		json_response = requests.post('%s/oauth2/token' % API_ENDPOINT, data = data, headers = headers)
		json_response.raise_for_status()
		response = json_response.json()

		with Session(engine) as session:
			session.execute(
				update(DiscordTable)
				.where(DiscordTable.refresh)
				.values(
					refresh=response['refresh_token'],
					bearer=response['access_token'],
					generationDate=time.time()
				)
			)
			session.commit()
		return True

	def deleteDiscordUser(self, ID:int):
		print('[DELETING %s]' % ID)
		with Session(engine) as session:
			session.execute(delete(DiscordTable).where(DiscordTable.id == id))
			session.execute(delete(DiscordFriends).where(DiscordFriends.id == id))
			session.commit()

	def deactivateDiscordUser(self, ID:int):
		print('[DEACTIVATING %s]' % ID)
		with Session(engine) as session:
			session.execute(delete(DiscordTable).where(DiscordTable.id == id))
			session.execute(delete(DiscordFriends).where(DiscordFriends.id == id))
			session.commit()

delay = 2

while True:
	time.sleep(delay)

	with Session(engine) as session:
		discord = Discord()

		
		group = session.scalars(select(DiscordTable)).all()
		for dn in group:
			try:
				
				if discord.refreshBearer(dn.refresh, dn.bearer, dn.generation_date, dn.id):
					time.sleep(delay * 2)
			except:
				#discord.deleteDiscordUser(dn[0])
				discord.deactivateDiscordUser(dn.id)

		wait = time.time()

		while time.time() - wait <= 1200:
			discordFriends = session.scalars(select(DiscordFriends).where(DiscordFriends.active)).all()
			discordUsers = session.scalars(select(DiscordTable)).all()

			inactiveUsers:list[DiscordTable] = []

			for user in discordUsers:
				if any(user.id == inactive_user.id for inactive_user in inactiveUsers):
					continue
				fail = False
				for associatedFriends in discordFriends:
					if user.id == associatedFriends.id:
						fail = True
				if not fail:
					inactiveUsers.append(user)
			print('[CLEARING INACTIVES; BATCH OF %s]' % len(inactiveUsers))

			for inactive_user in inactiveUsers:
				try:
					print('[RESETTING %s]' % inactive_user.id)
					if discord.resetPresence(inactive_user.bearer, inactive_user.refresh, inactive_user.session, inactive_user.last_accessed, inactive_user.generation_date):
						time.sleep(delay)
				except:
					discord.deleteDiscordUser(inactive_user.id)

			time.sleep(delay)

			print('[BATCH OF %s USERS]' % len(discordFriends))
			if len(discordFriends) < 1:
				time.sleep(delay)
				continue
			for discord_friend in discordFriends:
				print('[RUNNING %s - %s on %s]' % (discord_friend.id, discord_friend.friend_code, discord_friend.network.lower_name()))
				
				friend_data = session.scalar(
					select(Friend)
					.where(Friend.friend_code == discord_friend.friend_code)
					.where(Friend.network == discord_friend.network)
				)

				discord_user = session.scalar(select(DiscordTable).where(DiscordTable.id == discord_friend.id))
				if time.time() - discord_user.last_accessed >= 60 and friend_data:
					principalId = convertFriendCodeToPrincipalId(friend_data.friend_code)
					if not friend_data.online:
						try:
							print('[RESETTING %s on %s]' % (friend_data.friend_code, friend_data.network.lower_name()))
							if discord.resetPresence(discord_user.bearer, discord_user.refresh, discord_user.session, discord_user.last_accessed, discord_user.generation_date):
								time.sleep(delay)
						except:
							discord.deleteDiscordUser(discord_user.id)
					else:
						presence = {
							'gameDescription': friend_data.game_description,
							'game': getTitle(friend_data.title_id, titlesToUID, titleDatabase),
						}
						mii = friend_data.mii
						if mii:
							mii = MiiData().mii_studio_url(mii)
						print('[UPDATING %s]' % friend_data.id)
						try:
							if discord.updatePresence(discord_user.bearer, discord_user.refresh, discord_user.session, discord_user.last_accessed, discord_user.generation_date, {
									'User': {
										'friendCode': str(convertPrincipalIdtoFriendCode(principalId)).zfill(12),
										'online': friend_data.online,
										'Presence': presence,
										'username': friend_data.username,
										'mii': mii,
										'lastAccessed': friend_data.last_accessed,
									}
								}, (discord_user.show_profile_button, discord_user.show_small_image), discord_friend.network):
								time.sleep(delay)
						except:
							discord.deleteDiscordUser(discord_user.id)
				else:
					print('[WAIT]')
			time.sleep(delay)
