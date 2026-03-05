import json
import os
from collections import deque
from typing import Optional, Any, Dict


class RedisQueue:
    def __init__(self, queue_name: str = "default"):
        self._queue_name = queue_name
        self._redis = None
        self._fallback: deque = deque()
        self._use_fallback = True
        self._try_connect()

    def _try_connect(self):
        redis_url = os.environ.get("REDIS_URL")
        if not redis_url:
            self._use_fallback = True
            return
        try:
            import redis
            self._redis = redis.from_url(redis_url)
            self._redis.ping()
            self._use_fallback = False
        except Exception:
            self._use_fallback = True
            self._redis = None

    def enqueue(self, item: dict) -> bool:
        serialized = json.dumps(item, default=str)
        if self._use_fallback:
            self._fallback.append(serialized)
            return True
        try:
            self._redis.rpush(self._queue_name, serialized)
            return True
        except Exception:
            self._fallback.append(serialized)
            return True

    def dequeue(self) -> Optional[dict]:
        if self._use_fallback:
            if not self._fallback:
                return None
            return json.loads(self._fallback.popleft())
        try:
            item = self._redis.lpop(self._queue_name)
            if item is None:
                return None
            return json.loads(item)
        except Exception:
            if not self._fallback:
                return None
            return json.loads(self._fallback.popleft())

    def peek(self) -> Optional[dict]:
        if self._use_fallback:
            if not self._fallback:
                return None
            return json.loads(self._fallback[0])
        try:
            item = self._redis.lindex(self._queue_name, 0)
            if item is None:
                return None
            return json.loads(item)
        except Exception:
            if not self._fallback:
                return None
            return json.loads(self._fallback[0])

    def length(self) -> int:
        if self._use_fallback:
            return len(self._fallback)
        try:
            return self._redis.llen(self._queue_name)
        except Exception:
            return len(self._fallback)

    @property
    def is_using_fallback(self) -> bool:
        return self._use_fallback
