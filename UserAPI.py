import requests, os, logging
import StorageStruct as Store
from typing import List, Tuple, Dict, Iterator, Optional, Any

API_KEY = os.environ["STEAM_API_KEY"] 

def _get_json(url: str, default: Any=None):
    try:
        req = requests.get(url)
        req.raise_for_status()
        return req.json()
    except:
        return default

friend_url = f"http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key={API_KEY}&steamid="
user_url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={API_KEY}&steamids="
owned_games_url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={API_KEY}&steamid="

class UserAPI:
    
    @staticmethod
    def fetchFriendList(steamid: int) -> set[Store.UserInfo]:
        data: dict = _get_json(rf"{friend_url}{steamid}&relationship=friend", {})
        friends: dict = data.get("friendslist", {}).get("friends", [])        
        
        ids: set[int] = set()
        ids.update(int(friend.get("steamid")) for friend in friends if isinstance(friend, dict) and friend.get("steamid") and friend.get("steamid").isdigit())
        return {user for chunk in UserAPI._ids_chunks(ids) for user in UserAPI.fetchUserSummary(chunk, chunk=True)}

    @staticmethod
    def fetchUserSummary(steamids: int | Tuple[int, ...], chunk: bool=False) -> Iterator[Store.UserInfo]:
        if chunk:
            steamids = ",".join(map(str, steamids))
        response = requests.get(fr"{user_url}{steamids}")            
        try:
            if response.status_code == 429:
                raise requests.RequestException
            player_summaries: List[Dict] = response.json().get("response", {}).get("players", [])
        except (ValueError, TypeError, IndexError, requests.RequestException) as e:
            if e is requests.RequestException:
                logging.warning(f"429 Too Many Requests: Failed to fetch user: {user_url}{steamids}")
            else:
                logging.warning(f"Failed to fetch user: {user_url}{steamids}\n{e}")
            return iter(())
        for player_summary in player_summaries:
            steamid = result if (result:= player_summary.get("steamid")) else None
            games_info = UserAPI.fetchUserGames(steamid) if steamid else None
            username = result if (result:= player_summary.get("personaname")) else None
            profile_url = result if (result:= player_summary.get("profileurl")) else None
            personastate = result if (result:= player_summary.get("personastate")) else None
            timecreated = result if (result:= player_summary.get("timecreated")) else None
            lastlogoff = result if (result:= player_summary.get("lastlogoff")) else None

            avatar = result if (result:= player_summary.get("avatar")) else None
            avatarmedium = result if (result:= player_summary.get("avatarmedium")) else None
            avatarfull = result if (result:= player_summary.get("avatarfull")) else None

            avatars = Store.Avatars(avatar, avatarmedium, avatarfull)

            user = Store.UserInfo(steamid=steamid, username=username, profile_url=profile_url,avatars=avatars, personastate=personastate, timecreated=timecreated, lastlogoff=lastlogoff, games_info=games_info)
            yield user

    def _ids_chunks(ids: set[int]) -> Iterator[List[int]]:
        ids_list = tuple(ids)
        yield ids_list[:99]

        for i in range(99, len(ids_list), 100):
            yield ids_list[i:i + 100]
    
    @staticmethod
    def fetchUserGames(steamid: Store.SteamID) -> set[Store.UserGame]:
        try:
            owned_games: List[Dict] = requests.get(fr"{owned_games_url}{steamid}&format=json&include_appinfo=true").json().get("response", {}).get("games", [])
        except (ValueError, TypeError) as e:
            return set()
        
        user_games_info: set[Store.UserGame] = set()

        for game in owned_games:
            app_id = result if (result:= game.get("appid")) else None
            if not app_id:
                continue
            playtime = result if (result:= game.get("playtime_forever")) else 0
            img_icon_url = result if (result:= game.get("img_icon_url")) else ""
            last_played = result if (result:= game.get("rtime_last_played")) else 0

            user_game_info = Store.UserGame(app_id, playtime, img_icon_url, last_played)

            user_games_info.add(user_game_info)
        return user_games_info

    @staticmethod
    def verifyUserGameID(app_id: Store.AppID) -> Optional[bool]:
        try:
            game_request: dict = requests.get(f"https://store.steampowered.com/api/appdetails?appids={app_id}").json().get(str(app_id), {})
            if game_request.get("success") is False:
                return None # Appid invalid or no game details
        except AttributeError:
            return False # Error 429, too many requests
        return True # game is valid
            
    

if __name__ == "__main__":
    print(__file__)