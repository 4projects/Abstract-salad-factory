from webob import static

from . import app
from . import model


@app.App.view(model=model.Root)
def view_root(self, request):
    request.include('abstract_salad_bar')
    return request.get_response(static.FileApp('index.html'))


@app.ResourceApp.json(model=model.DocumentCollection)
def collection_json_view(self, request):
    return self


@app.ResourceApp.json(model=model.Document)
def document_json_view(self, request):
    return self


@app.ResourceApp.json(model=model.DocumentCollection, request_method='POST',
                      body_model=model.Document)
def create_salad(self, request):
    resource = self.add(request.body_obj)
    return request.view(resource)


# Load and dump json


@app.ResourceApp.dump_json(model=model.DocumentCollection)
def dump_json_collection(self, request):
    return {
        '@context': 'http://schema.org',
        '@type': 'ItemList',
        '@id': request.link(self),
        'itemListElement': [{
            '@id': request.link(v),
            '@type': v.schema_type,
        } for v in self.values()],
    }


@app.ResourceApp.dump_json(model=model.Document)
def dump_json_resource(self, request):
    return {
        '@context': 'http://schema.org',
        '@type': self.schema_type,
        '@id': request.link(self)
    }


@app.SaladsApp.dump_json(model=model.Salad)
def dump_json_salad(self, request):
    json = {
        'startDate': self.start_time.isoformat(),
        'location': self.location,
        'ingredients': {
            '@type': 'ItemList',
            '@id': request.link(
                self.ingredients,
                app=request.app.child(app.IngredientsApp(self))
            )
        }
    }
    json.update(dump_json_resource(self, request))
    return json


@app.IngredientsApp.dump_json(model=model.Ingredient)
def dump_json_ingredient(self, request):
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
    json.update(dump_json_resource(self, request))
    return json


@app.SaladsApp.load_json()
def load_json_salad(json, request):
    if model.Salad.is_valid_json(json):
        return model.Salad(start_time=json.get('startDate'),
                           location=json.get('location'))
    return json


@app.IngredientsApp.load_json()
def load_json_ingredient(json, request):
    if model.Ingredient.is_valid_json(json):
        return model.Ingredient(name=json['name'], owner=json['seller'])
    return json
