import datetime
from functools import partial
from unittest import mock

from dateutil import tz

import iso8601

import pytest

from asf import model


class MockRequest(mock.MagicMock):
    def __init__(self, **kwargs):
        if 'params' not in kwargs:
            kwargs['params'] = {}
        super().__init__(link=mock.MagicMock(), **kwargs)


class TestResource:

    resource_class = model.Resource

    @property
    def resource(self):
        return self.resource_class

    def test_dump_json_no_root(self):
        resource = self.resource()
        json = resource.dump_json(MockRequest(), root=False)
        assert '@context' not in json

    def test_dump_json(self):
        resource = self.resource()
        request = MockRequest()
        json = resource.dump_json(request)
        assert json['@type'] == self.resource_class.schema_type
        assert '@id' in json
        request.link.assert_any_call(resource)
        assert json['@context'] == 'http://schema.org'

    def test_load_json_fail(self):
        obj = self.resource_class.load_json({}, request=MockRequest())
        assert not isinstance(obj, self.resource_class)
        assert obj == {}


class TestDocumentCollection(TestResource):
    resource_class = model.DocumentCollection
    parent = None
    _document = model.Document

    @property
    def resource(self):
        return partial(self.resource_class, self.parent)

    @property
    def document(self):
        return mock.MagicMock(self._document)

    def test_add(self):
        resource = self.resource()
        mock_document = self.document()
        obj = resource.add(mock_document)
        assert obj is mock_document

    def test_dump_json_no_root(self):
        resource = self.resource()
        json = resource.dump_json(MockRequest(), root=False)
        assert 'websocket' not in json

    def test_dump_json(self):
        resource = self.resource()
        document = self.document()
        request = MockRequest()
        resource[document.id] = document
        json = resource.dump_json(request)
        assert not document.dump_json.called
        assert len(json['itemListElement']) == 1
        item = json['itemListElement'][0]
        assert sorted(item.keys()) == ['@id', '@type']
        assert item['@type'] == document.schema_type
        request.link.assert_any_call(document)
        websocket = json['websocket']
        assert websocket['@type'] == 'url'
        assert '@value' in websocket

    def test_dump_json_with_children(self):
        resource = self.resource()
        document = self.document()
        resource[document.id] = document
        json = resource.dump_json(MockRequest(params={'children': True}))
        assert document.dump_json.called
        assert len(json['itemListElement']) == 1
        item = json['itemListElement'][0]
        assert '@context' not in item


class TestSaladCollection(TestDocumentCollection):
    resource_class = model.SaladCollection
    _document = model.SaladDocument


class TestIngredientCollection(TestDocumentCollection):
    resource_class = model.IngredientCollection
    _document = model.IngredientDocument


class TestCommentCollection(TestDocumentCollection):
    resource_class = model.CommentCollection
    _document = model.CommentDocument


class TestDocument(TestResource):
    resource_class = model.Document

    @pytest.mark.parametrize('json, valid', [
        ({'@type': 'Thing'}, True),
        ({'type': 'Thing'}, True),
        ({'type': 'thing'}, True),
        ({'type': 'THING'}, True),
        ({'type': 'something'}, False),
        ({'sometype': 'thing'}, False),
        ({}, False),
    ])
    def test_is_valid_json(self, json, valid):
        assert self.resource_class.is_valid_json(json) is valid

    def test_load_json(self):
        json = {'@type': self.resource_class.schema_type}
        obj = self.resource_class.load_json(json)
        assert not isinstance(obj, self.resource_class)
        assert obj == json


class TestSaladDocument(TestDocument):
    resource_class = model.SaladDocument

    @property
    def resource(self):
        return partial(self.resource_class,
                       datetime.datetime.now(tz.tzutc()))

    @pytest.mark.parametrize('json, valid', [
        ({}, False),
        ({'@type': 'FoodEvent'}, False),
        ({'type': 'FoodEvent', 'startDate': ''}, False),
        ({'type': 'FoodEvent', 'startDate': 'hello'}, False),
        ({'type': 'FoodEvent',
          'startDate': '2017-03-04T17:26'}, False),  # Missing timezone.
        ({'type': 'FoodEvent', 'startDate': '2017-03-04T17:26-05:00'}, True),
        ({'type': 'FoodEvent',
          'startDate': '2017-03-04 17:26:00-05:00'}, True),
        ({'type': 'FoodEvent',
          'startDate': '2017-03-04 17:26:00.000000-05:00'}, True),
        ({'type': 'FoodEvent',
          'startDate': '2017-03-04 17:26-05:00.000000'}, False),
        ({'type': 'FoodEvent',
          'startDate': '2017-03-04 17:26:00.000000-05:00',
          'location': 'Somewhere'}, True),
    ])
    def test_is_valid_json(self, json, valid):
        assert self.resource_class.is_valid_json(json) is valid

    @pytest.mark.parametrize('json, result', [
        ({'startDate': '2017-03-04T17:26-05:00'},
         {'start_time': iso8601.parse_date('2017-03-04T17:26:00-05:00'),
          'location': None}),
        ({'startDate': '2017-03-04T17:26-05:00'},
         {'start_time': datetime.datetime(2017, 3, 4, 22, 26,
                                          tzinfo=tz.tzutc()),
          'location': None}),
        ({'startDate': '2017-03-04T17:26-05:00',
          'location': 'somewhere'}, {'location': 'somewhere'}),
        ({'startDate': '2017-03-04T17:26-05:00',
          'location': 'somewhere   '}, {'location': 'somewhere'}),
        ({'startDate': '2017-03-04T17:26-05:00',
          'location': ''}, {'location': None}),
        ({'startDate': '2017-03-04T17:26-05:00',
          'location': '  '}, {'location': None}),
    ])
    def test_load_json(self, json, result):
        json.update({'@type': self.resource_class.schema_type})
        obj = self.resource_class.load_json(json, request=MockRequest())
        assert isinstance(obj, self.resource_class)
        for attr, val in result.items():
            assert getattr(obj, attr) == val

    @pytest.mark.parametrize('date', [
        datetime.datetime.now(),
    ])
    def test_init_fail(self, date):
        with pytest.raises(ValueError):
            self.resource_class(date)

    def test_dump_json(self):
        resource = self.resource()
        request = MockRequest()
        json = resource.dump_json(request)
        iso8601.parse_date(json['startDate'])
        assert not json['location']
        ingredients = json['ingredients']
        assert ingredients['@type'] == resource.ingredients.schema_type
        request.link.assert_any_call(resource, 'ingredients')

    def test_dump_json_location(self):
        location = 'somewhere'
        resource = self.resource(location=location)
        json = resource.dump_json(MockRequest())
        iso8601.parse_date(json['startDate'])
        assert json['location'] == location

    def test_dump_json_with_children(self):
        resource = self.resource()
        request = MockRequest(params={'children': True})
        json = resource.dump_json(request)
        ingredients = json['ingredients']
        assert isinstance(ingredients['itemListElement'], list)
        assert '@context' not in ingredients


class TestIngredientDocument(TestDocument):
    resource_class = model.IngredientDocument

    name = 'lettuce'
    owner = 'me'

    @property
    def resource(self):
        return partial(self.resource_class, self.name, self.owner)

    @pytest.mark.parametrize('json, valid', [
        ({}, False),
        ({'type': 'Offer'}, False),
        ({'type': 'Offer', 'seller': 'me'}, False),
        ({'type': 'Offer', 'name': 'lettuce'}, False),
        ({'type': 'Offer', 'name': '', 'seller': ''}, False),
        ({'type': 'Offer', 'name': 'lettuce', 'seller': ''}, False),
        ({'type': 'Offer', 'name': '', 'seller': 'me'}, False),
        ({'type': 'Offer', 'name': '  ', 'seller': 'me'}, False),
        ({'type': 'Offer', 'name': 'lettuce', 'seller': '  '}, False),
        ({'type': 'Offer', 'name': 'lettuce', 'seller': 'me'}, True),
        # These are not working yet, have to implemment dict parsing.
        pytest.mark.xfail(
            ({'type': 'Offer', 'name': {}, 'seller': {}}, False)
        ),
        pytest.mark.xfail(
            ({'type': 'Offer', 'name': {'name': ''}, 'seller': 'me'}, False),
        ),
        pytest.mark.xfail(
            ({'type': 'Offer', 'name': {'name': 'lettuce'},
              'seller': 'me'}, True),
        ),
        pytest.mark.xfail(
            ({'type': 'Offer', 'name': {'type': 'Product',
                                        'name': 'lettuce'},
              'seller': 'me'}, True),
        ),
        pytest.mark.xfail(
            ({'type': 'Offer', 'name': {'@type': 'Product',
                                        'name': 'lettuce'},
              'seller': 'me'}, True),
        ),
        pytest.mark.xfail(
            ({'type': 'Offer', 'name': {'@type': 'Person',
                                        'name': 'lettuce'},
              'seller': 'me'}, False),
        ),
        pytest.mark.xfail(
            ({'type': 'Offer', 'name': {'@type': 'Product',
                                        'name': ''},
              'seller': 'me'}, False),
        ),
        pytest.mark.xfail(
            ({'type': 'Offer', 'name': 'lettuce',
              'seller': {'type': 'Person',
                         'name': 'me'}}, True),
        ),
    ])
    def test_is_valid_json(self, json, valid):
        assert self.resource_class.is_valid_json(json) is valid

    @pytest.mark.parametrize('json, result', [
        ({'name': 'lettuce', 'seller': 'me'},
         {'name': 'lettuce', 'owner': 'me'}),
        ({'name': 'lettuce  ', 'seller': 'me  '},
         {'name': 'lettuce', 'owner': 'me'}),
        pytest.mark.xfail(
            ({'name': {'name': 'lettuce  '}, 'seller': {'name': 'me  '}},
             {'name': 'lettuce', 'owner': 'me'}),
        ),
    ])
    def test_load_json(self, json, result):
        json.update({'@type': self.resource_class.schema_type})
        obj = self.resource_class.load_json(json, request=MockRequest())
        assert isinstance(obj, self.resource_class)
        for attr, val in result.items():
            assert getattr(obj, attr) == val

    def test_dump_json(self):
        resource = self.resource()
        request = MockRequest()
        json = resource.dump_json(request)
        seller = json['seller']
        assert seller['@type'] == 'Person'
        assert seller['name'] == self.owner
        item = json['itemOffered']
        assert item['@type'] == 'Product'
        assert item['name'] == self.name


class TestCommentDocument(TestDocument):
    resource_class = model.CommentDocument


class TestRootDocument(TestDocument):
    resource_class = model.RootDocument

    def test_dump_json(self):
        resource = self.resource()
        request = MockRequest()
        json = resource.dump_json(request)
        salads = json['salads']
        assert salads['@type'] == resource.salads.schema_type
        request.link.assert_any_call(resource, 'salads')
        websocket = json['websocket']
        assert websocket['@type'] == 'url'
        assert '@value' in websocket

    def test_dump_json_with_children(self):
        resource = self.resource()
        request = MockRequest(params={'children': True})
        json = resource.dump_json(request)
        salads = json['salads']
        assert isinstance(salads['itemListElement'], list)
        assert '@context' not in salads
