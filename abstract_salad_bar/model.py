"""The abstract salad bar model."""
import datetime
import logging

import arrow
from BTrees.OOBTree import BTree
import persistent
import shortuuid


def log():
    """Logger, is loaded on first use.

    Thus we make sure it is loaded after our config is loaded.
    """
    return logging.getLogger(__name__)


class Resource(object):

    def __init__(self):
        pass

    schema_type = 'Thing'

    def dump_json(self, request, root=True):
        json = {
            '@type': self.schema_type,
            '@id': request.link(self)
        }
        if root:
            # Only add the context if this is a root object.
            json.update({'@context': 'http://schema.org'})
        return json

    @classmethod
    def load_json(cls, json, request=None):
        return json


class DocumentCollection(BTree, Resource):

    # schema itemList
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def add(self, obj):
        self[obj.id] = obj
        return obj

    schema_type = 'ItemList'

    def dump_json(self, request, root=True):
        """Dump the json of a DocumentCollection.

        If full is in parameters we also dump all children.
        root indicates if this is the root object to be json dumped,
        children objects should have root set to false.
        """
        if request.params.get('full') or \
                (root and request.params.get('children')):
            def item_function(document):
                return document.dump_json(request, False)
        else:
            def item_function(document):
                return {
                    '@id': request.link(document),
                    '@type': document.schema_type,
                }
        json = {
            'itemListElement': [item_function(v) for v in self.values()],
            'websocket': {
                '@type': 'url',
                '@value': request.link(self, 'ws')
            },
        }
        json.update(super().dump_json(request, root))
        return json


class SaladCollection(DocumentCollection):
    pass


class IngredientCollection(DocumentCollection):
    pass


class CommentCollection(DocumentCollection):
    pass


class Document(persistent.Persistent, Resource):
    def __init__(self):
        super().__init__()
        self.id = shortuuid.uuid()

    @classmethod
    def is_valid_json(cls, json):
        log = logging.getLogger(__name__)
        log.debug('Validating abject of type [ %s ]', cls.__name__)
        schema_type = json.get('@type', json.get('type', ''))
        if schema_type.lower() != cls.schema_type.lower():
            log.debug('wrong schema_type: [ %s ], expected: [ %s ]',
                      schema_type, cls.schema_type)
            return False
        return True

    @classmethod
    def load_json(cls, json, request=None):
        return super(Document, cls).load_json(json, request)

    def dump_json(self, request, root=True):
        return super().dump_json(request, root)

    def _dump_json_attr(self, attribute, request, root):
        # If full parameter is set or, if children parameter is set and
        # this is the root object return whole attribute, not just a
        # reference.
        if request.params.get('full') or \
                (root and request.params.get('children')):
            return getattr(self, attribute).dump_json(request, False)
        else:
            return {'@id': request.link(self, attribute),
                    '@type': getattr(self, attribute).schema_type}


class SaladDocument(Document):
    """The salad."""

    def __init__(self, start_time=None, location=None):
        super().__init__()
        if not start_time:
            start_time = arrow.get()
            # TODO set to next Thursday 12.30
            if start_time.time() > datetime.time(12, 00):
                start_time = start_time.shift(days=1)
            start_time = start_time.replace(hour=12).floor('hour')
        # TODO make sure it is iso formated
        self.start_time = arrow.get(start_time)
        self.location = location
        self.ingredients = IngredientCollection(self)
        self.comments = CommentCollection(self)

    schema_type = 'FoodEvent'

    @classmethod
    def is_valid_json(cls, json):
        log = logging.getLogger(__name__)
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

    @classmethod
    def load_json(cls, json, request=None):
        if cls.is_valid_json(json):
            return cls(start_time=json.get('startDate'),
                       location=json.get('location', '').strip() or None)
        return super(SaladDocument, cls).load_json(json, request)

    def dump_json(self, request, root=True):
        json = {
            'startDate': self.start_time.isoformat(),
            'location': self.location,
            'ingredients': self._dump_json_attr('ingredients', request, root)
        }
        json.update(super().dump_json(request, root))
        return json


class IngredientDocument(Document):
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
        # The name and seller values must be filled.
        for name in ('name', 'seller'):
            if not json.get(name, '').strip():
                return False
        return True

    @classmethod
    def load_json(cls, json, request=None):
        if cls.is_valid_json(json):
            return cls(name=json['name'].strip(),
                       owner=json['seller'].strip())
        return super(IngredientDocument, cls).load_json(json, request)

    def dump_json(self, request, root=True):
        json = {
            'seller': {
                '@type': 'Person',
                'name': self.owner,
            },
            'itemOffered': {
                '@type': 'Product',
                'name': self.name,
            }
        }
        json.update(super().dump_json(request, root))
        return json


class CommentDocument(Document):
    """A comment attached to a salad."""

    pass


class RootDocument(Document):

    def __init__(self):
        super().__init__()
        self.salads = SaladCollection(self)

    def dump_json(self, request, root=True):
        json = {
            'salads': self._dump_json_attr('salads', request, root),
            'websocket': {
                '@type': 'url',
                '@value': request.link(Websocket())
            },
        }
        json.update(super().dump_json(request, root))
        return json


class Websocket(object):
    """A websocket, uesd to get the correct link."""

    pass
