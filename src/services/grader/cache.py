import json
import hashlib
import logging
from src.config import REDIS_HOST, REDIS_PORT, REDIS_DB, CACHE_TTL

logger = logging.getLogger(__name__)

try:
    import redis
    redis_available = True
except ImportError:
    redis_available = False


class GradingCache:
    def __init__(self):
        self.client = None
        if redis_available:
            try:
                self.client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    decode_responses=True
                )
                self.client.ping()
            except Exception as e:
                logger.warning(f"Redis连接失败，缓存不可用: {e}")
                self.client = None

    def _make_key(self, pid: str, qid: str, answer: str) -> str:
        content = f"{pid}:{qid}:{answer}"
        return "grader:" + hashlib.sha256(content.encode()).hexdigest()

    def get(self, pid: str, qid: str, answer: str):
        if not self.client:
            return None
        try:
            key = self._make_key(pid, qid, answer)
            cached = self.client.get(key)
            return json.loads(cached) if cached else None
        except Exception as e:
            logger.warning(f"缓存读取失败: {e}")
            return None

    def set(self, pid: str, qid: str, answer: str, result: dict):
        if not self.client:
            return
        try:
            key = self._make_key(pid, qid, answer)
            self.client.setex(key, CACHE_TTL, json.dumps(result))
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")

    def invalidate(self, pid: str, qid: str):
        if not self.client:
            return
        try:
            pattern = f"grader:*:{pid}:{qid}:*"
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
        except Exception as e:
            logger.warning(f"缓存清除失败: {e}")


grader_cache = GradingCache()
