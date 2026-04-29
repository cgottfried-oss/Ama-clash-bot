from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import aiohttp


class ClashApiClient:
    def __init__(
        self,
        *,
        api_key: str,
        safe_load_json,
        safe_save_json,
        cache_file: str,
        cache_limit: int = 100,
    ):
        self.api_key = api_key
        self.safe_load_json = safe_load_json
        self.safe_save_json = safe_save_json
        self.cache_file = cache_file
        self.cache_limit = cache_limit

        self.session: aiohttp.ClientSession | None = None
        self.api_cache: dict[str, dict[str, Any]] = {}

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None

    async def load_cache(self):
        data = await self.safe_load_json(self.cache_file)
        self.api_cache = data if isinstance(data, dict) else {}
        return self.api_cache

    async def save_cache(self):
        await self.safe_save_json(self.cache_file, self.api_cache)

    async def fetch_json(self, url: str, retries: int = 3):
        sess = await self.get_session()

        for attempt in range(retries):
            try:
                async with sess.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()

                    if response.status == 429:
                        print("[CLASH API] Rate limited. Sleeping...", flush=True)
                        await asyncio.sleep(5)
                    else:
                        print(f"[CLASH API] HTTP {response.status} for {url}", flush=True)
                        return None

            except asyncio.TimeoutError:
                print(f"[CLASH API] Timeout attempt {attempt + 1}/{retries}", flush=True)

            except aiohttp.ClientError as exc:
                print(f"[CLASH API] ClientError: {exc}", flush=True)

            await asyncio.sleep(2)

        print(f"[CLASH API] Failed to fetch {url}", flush=True)
        return None

    async def get_cached_or_fetch(self, key: str, url: str, ttl: int = 120):
        now = datetime.now(timezone.utc).timestamp()

        if key in self.api_cache:
            entry = self.api_cache[key]
            if now - entry.get("timestamp", 0) < ttl:
                return entry.get("data")

        try:
            data = await asyncio.wait_for(self.fetch_json(url), timeout=10)
        except asyncio.TimeoutError:
            print(f"[CLASH API CACHE] Timeout. Using stale data for {key}", flush=True)
            return self.api_cache.get(key, {}).get("data")

        if data is not None:
            self.api_cache[key] = {
                "timestamp": now,
                "ttl": ttl,
                "data": data,
            }

            if len(self.api_cache) > self.cache_limit:
                self.api_cache = dict(
                    sorted(
                        self.api_cache.items(),
                        key=lambda item: item[1].get("timestamp", 0),
                        reverse=True,
                    )[: self.cache_limit]
                )

            await self.save_cache()

        return data

    async def fetch_clan_data(self, clan_tag: str):
        encoded_tag = clan_tag.replace("#", "%23")

        war_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/currentwar"
        members_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/members"

        cache_suffix = clan_tag.replace("#", "")

        war, members_json = await asyncio.gather(
            self.get_cached_or_fetch(f"war_{cache_suffix}", war_url, ttl=60),
            self.get_cached_or_fetch(f"members_{cache_suffix}", members_url, ttl=300),
        )

        if not members_json:
            print(f"⚠️ Member fetch failed for {clan_tag}", flush=True)
            return war, []

        return war, members_json.get("items", [])