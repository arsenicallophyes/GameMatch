import pandas as pd
import numpy as np
import StorageAPI
from scipy.sparse.linalg import svds
from scipy.sparse import coo_matrix
import StorageStruct as Store
from typing import List, Dict, Tuple
import math
 
FG = Dict[Store.AppID, List[Store.SteamID]]
GI = Dict[Store.AppID, Store.UserGame]

class Algorithm:
    class SVD:
        def buildUtilityMatrix(self, users: List[Store.User], storage: StorageAPI.Storage):
            rows = []
            for user in users:
                for game_info in user.user.games_info:
                    data =  storage.getGame(game_info.app_id)
                    if data is None or data is False:
                        continue
                    game, fetched_from_api = data
                    playtime_per_genre =  game_info.playtime / max(len(game.genres), 1)
                    for genre in game.genres:
                        rows.append((user.steamid, genre, playtime_per_genre))

            df = pd.DataFrame(rows, columns=["steamid", "genre", "playtime"])
            pivot  =(df.groupby(["steamid", "genre"], as_index=False).playtime.sum().pivot(index="steamid",columns="genre",values="playtime").fillna(0))
            
            
            steam_ids = pivot.index.to_numpy()
            genres = pivot.columns.to_numpy()

            self.user_index: Dict[Store.SteamID, int] = {steamid: index for index, steamid in enumerate(steam_ids)}
            self.genre_index: Dict[str, int] = {genre: index for index, genre in enumerate(genres)}
            
            matrix = coo_matrix(pivot.to_numpy(dtype=np.float32)) 
            
            k = min(50, matrix.shape[0]-1, matrix.shape[1]-1)

            u, s, vt = svds(matrix, k=k)

            self.user_features = u.dot(np.diag(s))
            self.genre_features = vt.T 

        
        def predict_score(self, steamid: Store.SteamID, game: Store.Game) -> float | bool:
            user_index = self.user_index.get(steamid)
            if user_index is None: 
                return False
            
            vectors = []
            for genre in game.genres:
                genre_index = self.genre_index.get(genre)
                if genre_index:
                    vectors.append(self.genre_features[genre_index])
            
            if not len(vectors):
                return False
            
            game_vec = np.stack(vectors).mean(axis=0)

            return float(self.user_features[user_index].dot(game_vec))

    class WRS:

        PLAYTIME_WEIGHT = 2.5
        POPULARITY_WEIGHT = 5/3
        competitive = {"e-sports", "Competitive", "Action"}
        action_adventure = {"Action-Adventure"}
        open_world = {"Open World"}
        @staticmethod
        def gatherData(user: Store.User, storage: StorageAPI.Storage) -> Tuple[List[Store.Game], GI, FG]:
            games_info: GI = {}
            games: Dict[Store.AppID, Store.Game] = {}
            friends_games: FG = {}
            for fr in user.friends_list:
                fr_games_info_only = fr.games_info.difference(user.user.games_info) # Remove user owned games from the friend's game list
                for gi in fr_games_info_only:
                    # Only APPID is considered, playtime cannot be fetched reliably due to the user's privacy settings.
                    
                    data = storage.getGame(gi.app_id)
                    if data is None:
                        continue
                    if data is False:
                        return False
                    game, fetched_from_api = data
                    games[game.app_id] = game
                    games_info[gi.app_id] = gi
                    friends_games.setdefault(gi.app_id, []).append(fr.steamid)
            
            return games, games_info, friends_games
        
        @staticmethod
        def calculateGamesScore(games: Dict[Store.AppID, Store.Game], games_info: GI, friends_games: FG, friends_recs: Dict[Store.AppID, List[Store.SteamID]]) -> Tuple[Dict[Store.AppID, Tuple[int, float, Tuple[int, int, int, int]]], List[Store.AppID], List[Store.AppID], List[Store.AppID], List[Store.AppID]]:
            WRS_scores: Dict[Store.AppID, Tuple[int, float, Tuple[int, float, int, float]]] = {}
            for app_id, friend_ids in friends_recs.items():
                game = games.get(app_id)
                if game is None:
                    continue
                average_playtime = (result.playtime if (result:=games_info.get(app_id)) and result.playtime else 1) / len(friend_ids)
                concurrent_players: int = max(1, game.concurrent_plays)

                friends_score: float = min(10, len(friends_games.get(game.app_id, [])) / 2) # 0.5 poinst for each friend, capped at 10

                playtime_score: float = min(10, math.log10(average_playtime) * Algorithm.WRS.PLAYTIME_WEIGHT) # log of playtime to prevent high-playtime games from dominating short-playtime games

                review_score: int = min(10, game.reviews.review_score / 10)

                popularity_score: float = min(10, math.log10(concurrent_players) * Algorithm.WRS.POPULARITY_WEIGHT)
                
                scores = (friends_score, playtime_score, review_score, popularity_score)
                total = sum(scores)
                match_precentage = round(total / 40 * 100)


                WRS_scores[game.app_id] = (match_precentage, average_playtime, tuple( map(lambda x: round(x / total * 100), scores )) )
            sorted_scores = sorted(list(WRS_scores.items()), key=lambda x: int(x[0]))
            WRS_scores = {}
            top_picks: List[Store.AppID] = list(app_id for app_id, _ in sorted_scores[:10])
            competitive_games: List[Store.AppID] = []
            adventure_action: List[Store.AppID] = []
            open_world: List[Store.AppID] = []
            for app_id, data in sorted_scores:
                WRS_scores[app_id] = data
                game = games.get(app_id)
                tags = set(game.genres + game.categories + list(game.tags))
                if {"Action"} & tags:
                    if tags & Algorithm.WRS.competitive:
                        competitive_games.append(app_id)
                    elif {"Adventure"} & tags:
                        adventure_action.append(app_id)
                elif {"Action-Adventure"} & tags:
                    adventure_action.append(app_id)
                elif {"Adventure"} & tags:
                    if Algorithm.WRS.open_world & tags:
                        open_world.append(app_id)
            
                

            WRS_scores = {app_id: data for app_id, data in sorted_scores}
            return WRS_scores, top_picks[:10], competitive_games[:10], adventure_action[:10], open_world[:10]
