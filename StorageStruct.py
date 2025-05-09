from dataclasses import dataclass, asdict
from typing import List, Any, Optional, Tuple, Dict, NewType
AppID = NewType('AppID', int)
SteamID = NewType('SteamID', int)

@dataclass
class Platforms:
    windows: bool
    mac: bool
    linux: bool
    controller: str

    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class Price:
    currency: str
    original_price: str
    final_price: str
    discount_percent: int
    is_free: bool

    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class Reviews:
    num_of_reviews: int
    review_score: int
    review_decription: Optional[str]
    positive_reviews: int
    negative_reviews: int
    reviews: List[Tuple[str, float]]

    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class Support:
    support_website: Optional[str]
    support_email: Optional[str]
    game_website: Optional[str]

    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class Image:
    header_image : Optional[str]
    capsule_image : Optional[str]
    capsule_image_v5 : Optional[str]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Game:
    name: str
    app_id: int
    
    platforms: Platforms
    price: Price
    reviews: Reviews
    images: Image
    support: Support

    developer: Optional[str]
    owners: Optional[str]
    tags: tuple
    languages: Optional[List]
    concurrent_plays: int
    number_of_achievements: Optional[int]
    categories: List
    genres: List[str]
    short_description: Optional[str]
    long_description: Optional[str]

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Game):
            return NotImplemented
        return self.app_id == other.app_id

    def __hash__(self) -> int:
        return hash(self.app_id)

    def to_dict(self) -> Dict:
        data = asdict(self)
        data['tags'] = list(self.tags) # JSON doesn't support tuples, convert it to a list first
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Game":
        return cls(
            name= data["name"],
            app_id = data["app_id"],
            platforms = Platforms(**data["platforms"]),
            price = Price(**data["price"]),
            reviews = Reviews(**data["reviews"]),
            images = Image(**data["images"]),
            support= Support(**data["support"]),
            developer= data.get("developer"),
            owners = data.get("owners"),
            tags = tuple(data.get("tags", [])),
            languages = data.get("languages"),
            concurrent_plays = data.get("concurrent_plays", 0),
            number_of_achievements = data.get("number_of_achievements"),
            categories = data.get("categories", []),
            genres = data.get("genres", []),
            short_description= data.get("short_description"),
            long_description = data.get("long_description"),
        )



@dataclass
class Avatars:
    avatar: str
    avatarmedium: str
    avatarfull: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class UserGame:
    app_id: AppID
    playtime: int
    img_icon_url: str
    last_played: int

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, UserGame):
            return NotImplemented
        return self.app_id == other.app_id

    def __hash__(self) -> int:
        return hash(self.app_id)

    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class UserInfo:
    steamid: SteamID
    username : str
    profile_url: str
    avatars: Avatars
    personastate: str
    timecreated: int
    lastlogoff: int
    games_info: set[UserGame]

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, UserInfo):
            return NotImplemented
        return self.steamid == other.steamid

    def __hash__(self) -> int:
        return hash(self.steamid)

    def to_dict(self) -> Dict:
        return {
            "steamid":self.steamid,
            "username": self.username,
            "profile_url": self.profile_url,
            "avatars": self.avatars.to_dict(),
            "personastate": self.personastate,
            "timecreated": self.timecreated,
            "lastlogoff": self.lastlogoff,
            "games_info":  [game.to_dict() for game in self.games_info],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserInfo":
        return cls(
            steamid= data["steamid"],
            username= data["username"],
            profile_url = data["profile_url"],
            avatars=Avatars(**data["avatars"]),
            personastate=data["personastate"],
            timecreated= data["timecreated"],
            lastlogoff= data["lastlogoff"],
            games_info={UserGame(**usergame) for usergame in data["games_info"]}
            )


@dataclass
class User:
    steamid: SteamID
    friends_list : set[UserInfo]
    user: UserInfo

    def to_dict(self) -> Dict:
        return {
            "steamid": self.steamid,
            "friends_list": [frnd.to_dict() for frnd in self.friends_list],
            "user": self.user.to_dict(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        return cls(
            steamid=data["steamid"],
            friends_list= {UserInfo.from_dict(friend) for friend in data["friends_list"]},
            user= UserInfo.from_dict(data["user"])
        )
    