cache = {}


def set_cache(key, value):
    cache[key] = value


def get_cache(key):
    return cache.get(key)


def clear_cache():
    global cache
    cache = {}
