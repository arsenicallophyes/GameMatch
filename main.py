from flask import Flask, redirect, url_for, render_template, request, session, jsonify
from SteamAuth import SteamAuth
import StorageAPI
from GameAPI import GameAPI
import StorageStruct as Store
from SmartEngine import Algorithm
from flask_session import Session # Flask_session is used to simplify the redis-session integration
import os, redis
from datetime import datetime
from openid.consumer.consumer import Consumer, SUCCESS
from typing import List, Dict, Tuple
os.chdir(os.path.dirname(__file__))
import math


app = Flask(__name__)
app.secret_key =  os.environ["SECRET_KEY"]
# app.permanent_session_lifetime = timedelta(minutes=30)

app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = redis.StrictRedis(host="localhost",port=6379, db=0)
Session(app)

user_data_redis = redis.StrictRedis(host="localhost", port=6379, db=1)
game_data_redis = redis.StrictRedis(host="localhost", port=6379, db=2)

# user_data_redis.flushdb()
# game_data_redis.flushdb()

steam_auth = SteamAuth()
store = steam_auth.openid_store
storage = StorageAPI.Storage(user_data_redis, game_data_redis)

svd = Algorithm.SVD()

@app.route("/home")
def home():
    steamid: Store.SteamID = session.get('steamid')
    if steamid:
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/")
def baseURL():
    steamid: Store.SteamID = session.get('steamid')
    if steamid:
        return redirect(url_for("dashboard"))
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    if "steamid" in session:
        session.pop("steamid")
    if "SVD" in session:
        session.pop("SVD")
    return redirect(url_for("home"))

@app.route("/library")
def library():
    steamid: Store.SteamID = session.get('steamid')
    if not steamid:
        return redirect(url_for("logout"))
    
    user = storage.getUser(steamid)

    if user is None:
        return render_template("error.html", CODE=500, MESSAGE="Failed to fetch user info." )
    
    user_info = user.user
    games: List[Store.Game] = []

    OWNED_GAMES = len(user_info.games_info)
    TOTAL_PLAYTIME = 0
    GAMES_PLAYED = 0
    games_info: Dict[Store.AppID, Store.UserGame] = {}
    for gi in user_info.games_info:
        if gi.playtime:
            GAMES_PLAYED += 1
            TOTAL_PLAYTIME += gi.playtime
        data = storage.getGame(gi.app_id)
        if data is None:
            continue
        if data is False:
            return jsonify("Too many requests"), 429
        game, fetched_from_api = data
        games.append(game)
        games_info[gi.app_id] = gi

    TOTAL_PLAYTIME = format_playtime(TOTAL_PLAYTIME)
    
    
    return render_template("library.html", OWNED_GAMES=OWNED_GAMES, USERNAME=user_info.username, TOTAL_PLAYTIME=TOTAL_PLAYTIME, STEAMID=user.steamid, games=games, games_info=games_info, AVATAR_MEDIUM=user_info.avatars.avatarmedium)
    



@app.route("/dashboard")
def dashboard():
    steamid: Store.SteamID = session.get('steamid')
    if not steamid:
        return redirect(url_for("logout"))
    
    user = storage.getUser(steamid)

    if user is None:
        return render_template("error.html", CODE=500, MESSAGE="Failed to fetch user info." )
    
    user_info = user.user
    calculateSVDScore(user, steamid)    

    return render_template("dashboard.html", AVATAR_MEDIUM=user_info.avatars.avatarmedium, USERNAME=user_info.username, STEAMID=user_info.steamid)

@app.route("/profile")
def profile():
    steamid: Store.SteamID = session.get('steamid')
    if not steamid:
        return redirect(url_for("logout"))
    
    user = storage.getUser(steamid)

    if user is None:
        return render_template("error.html", CODE=500, MESSAGE="Failed to fetch user info." )
    
    user_info = user.user

    DATE_CREATED = datetime.fromtimestamp(user_info.timecreated).date() if user_info.timecreated else "N/A"
    LASTLOGOFF = datetime.fromtimestamp(user_info.lastlogoff) if user_info.lastlogoff else "N/A"
    OWNED_GAMES = len(user_info.games_info)
    TOTAL_PLAYTIME = 0
    GAMES_PLAYED = 0
    for game in user_info.games_info:
        if game.playtime:
            GAMES_PLAYED += 1
            TOTAL_PLAYTIME += game.playtime
    NUM_FRIENDS = len(user.friends_list)

    TOTAL_PLAYTIME = format_playtime(TOTAL_PLAYTIME)
    

    return render_template(
        "profile.html", 
        AVATAR_FULL=user_info.avatars.avatarfull, 
        USERNAME=user_info.username, 
        STEAMID=user_info.steamid, 
        DATE_CREATED=DATE_CREATED,
        LASTLOGOFF=LASTLOGOFF,
        OWNED_GAMES=OWNED_GAMES,
        GAMES_PLAYED=GAMES_PLAYED,
        TOTAL_PLAYTIME=TOTAL_PLAYTIME,
        NUM_FRIENDS=NUM_FRIENDS
        )

@app.template_filter('format_playtime')
def format_playtime(total_minutes: int) -> str:
    days, remainder = divmod(total_minutes, 1440)
    hours, minutes = divmod(remainder, 60)
    hours = int(hours)
    minutes = int(minutes)
    days = int(days)
    if days:
        return f"{days} {"day" if days == 1 else "days"} and {hours} {"hour" if hours == 1 else "hours"}"
    elif hours:
        return f"{hours} {"hour" if hours == 1 else "hours"} and {minutes} {"min" if minutes == 1 else "mins"}"
    else:
        return f"{minutes} {"min" if minutes == 1 else "mins"}"
        

@app.template_filter('time_since')
def time_since(last_layed: int) -> str:
    if last_layed == 0:
        return "Never"
    now = datetime.now()
    past = datetime.fromtimestamp(last_layed)
    diff = now - past
    seconds = int(diff.total_seconds())

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes or 1} minute{'s' if minutes != 1 else ''} ago"

    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

    days = hours // 24
    if days < 7:
        return f"{days} day{'s' if days != 1 else ''} ago"

    weeks = days // 7
    if weeks < 4:
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"

    months = days // 30
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''} ago"

    years = days // 365
    return f"{years} year{'s' if years != 1 else ''} ago"

@app.route("/fetch-user-games")
def fetchUserGames():
    steamid: Store.SteamID = session.get('steamid')
    limit = request.args.get('limit', type=int)

    if not steamid:
        return jsonify(error="Not logged in"), 401
    
    user = storage.getUser(steamid)

    played = sorted(user.user.games_info, key=lambda x: x.last_played, reverse=True)
    if limit:
        played = played[:limit]
    games_data: List[Dict] = []
    games_info = {}
    for gi in played:
        data = storage.getGame(gi.app_id)
        if data is None:
            continue
        if data is False:
            return jsonify("Too many requests"), 429
        game, fetched_from_api = data
        games_info[gi.app_id] = gi.to_dict()
        games_data.append(game.to_dict())

    data = {
    "count": len(games_info),
    "games_info": games_info,
    "games_data": games_data
    }

    return jsonify(data)

@app.route("/fetch-friend-games")
def fetchFriendGames():
    steamid: Store.SteamID = session.get('steamid')
    limit = request.args.get('limit', type=int)

    if not steamid:
        return jsonify(error="Not logged in"), 401
    
    user = storage.getUser(steamid)
    
    user_games_info = {gi.app_id: gi.to_dict() for gi in user.user.games_info}
    friends_games = getFriendGames(user.friends_list, limit)
    games_data = {app_id: storage.getGame(app_id)[0].to_dict() for app_id in friends_games.keys()}

    data = {
    "count": len(friends_games),
    "friends_games": friends_games,
    "games_data": games_data,
    "user_games_info": user_games_info
    }
    return jsonify(data)

@app.route("/fetch-recommendations")
def fetchSVDRecommendations():
    steamid: Store.SteamID = session.get('steamid')
    limit = request.args.get('limit', type=int)

    if not steamid:
        return jsonify(error="Not logged in"), 401
    
    user = storage.getUser(steamid)

    if user is None :
        return jsonify(error="Couldn't fetch user info"), 401 
        
    if (result := getTrendingGames(user, steamid)):
        trending_game_ids = result
    else:
        return jsonify({"count": 0}), 402

    if session.get("SVD", None) is None:
        return jsonify({"count": 0,}), 402
    max_score = session.get("SVD")[0]

    sorted_scores = getSVDScores(steamid, trending_game_ids, max_score, limit)

    
    games_data = {app_id: storage.getGame(app_id)[0].to_dict() for app_id, score in sorted_scores}
    data = {"count": len(games_data), "games_data": games_data, "scores": sorted_scores }
    return jsonify(data)


def getTrendingGames(user: Store.User, steamid: Store.SteamID) -> set[Store.AppID] | bool:
    fetched_from_api = False
    trending_game_ids: set[Store.AppID] = GameAPI.fetchTrendingGameIDs()
    for app_id in trending_game_ids:
        data = storage.getGame(app_id)
        game, api_status = data
        if api_status:
            fetched_from_api = True
    
    if fetched_from_api:
        if not calculateSVDScore(user, steamid):
            return False
    
    return trending_game_ids

def getSVDScores(steamid: Store.SteamID, trending_game_ids: set[Store.AppID], max_score: float, limit: int=False) -> Dict[Store.AppID, int]:
    scores: Dict[Store.AppID, int] = {}
    for app_id in trending_game_ids:
        data = storage.getGame(app_id)
        if data is None or data is False:
            continue
        game, fetched_from_api = data
        scores[app_id] = round((svd.predict_score(steamid, game)/max_score) * 100)

    sorted_scores = sorted(list(scores.items()), key=lambda x: x[1], reverse=True)
    if limit:
        sorted_scores = sorted_scores[:limit]

    
    return sorted_scores

def getFriendGames(friends_list: set[Store.UserInfo], limit: int=False) -> Dict[Store.AppID, List[Store.SteamID]]:
    friends_games = calculateFriendGames(friends_list)

    sorted_frg: Tuple[Store.AppID, List[Store.SteamID]] = sorted(friends_games.items(), key = lambda kv: len(kv[1]), reverse=True)
    if limit:
        sorted_frg = sorted_frg[:limit]
    friend_games: Dict[Store.AppID, List[Store.SteamID]] = {app_id: steamids for app_id, steamids in sorted_frg}
    return friend_games

@app.route("/recommendations")
def recommendations():
    steamid: Store.SteamID = session.get('steamid')
    if not steamid:
        return redirect(url_for("logout"))
    
    user = storage.getUser(steamid)

    if user is None:
        return render_template("error.html", CODE=500, MESSAGE="Failed to fetch user info." )
    
    if (result := getTrendingGames(user, steamid)):
        trending_game_ids = result
    else:
        return jsonify({"count": 0}), 402

    if session.get("SVD", None) is None:
        return jsonify({"count": 0,}), 402
    max_score = session.get("SVD")[0]
    
    friends_recs = getFriendGames(user.friends_list)
    WRS_scores, top_picks, competitive_games, adventure_action, open_world = Algorithm.WRS.calculateGamesScore(*Algorithm.WRS.gatherData(user, storage), friends_recs)
    SVD_scores = getSVDScores(steamid, trending_game_ids, max_score, 40)
    sections = (("Top Picks for You", top_picks, "star"), ("Action-Packed Adventures", adventure_action, "lightning"), ("Open World Explorations", open_world, "globe"), ("Competitive Multiplayer", competitive_games, "trophy"))
    recently_played = tuple(app.app_id for app in sorted(user.user.games_info, key=lambda x: x.last_played, reverse=True))
    return render_template("recommendations.html",
        SVD_scores=SVD_scores,
        WRS_scores=WRS_scores,
        friends_recs=friends_recs,
        friend_dict={friend.steamid: (friend.avatars.avatarmedium, friend.username) for friend in user.friends_list},
        recently_played=recently_played,
        AVATAR_MEDIUM=user.user.avatars.avatarmedium,
        USERNAME=user.user.username,
        sections=sections,
        trending_games_ids=trending_game_ids
    )


@app.template_filter("fetchGame")
def fetchGame(app_id: Store.AppID):
    data = storage.getGame(app_id)
    if data is None or data is False:
        return False
    return data[0]

@app.template_filter("activePlayerBase")
def activePlayerBase(game: Store.Game):
    game.concurrent_plays
    if game.owners:
        owners_range = list(map(int, game.owners.replace(",","").replace(" ","").split("..")))
        avg_owners = sum(owners_range) / 2
        return f"{game.concurrent_plays / max(1, math.sqrt(game.concurrent_plays) * math.sqrt(avg_owners)) * 100:.1f}"
    return "N/A"

def calculateSVDScore(user: Store.User, steamid: Store.SteamID) -> bool:
    all_users = storage.get_all_users()
    if len(all_users) < 2:
        return False
    
    svd.buildUtilityMatrix(all_users, storage)
    app_id = 0
    max_score = 0
    for game_info in user.user.games_info:
            data = storage.getGame(game_info.app_id)
            if data is None or data is False:
                continue
            game, fetched_from_api = data
            score = svd.predict_score(steamid, game)
            if max_score < score:
                max_score = score
                app_id = game_info.app_id
    if not app_id:
        return False
    
    session["SVD"] = (max_score, app_id)
    return True

def calculateFriendGames(friends: set[Store.UserInfo]) -> Dict[Store.AppID, List[Store.SteamID]]:
    friends_games: Dict[Store.AppID, List[Store.SteamID]] = {}
    for fr in friends:
        for gi in fr.games_info:
            data = storage.getGame(gi.app_id)
            if data is None:
                continue
            if data is False:
                return jsonify("Too many requests"), 429
            
            friends_games.setdefault(gi.app_id, []).append(fr.steamid)
    
    return friends_games

@app.route('/authorize')
def authorize():
    consumer = Consumer({}, store)
    response = consumer.complete(dict(request.args), request.url)

    if response.status == SUCCESS:
        steamid = steam_auth.get_steamid(response.getDisplayIdentifier())
        session['steamid'] = Store.SteamID(steamid)
        return redirect(url_for('home'))
    return 'Steam login failed!'

@app.route("/login")
def login():
    consumer = Consumer({}, store)
    auth_request = consumer.begin(SteamAuth.STEAM_OPENID_URL)
    return redirect(auth_request.redirectURL(realm=request.url_root, return_to=url_for('authorize', _external=True)))

if __name__ == "__main__":
    all_users = storage.get_all_users()
    if len(all_users) >= 2:
        svd.buildUtilityMatrix(all_users, storage)
    
    app.run("localhost", port=8000)