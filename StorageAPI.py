import json
from pathlib import Path
from datetime import datetime, timedelta
from GameAPI import GameAPI
from UserAPI import UserAPI
import StorageStruct as Store
import redis
from typing import Optional, Tuple, Type, TypeVar, List, Literal
import logging

logging.basicConfig(level=logging.INFO)

T = TypeVar("T", Store.User, Store.Game)
"""
GAME_TTL realisticly should be 24 hours, and USER_TTL should be 15/30 minutes.
That is if we get sufficent traffic daily, otherwise when a user does eventually
accesses GameMatch, all cached requests would have expired, and the user needs to
wait for multiples API's to return their reponses. If the user has many friends or
games, games would be the stronger factor, the number of API's requests will hit
the throttle limit, or even the daily limit. If we verify this service, we would 
be provided with API's with TLS and access to more sensitive information. For the
time being cache TTL would remain 90 days.
"""
GAME_TTL = 2160  # 90 days in hours
USER_TTL = 129_600  # 90 days in minutes
GAME_ERROR_CACHE_DIR = Path("cache/game_error_cache")
GAME_CACHE_DIR = Path("cache/game_cache")
USER_CACHE_DIR = Path("cache/user_cache")

GAME_CACHE_DIR.mkdir(exist_ok=True, parents=True)
GAME_ERROR_CACHE_DIR.mkdir(exist_ok=True, parents=True)
USER_CACHE_DIR.mkdir(exist_ok=True, parents=True)
class Storage:

    def __init__(self, user_data_redis: redis.StrictRedis, game_data_redis: redis.StrictRedis):
        self.user_data_redis = user_data_redis
        self.game_data_redis = game_data_redis
    
    def getUser(self, steamid: Store.SteamID) -> Optional[Store.User]:
        user: Store.User = Storage.Memory.get(str(steamid), Store.User, self.user_data_redis)
        if not user: 
            data = Storage.Disk.load_user(steamid)
            if data is None:
                return None
            
            user, age = data
            logging.debug(f"Cached to Redis {steamid=}")
            Storage.Memory.cache(str(steamid), user, self.user_data_redis, age)
        logging.debug(f"Fetched from Redis {steamid=}")  
        return user 
    
    def getGame(self, appid: Store.AppID) -> Optional[Tuple[Store.Game, bool]] | Literal[False]:
        game: Store.Game = Storage.Memory.get(str(appid), Store.Game, self.game_data_redis)
        fetched_from_api = False
        if not game:   
            data = Storage.Disk.load_game(appid)
            if data is None:
                return None
            
            if data is False:
                return False

            game, age, fetched_from_api = data
            logging.debug(f"Cached to Redis {appid=}")
            Storage.Memory.cache(str(appid), game, self.game_data_redis, age)   
        logging.debug(f"Fetched from Redis {appid=}")  
        return game, fetched_from_api
    
    def get_all_users(self):
        user_ids: set[str] = set()
        users: List[Store.User] = []
        for raw_key in self.user_data_redis.scan_iter():
            key = raw_key.decode() if isinstance(raw_key, bytes) else raw_key
            user_ids.add(key)
            user = Storage.Memory.get(key, Store.User, self.user_data_redis)
            if user is not None:
                users.append(user)
        for cache_file in USER_CACHE_DIR.glob("*.json"):
            try:
                if cache_file.name.strip(".json") in user_ids:
                    continue
                user = Store.User.from_dict(json.loads(cache_file.read_text()))
                users.append(user)
            except Exception:
                logging.warning(f"Could not load user cache {cache_file}, skipping")
        return users
    
    class Disk:

        @staticmethod
        def load_game(app_id: Store.AppID) -> Optional[Tuple[Store.Game, timedelta, bool]] | Literal[False]:
            fetched_from_api = False
            cache_file = GAME_CACHE_DIR / f"{app_id}.json"
            error_cache_file = GAME_ERROR_CACHE_DIR / f"{app_id}"

            if cache_file.exists():
                mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                age = datetime.now() - mtime
                if age < timedelta(hours=GAME_TTL):
                    try:
                        data = json.loads(cache_file.read_text())
                        logging.debug(f"Loaded from disk {app_id=}")  
                        return Store.Game.from_dict(data), age, fetched_from_api
                    except Exception as e:
                        logging.error(f"Error while loading from disk {app_id=}: {e}")
            
            if error_cache_file.exists():
                logging.debug(f"Avoiding game {app_id=}")
                return None
            
            logging.info(f"Fetching from SteamAPI {app_id=}")
            game = GameAPI.fetchGameInfo(app_id)
            fetched_from_api = True

            if game is None:
                logging.warning(f"Failed to fetch game {app_id}, Saved to avoid next time")
                error_cache_file.touch(exist_ok=True)
                return None

            if game is False:
                logging.critical(f"TOO MANY REQUESTS:Failed to fetch game {app_id}: ")
                return False
            
            tmp = cache_file.with_suffix(".json.tmp") # create a tmp file to ensure atomicity, - COMP207 -
            tmp.write_text(json.dumps(game.to_dict()))
            tmp.replace(cache_file)
            return game, timedelta(0), fetched_from_api
        

        @staticmethod
        def load_user(steamid: Store.SteamID) -> Optional[Tuple[Store.User, timedelta]]:
            cache_file = USER_CACHE_DIR / f"{steamid}.json"
            if cache_file.exists():
                mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                age = datetime.now() - mtime
                if age < timedelta(minutes=USER_TTL):
                    try:
                        data = json.loads(cache_file.read_text())
                        logging.debug(f"Loaded from disk {steamid=}")
                        return Store.User.from_dict(data), age
                    except Exception as e:
                        logging.error(f"Error while loading from disk {steamid=}: {e}")
            
            logging.info(f"Fetching from SteamAPI {steamid=}")
            summary = next(UserAPI.fetchUserSummary(steamid), None)
            friends = UserAPI.fetchFriendList(steamid)

            if summary is None:
                logging.warning(f"Failed to fetch user\n{summary=}\n{friends=}")
                return None
            user = Store.User(
                steamid=steamid,
                friends_list=friends,
                user=summary
            )    
            tmp = cache_file.with_suffix(".json.tmp") # create a tmp file to ensure atomicity, - COMP207 -
            tmp.write_text(json.dumps(user.to_dict()))
            tmp.replace(cache_file)
            
            return user, timedelta(0)
        

    class Memory:

        @staticmethod
        def cache(key: str, obj: Store.User | Store.Game, db: redis.StrictRedis, age: timedelta) -> None:
            if isinstance(obj, Store.User):
                TTL = timedelta(minutes=USER_TTL) - age
            elif isinstance(obj, Store.Game):
                TTL = timedelta(hours=GAME_TTL) - age
            db.set(key, json.dumps(obj.to_dict()), TTL)

        @staticmethod
        def get(key: str, obj_type: Type[T], db: redis.StrictRedis) -> Optional[T]:
            if obj_type not in (Store.User, Store.Game):
                raise TypeError(f"Expected obj_type to be Store.User or Store.Game, got {obj_type!r}")

            data = db.get(key)
            if data is None:
                return None

            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                return None
            
            return obj_type.from_dict(obj)
                