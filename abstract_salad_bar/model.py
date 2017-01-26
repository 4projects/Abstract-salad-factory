"""The abstract salad bar model."""
import datetime
import logging

import arrow
from BTrees.OOBTree import BTree
import persistent
import shortuuid


log = logging.getLogger(__name__)


class Resource(object):
    pass


class DocumentCollection(BTree, Resource):

    # schema itemList

    def add(self, obj):
        self[obj.id] = obj
        return obj


class SaladCollection(DocumentCollection):
    pass


class IngredientCollection(DocumentCollection):
    pass


class CommentCollection(DocumentCollection):
    pass


class Document(persistent.Persistent, Resource):
    def __init__(self):
        self.id = shortuuid.uuid()

    @property
    def schema_type(self):
        return self.__class__.__name__

    @classmethod
    def is_valid_json(cls, json):
        log.debug('Validating abject of type [ %s ]', cls.__name__)
        schema_type = json.get('@type', json.get('type', ''))
        if schema_type.lower() != cls.schema_type.lower():
            log.debug('wrong schema_type: [ %s ], expected: [ %s ]',
                      schema_type, cls.schema_type)
            return False
        return True


class Salad(Document):
    """The salad."""

    def __init__(self, start_time=None, location=None):
        super().__init__()
        if not start_time:
            start_time = arrow.get()
            if start_time.time() > datetime.time(12, 00):
                start_time = start_time.shift(days=1)
            start_time = start_time.replace(hour=12).floor('hour')
        self.start_time = arrow.get(start_time)
        self.location = location
        self.ingredients = IngredientCollection()
        self.comments = CommentCollection()

    schema_type = 'FoodEvent'

    @classmethod
    def is_valid_json(cls, json):
        if not super().is_valid_json(json):
            return False
        date = json.get('startDate')
        if date:
            try:
                # Don't like this for validation, how could I improve this?
                arrow.get(date)
            except RuntimeError:
                log.debug('Could not parse date')
                return False
        return True


class Ingredient(Document):
    """A ingredient in a salad."""

    def __init__(self, name, owner):
        super().__init__()
        # shcema.org/offer
        self.owner = owner
        # owner: schema.org/offeredBy
        self.name = name

    schema_type = 'Offer'

    @classmethod
    def is_valid_json(cls, json):
        if not super().is_valid_json(json):
            return False
        for name in ('name', 'seller'):
            if name not in json:
                return False
        return True


class Comment(Document):
    """A comment attached to a salad."""

    pass


class Root(Resource):

    def __init__(self, db):
        print(db)
        self.salads = db['salads']
