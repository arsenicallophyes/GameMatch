import requests
import StorageStruct as Store
from typing import List, Tuple, Dict, Optional, Literal


class GameAPI:
    datasets = ("specials", "coming_soon", "top_sellers", "new_releases")

    @staticmethod    
    def fetchFeaturedCategories() -> set[Store.Game]:
        data: dict = requests.get("https://store.steampowered.com/api/featuredcategories").json()
        games: set[Store.Game] = set()
        for dataset in GameAPI.datasets:
            items: List[Dict] = data.get(dataset, {}).get("items", [])
            for item in items:
                # Info
                try:
                    app_id: str = int(item.get("id"))
                except ValueError:
                    continue
                game = GameAPI.fetchGameInfo(app_id)
                if game is not None and game is not False:
                    games.add(game)
        return games
    
    def fetchTrendingGameIDs() -> set[Store.AppID]:
        data: dict = requests.get("https://steamspy.com/api.php?request=top100in2weeks").json()
        if data:
            return set(data.keys())
        return set()
        
    
    @staticmethod
    def fetchGameInfo(app_id: int) -> Optional[Store.Game] | Literal[False]:
        # Data Requests
        try:
            game_request: dict = requests.get(f"https://store.steampowered.com/api/appdetails?appids={app_id}").json().get(str(app_id), {})
        except AttributeError:
            return False
        if game_request.get("success") is False:
            return None
        game_details: dict = game_request.get("data", {})
        app_review: dict = requests.get(f"https://store.steampowered.com/appreviews/{app_id}?json=1&filter=all").json()
        concurrent_plays: int = requests.get(f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={app_id}").json().get("response", {}).get("player_count", 0)
        steamspy_response: dict = requests.get(f"https://steamspy.com/api.php?request=appdetails&appid={app_id}").json()
        

        # Game Details
        name: str = game_details.get("name")
        developer: Optional[str] = steamspy_response.get("developer", None)
        owners: Optional[str] = steamspy_response.get("owners", None)
        tags : tuple = tuple() if type(steamspy_response.get("tags", {})) is not dict else tuple(steamspy_response.get("tags", {}).keys())
        languages: Optional[List] = steamspy_response.get("languages").split(",") if steamspy_response.get("languages") else None
        number_of_achievements: Optional[int] = int(game_details.get("achievements", {}).get("total")) if game_details.get("achievements", {}).get("total") else None
        categories: List = [i["description"] for i in game_details.get("categories", []) if i.get("description")]
        genres: List[str] = [item.get("description") for item in game_details.get("genres", [{}])]
        short_description: Optional[str] = game_details.get("short_description", None)
        long_description: Optional[str] = game_details.get("long_description", None)
        support_website: Optional[str] = game_details.get("url", None)
        support_email: Optional[str] = game_details.get("email", None)
        game_website: Optional[str] = game_details.get("website", None)
        header_image : Optional[str] = game_details.get("header_image", None)
        capsule_image : Optional[str] = game_details.get("capsule_image", None)
        capsule_image_v5 : Optional[str] = game_details.get("capsule_imagev5", None)

        # Reviews
        reviews_data: List[Tuple[str, float]] = []
        num_of_reviews: int = int(app_review.get("query_summary", {}).get("num_reviews", 0))
        review_score: int = int(app_review.get("query_summary", {}).get("review_score", 0))
        review_decription: Optional[str] = app_review.get("query_summary", {}).get("review_score_desc", None)
        positive_reviews: int = int(app_review.get("query_summary", {}).get("total_positive", 0))
        negative_reviews: int = int(app_review.get("query_summary", {}).get("total_negative", 0))
         
        for review_data in app_review.get("reviews", {}):
            if review_data.get("language") != "english":
                continue
            review: Optional[str] = review_data.get("review")
            weighted_scored: float = float(review_data.get("weighted_vote_score", 0))
            reviews_data.append((review, weighted_scored))

        # Platforms        
        windows: bool = game_details.get("platforms", {}).get("windows", False)
        mac: bool = game_details.get("platforms", {}).get("mac", False)
        linux: bool = game_details.get("platforms", {}).get("linux", False)
        controller: str = game_details.get("controller_support", "Unavailable")
        

        # Price
        is_free: bool = game_details.get("is_free")
        currency: str = game_details.get("price_overview", {}).get("currency")
        original_price: str = game_details.get("price_overview", {}).get("initial_formatted")
        final_price: str = game_details.get("price_overview", {}).get("final_formatted")
        discount_percent: int = game_details.get("price_overview", {}).get("discount_percent")

        # Storing
        reviews = Store.Reviews(num_of_reviews, review_score, review_decription, positive_reviews, negative_reviews, reviews_data)
        platforms = Store.Platforms(windows, mac, linux, controller)
        price = Store.Price(currency, original_price, final_price, discount_percent, is_free)
        images = Store.Image(header_image, capsule_image, capsule_image_v5)
        support = Store.Support(support_website, support_email, game_website)
        game = Store.Game(name=name, app_id=app_id, platforms=platforms, price=price, reviews=reviews, images=images, support=support, developer=developer, owners=owners, tags=tags, languages=languages, concurrent_plays=concurrent_plays, number_of_achievements=number_of_achievements, genres=genres, categories=categories, short_description=short_description, long_description=long_description)

        return game


if __name__ == "__main__":
    print(__file__)


