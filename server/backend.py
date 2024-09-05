# Created by Deltaion Lee (MCMi460) on Github
# Based from NintendoClients' `examples/3ds/friends.py`
import asyncio
import signal
import sys
import time
import json
import os
import traceback
import logging

from nintendo import nasc
from nintendo.nex import backend, friends, settings
from sqlalchemy import create_engine, delete, select, update
from sqlalchemy.orm import Session
from database import start_db_time, get_db_url, Friend, DiscordFriends
from api.private import (SERIAL_NUMBER, MAC_ADDRESS, DEVICE_CERT, DEVICE_NAME,REGION, LANGUAGE, NINTENDO_PID, PRETENDO_PID, PID_HMAC, NINTENDO_NEX_PASSWORD, PRETENDO_NEX_PASSWORD)
from api.love2 import *
from api.networks import NetworkType, InvalidNetworkError

logging.basicConfig(level=logging.INFO)

stop_event = asyncio.Event()


class FriendScraperInstance:
    def __init__(self, network, config, begun):
        self.network = network
        self.delay = 2 if network == NetworkType.NINTENDO else 0
        self.quicker = 15 if network == NetworkType.NINTENDO else 1
        self.begun = begun
        self.since = 0
        self.config = config

    async def scrape(self):
        engine = create_engine(get_db_url())
        session = Session(engine)

        while not stop_event.is_set():
            await asyncio.sleep(1)
            print(f'Grabbing new friends using {self.config["display_name"]}')

            queried_friends = session.scalars(select(Friend).where(Friend.network == self.network)).all()
            if not queried_friends:
                continue

            all_friends = [(convertFriendCodeToPrincipalId(f.friend_code), f.last_accessed) for f in queried_friends]
            friend_codes = [f[0] for f in all_friends]

            for i in range(0, len(friend_codes), 100):
                if stop_event.is_set():
                    break

                rotation = friend_codes[i:i + 100]

                try:
                    client = nasc.NASCClient()
                    # TODO: This should be separate between networks.
                    # E.g. if the friend code was is banned on one network,
                    # you'd still be able to keep the friend code for the other network.

                    client.set_title(0x0004013000003202, 20)
                    client.set_locale(REGION, LANGUAGE)

                    if self.network == NetworkType.NINTENDO:
                        client.set_url("nasc.nintendowifi.net")
                        PID = NINTENDO_PID
                        NEX_PASSWORD = NINTENDO_NEX_PASSWORD
                    elif self.network == NetworkType.PRETENDO:
                        client.set_url("nasc.pretendo.cc")
                        client.context.set_authority(None)
                        PID = PRETENDO_PID
                        NEX_PASSWORD = PRETENDO_NEX_PASSWORD
                    else:
                        raise InvalidNetworkError(f"Network type {self.network} is not configured for querying")

                    client.set_device(SERIAL_NUMBER, MAC_ADDRESS, DEVICE_CERT, DEVICE_NAME)
                    client.set_user(PID, PID_HMAC)

                    response = await client.login(0x3200)

                    s = settings.load('friends')
                    s.configure("ridfebb9", 20000)

                    async with backend.connect(s, response.host, response.port) as be:
                        async with be.login(str(PID), NEX_PASSWORD) as client:
                            friends_client = friends.FriendsClientV1(client)
                            if time.time() - self.begun < 30:
                                await asyncio.sleep(self.delay)
                                await friends_client.update_comment('3dsrpc.com')
                            self.since = time.time()

                            if time.time() - self.since > 3600:
                                break

                            await asyncio.sleep(self.delay)
                            print('Cleaning out to zero')
                            removables = await friends_client.get_all_friends()
                            for friend in removables:
                                if stop_event.is_set():
                                    break
                                await asyncio.sleep(self.delay / self.quicker)
                                await friends_client.remove_friend_by_principal_id(friend.pid)
                            print(f'Removed {len(removables)} friends')

                            removal_list = []
                            cleanUp = []

                            if self.network == NetworkType.PRETENDO:
                                for friend_pid in rotation:
                                    if stop_event.is_set():
                                        break
                                    await asyncio.sleep(self.delay / self.quicker)
                                    await friends_client.add_friend_by_principal_id(0, friend_pid)
                            else:
                                await asyncio.sleep(self.delay)
                                await friends_client.add_friend_by_principal_ids(0, rotation)

                            await asyncio.sleep(self.delay)

                            network_friends = await friends_client.get_all_friends()
                            if len(network_friends) < len(rotation):
                                for current_pid in rotation:
                                    if current_pid not in [f.pid for f in network_friends]:
                                        removal_list.append(current_pid)

                            x = network_friends
                            network_friends = []
                            for t1 in x:
                                if t1.pid in rotation:
                                    network_friends.append(t1)
                                else:
                                    cleanUp.append(t1.pid)

                            for removed_friend in removal_list:
                                if stop_event.is_set():
                                    break
                                removed_friend_code = str(convertPrincipalIdtoFriendCode(removed_friend)).zfill(12)
                                session.execute(delete(Friend).where(Friend.friend_code == removed_friend_code).where(Friend.network == self.network))
                                session.execute(delete(DiscordFriends).where(
                                    DiscordFriends.friend_code == removed_friend_code,
                                    DiscordFriends.network == self.network)
                                )
                                session.commit()

                            if len(network_friends) > 0:
                                await asyncio.sleep(self.delay)
                                tracked_presences = await friends_client.get_friend_presence([e.pid for e in network_friends])
                                users = []
                                for game in tracked_presences:
                                    users.append(game.pid)
                                    game_description = game.presence.game_mode_description
                                    if not game_description:
                                        game_description = ''
                                    joinable = bool(game.presence.join_availability_flag)

                                    friend_code = str(convertPrincipalIdtoFriendCode(users[-1])).zfill(12)
                                    session.execute(
                                        update(Friend)
                                        .where(Friend.friend_code == friend_code)
                                        .where(Friend.network == self.network)
                                        .values(
                                            online=True,
                                            title_id=game.presence.game_key.title_id,
                                            upd_id=game.presence.game_key.title_version,
                                            joinable=joinable,
                                            game_description=game_description,
                                            last_online=time.time()
                                        )
                                    )
                                    session.commit()

                                for user in [h for h in rotation if not h in users]:
                                    friend_code = str(convertPrincipalIdtoFriendCode(user)).zfill(12)
                                    session.execute(
                                        update(Friend)
                                        .where(Friend.friend_code == friend_code)
                                        .where(Friend.network == self.network)
                                        .values(
                                            online=False,
                                            title_id=0,
                                            upd_id=0
                                        )
                                    )
                                    session.commit()

                                for current_friend in network_friends:
                                    if stop_event.is_set():
                                        break
                                    work = False
                                    for l in all_friends:
                                        if l[0] == current_friend.pid and time.time() - l[1] <= 600000:
                                            work = True
                                    if not work:
                                        continue

                                    await asyncio.sleep(self.delay)

                                    current_friend.friend_code = 0
                                    try:
                                        current_info = await friends_client.get_friend_persistent_info([current_friend.pid])
                                    except:
                                        continue
                                    comment = current_info[0].message
                                    favorite_game = 0
                                    username = ''
                                    face = ''
                                    if not comment.endswith(' '):
                                        m = await friends_client.get_friend_mii([current_friend])
                                        username = m[0].mii.name
                                        mii_data = m[0].mii.mii_data
                                        obj = MiiData()
                                        obj.decode(obj.convert(io.BytesIO(mii_data)))
                                        face = obj.mii_studio()['data']

                                        favorite_game = current_info[0].game_key.title_id
                                    else:
                                        comment = ''

                                    friend_code = str(convertPrincipalIdtoFriendCode(current_friend.pid)).zfill(12)
                                    session.execute(
                                        update(Friend)
                                        .where(Friend.friend_code == friend_code)
                                        .where(Friend.network == self.network)
                                        .values(
                                            username=username,
                                            message=comment,
                                            mii=face,
                                            favorite_game=favorite_game
                                        )
                                    )
                                    session.commit()

                            for friend in rotation + cleanUp:
                                if stop_event.is_set():
                                    break
                                await asyncio.sleep(self.delay / self.quicker)
                                await friends_client.remove_friend_by_principal_id(friend)
                except Exception as e:
                    print('An error occurred!\n%s' % e)
                    print(traceback.format_exc())
                    await asyncio.sleep(2)


async def shutdown(signal, loop):
    print(f"Received exit signal {signal.name}...")
    stop_event.set()
    await asyncio.sleep(1)
    loop.stop()


async def main(network):
    def load_config(folder):
        config_files = [f for f in os.listdir(folder) if f.endswith('.json')]
        configs = []
        for file in config_files:
            with open(os.path.join(folder, file), 'r') as f:
                configs.append(json.load(f))
        return configs

    config_folders = {
        NetworkType.NINTENDO: "accounts/nintendo",
        NetworkType.PRETENDO: "accounts/pretendo"
    }

    configs = load_config(config_folders[network])
    begun = time.time()

    tasks = [asyncio.create_task(FriendScraperInstance(network, config, begun).scrape()) for config in configs]

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s, loop)))

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        print("Tasks were cancelled.")

if __name__ == '__main__':
    try:
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('-n', '--network', choices=[member.lower_name() for member in NetworkType], required=True)
        args = parser.parse_args()

        network = NetworkType[args.network.upper()]
        asyncio.run(main(network))
    except KeyboardInterrupt:
        print('KeyboardInterrupt received in main thread.')
        sys.exit(0)
    except Exception as e:
        print(f"Unhandled exception: {e}")
        sys.exit(1)
