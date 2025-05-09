from openid.store.memstore import MemoryStore
from StorageStruct import SteamID
from typing import Optional
import re

class SteamAuth:
    STEAM_OPENID_URL = "https://steamcommunity.com/openid/"

    def __init__(self):
        self.openid_store = MemoryStore()

    def get_steamid(self, url) -> Optional[SteamID]:
        steamid = re.search(rf'{self.STEAM_OPENID_URL}id/(\d+)', url).group(1)
        return steamid if steamid else None
