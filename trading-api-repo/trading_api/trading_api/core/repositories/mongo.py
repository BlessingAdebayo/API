import logging
import time
from abc import ABC
from contextlib import contextmanager
from decimal import Decimal
from typing import Any, Callable, Iterator, List, Optional, Tuple

from bson.codec_options import CodecOptions, TypeEncoder, TypeRegistry
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import AutoReconnect
from pymongo.errors import ConnectionFailure as MongoConnectionFailure

logger = logging.getLogger(__name__)


def connect_mongo(mongo_connection_str: str) -> MongoClient:
    logger.debug("Connecting to mongo...")

    client = MongoClient(mongo_connection_str, maxPoolSize=300)

    logger.debug(f"Connected to mongo.")

    return client


@contextmanager
def managed_mongo(mongo_connection_str: str) -> MongoClient:
    mongo = connect_mongo(mongo_connection_str)
    try:
        yield mongo
    finally:
        mongo.close()


def mongodb_retry(function: Callable, max_attempts: int = 5):
    """A decorator that automatically tries to retry the given function `max_attempts` times,
     if PyMongo loses its connection to the MongoDB database.

    @param function: Function to execute N times
    @param max_attempts: N maximum attempts at the function before raising the PyMongo exception.
    @return:
    """

    def wrapper(*args, **kwargs):
        for attempt_nr in range(max_attempts):
            try:
                return function(*args, **kwargs)
            except AutoReconnect as exception:
                if attempt_nr == max_attempts - 1:
                    raise exception

                wait_t = 0.5 * pow(2, attempt_nr + 1)  # exponential back off
                logger.warning("PyMongo auto-reconnecting... %s. Waiting %.1f seconds.", str(exception), wait_t)
                time.sleep(wait_t)

    return wrapper


class DecimalCodec(TypeEncoder):
    python_type = Decimal  # the Python type acted upon by this type codec

    def transform_python(self, value: Decimal):
        """Function that transforms a custom type value into a type
        that BSON can encode."""
        return str(value)


def type_registry():
    return TypeRegistry([DecimalCodec()])


class BaseRepositoryInterface(ABC):
    pass


class BaseRepository(BaseRepositoryInterface, ABC):
    collection: Collection

    def __init__(self, client: MongoClient, db: Collection, collection_name: str, dto_class):
        codec_options = CodecOptions(tz_aware=True, type_registry=type_registry())

        self.client = client
        self.db = db
        self.collection = db.get_collection(collection_name, codec_options=codec_options)
        self.dto_class = dto_class

        if hasattr(dto_class, "indexes"):
            for compound_index in dto_class.indexes():
                self.collection.create_index(compound_index, background=True)

    def is_healthy(self) -> bool:
        try:
            return "ok" in self.client.admin.command("ping")
        except MongoConnectionFailure:
            return False

    def _op_set(self, fields: dict[str, Any]) -> dict:
        return {"$set": fields}

    def _update_one(self, filter_query, update_dict, upsert=True):
        r = self.collection.update_one(filter_query, update_dict, upsert=upsert)
        logger.debug(
            f"Mongodb _update_one: {filter_query=} {update_dict=} {r.acknowledged=} {r.matched_count=} {r.modified_count=} {r.upserted_id=} "
        )

        return r

    def _models_by_key_value(self, key: str, value: Any) -> Iterator:
        for item in self.collection.find({key: value}, batch_size=100):
            yield self.dto_class.parse_obj(item)

    def _count_docs_by_key_value(self, key: str, value: Any):
        return self.collection.count_documents(filter={key: value})

    def _models_by_key_value_paginated(self, key: str, value: str, skip: int, limit: int, sort_query: List[Tuple]):
        for item in self.collection.find({key: value}, batch_size=100, skip=skip, limit=limit).sort(sort_query):
            yield self.dto_class.parse_obj(item)

    def _model_by_key_value(self, key: str, value: Any) -> Optional[object]:
        item = self.collection.find_one(filter={key: value})
        if item is None:
            return None

        return self.dto_class.parse_obj(item)

    def _all_models(self) -> Iterator[object]:
        for item in self.collection.find({}, batch_size=100):
            yield self.dto_class.parse_obj(item)

    def delete_all(self):
        deleted = self.collection.delete_many({})
        logger.debug(f"Mongodb cleaned up [{deleted}] items.")
