from aiocache import caches


def setup_cache():
    caches.set_config(
        {
            "default": {
                "cache": "aiocache.SimpleMemoryCache",
                "serializer": {"class": "aiocache.serializers.PickleSerializer"},
                "ttl": 600,  # 10 minutes default TTL
            }
        }
    )
