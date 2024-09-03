import sys, pickle
sys.path.append('../')
from api import *
from api.love2 import *
from api.private import CLIENT_ID, CLIENT_SECRET, HOST
from api.networks import NetworkType

from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.orm import Session
from database import get_db_url, DiscordFriends, Friend
from database import Discord as DiscordTable

API_ENDPOINT:str = 'https://discord.com/api/v10'

with open('./cache/databases.dat', 'rb') as file:
	t = pickle.loads(file.read())
	titleDatabase = t[0]
	titlesToUID = t[1]

engine = create_engine(get_db_url())

session = Session(engine)


class DiscordSession():
	def retire(self, refresh):
		session.execute(
			update(DiscordTable)
			.where(DiscordTable.refresh == refresh)
			.values(session='')
		)
		session.commit()

	def create(self, refresh, discord_session):
		session.execute(
			update(DiscordTable)
			.where(DiscordTable.refresh == refresh)
			.values(session=discord_session)
		)
		session.commit()
		return discord_session

	def update(self, discord_session):
		session.execute(
			update(DiscordTable)
			.where(DiscordTable.last_accessed == time.time())
			.values(discord_session)
		)
		session.commit()


class Discord():
	def update_presence(self, bearer: str, refresh: str, user_token: str, last_accessed: int, generation_date: int, userData, config, network: NetworkType):
		if time.time() - last_accessed >= 1000:
			DiscordSession().retire(refresh)
		elif time.time() - last_accessed <= 30:
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
			if user_token:
				data['token'] = user_token

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
			DiscordSession().create(refresh, r.json()['token'])
			DiscordSession().update(r.json()['token'])
			return True

	def reset_presence(self, bearer: str, refresh: str, session: str, last_accessed: int, generation_date: int):
		if not session:
			print('[NO SESSION TO RESET]')
			return False
		elif time.time() - last_accessed <= 30:
			print('[MANUAL RATE LIMITED]')
			return False
		DiscordSession().update(session)
		headers = {
			'Authorization': 'Bearer %s' % bearer,
			'Content-Type': 'application/json',
		}
		data = {
			'token': session,
		}
		r = requests.post('%s/users/@me/headless-sessions/delete' % API_ENDPOINT, data = json.dumps(data), headers = headers)
		r.raise_for_status()

		# Reset session
		DiscordSession().create(refresh, '')
		return True

	def refresh_bearer(self, refresh: str, access: str, generation_date: int, user_id: int):
		# 30 minutes before the token expires
		if time.time() - generation_date < 604800 - 1800:
			return False
		print('[REFRESH BEARER %s]' % user_id)
		data = {
			'client_id': '%s' % CLIENT_ID,
			'client_secret': '%s' % CLIENT_SECRET,
			'grant_type': 'refresh_token',
			'refresh_token': refresh,
		}
		headers = {
			'Content-Type': 'application/x-www-form-urlencoded',
		}
		json_response = requests.post('%s/oauth2/token' % API_ENDPOINT, data=data, headers=headers)
		json_response.raise_for_status()
		response = json_response.json()

		session.execute(
			update(DiscordTable)
			.where(DiscordTable.refresh == refresh)
			.values(
				refresh=response['refresh_token'],
				bearer=response['access_token'],
				generation_date=time.time()
			)
		)
		session.commit()
		return True

	def delete_discord_user(self, user_id: int):
		print('[DELETING %s]' % user_id)
		session.execute(delete(DiscordTable).where(DiscordTable.id == user_id))
		session.execute(delete(DiscordFriends).where(DiscordFriends.id == user_id))
		session.commit()


delay = 2

while True:
	time.sleep(delay)

	discord = Discord()
	
	group = session.scalars(select(DiscordTable)).all()
	for dn in group:
		try:
			if discord.refresh_bearer(dn.refresh, dn.bearer, dn.generation_date, dn.id):
				time.sleep(delay * 2)
		except:
			discord.delete_discord_user(dn.id)

	wait = time.time()

	while time.time() - wait <= 1200:
		discord_friends = session.scalars(select(DiscordFriends).where(DiscordFriends.active)).all()
		discord_users = session.scalars(select(DiscordTable)).all()

		inactive_users: list[DiscordTable] = []

		for user in discord_users:
			if any(user.id == inactive_user.id for inactive_user in inactive_users):
				continue
			fail = False
			for associatedFriends in discord_friends:
				if user.id == associatedFriends.id:
					fail = True
			if not fail:
				inactive_users.append(user)
		print('[CLEARING INACTIVES; BATCH OF %s]' % len(inactive_users))

		for inactive_user in inactive_users:
			try:
				print('[RESETTING %s]' % inactive_user.id)
				if discord.reset_presence(inactive_user.bearer, inactive_user.refresh, inactive_user.session, inactive_user.last_accessed, inactive_user.generation_date):
					time.sleep(delay)
			except:
				discord.delete_discord_user(inactive_user.id)

		time.sleep(delay)

		print('[BATCH OF %s USERS]' % len(discord_friends))
		if len(discord_friends) < 1:
			time.sleep(delay)
			continue
		for discord_friend in discord_friends:
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
						if discord.reset_presence(discord_user.bearer, discord_user.refresh, discord_user.session, discord_user.last_accessed, discord_user.generation_date):
							time.sleep(delay)
					except:
						discord.delete_discord_user(discord_user.id)
				else:
					presence = {
						'gameDescription': friend_data.game_description,
						'game': getTitle(friend_data.title_id, titlesToUID, titleDatabase),
					}
					mii = friend_data.mii
					if mii:
						mii = MiiData().mii_studio_url(mii)
					print('[UPDATING %s]' % discord_user.id)
					try:
						if discord.update_presence(discord_user.bearer, discord_user.refresh, discord_user.session, discord_user.last_accessed, discord_user.generation_date, {
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
						discord.delete_discord_user(discord_user.id)
			else:
				print('[WAIT]')
			time.sleep(delay)
