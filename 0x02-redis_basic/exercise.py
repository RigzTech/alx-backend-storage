ient"""

import redis
import uuid
from typing import Union, Callable, Optional, Any, ValuesView
from functools import wraps


def call_history(method: Callable) -> Callable:
    """ store the history of inputs and outputs for a particular function """
    key = method.__qualname__
    inputs = key + ":inputs"
    outputs = key + ":outputs"

    @wraps(method)
    def wrapper(self, *args, **kwds):
        """ wrapped function """
        self._redis.rpush(inputs, str(args))
        data = method(self, *args, **kwds)
        self._redis.rpush(outputs, str(data))
        return data
    return wrapper


def count_calls(method: Callable) -> Callable:
    """ takes a single method Callable argument and
    returns a Callable. and count how many times methods of
    the Cache class are called."""
    key = method.__qualname__

    @wraps(method)
    def wrapper(self, *args, **kwds):
        """ wrapped function to access the Redis instance."""
        self._redis.incr(key)
        return method(self, *args, **kwds)
    return wrapper


class Cache:
    """class"""
    def __init__(self):
        """store an instance"""
        self._redis = redis.Redis()
        self._redis.flushdb()

    @call_history
    @count_calls
    def store(self, data: Union[str, int, float, bytes]) -> str:
        """ generate random key """
        key = str(uuid.uuid4())
        self._redis.set(key, data)
        return key

    def get(self, key: str,
            fn: Optional[Callable] = None) -> Union[str, bytes, int, float]:
        """ takes a key string argument and an optional Callable argument
        named fn. This callable will be used to convert the data back
        to the desired format."""
        data = self._redis.get(key)
        if fn:
            return fn(data)
        return data

    def get_str(self, key: str) -> str:
        """automatically parametrize Cache.get with the correct
        conversion function str format"""
        data = self._redis.get(key)
        return data.decode("utf-8")

    def get_int(self, key: str) -> int:
        """automatically parametrize Cache.get with the correct
        conversion function int format"""
        data = self._redis.get(key)
        try:
            data = int(ValuesView.decode("utf-8"))
        except Exception:
            data = 0
        return data


def replay(method: Callable):
    """ display the history of calls of a particular function """
    key = method.__qualname__
    inputs = key + ":inputs"
    outputs = key + ":outputs"
    redis = method.__self__._redis
    count = redis.get(key).decode("utf-8")
    print("{} was called {} times:".format(key, count))
    inputList = redis.lrange(inputs, 0, -1)
    outputList = redis.lrange(outputs, 0, -1)
    redis_zipped = list(zip(inputList, outputList))
    for a, b in redis_zipped:
        attr, data = a.decode("utf-8"), b.decode("utf-8")
        print("{}(*{}) -> {}".format(key, attr, data))
