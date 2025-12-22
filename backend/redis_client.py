import os
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class RedisClient:
    def __init__(self):
        self.redis = None

    async def connect(self):
        self.redis = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        print("Redis Connected.")

    async def close(self):
        if self.redis:
            await self.redis.close()
            print("Redis Closed.")

    def get_client(self):
        return self.redis

# Global instance
redis_client = RedisClient()
