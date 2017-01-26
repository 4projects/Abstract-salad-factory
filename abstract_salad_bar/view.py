
from . import app as app_module
from . import model


# @app_module.App.view(model=model.Root)
# def view_root(self, request):
#     request.include('abstract_salad_bar')
#     return request.get_response(static.FileApp(
#         module_relative_path('index.html')
#     ))


@app_module.ResourceApp.json(model=model.Resource)
def view_json_resource(self, request):
    return self


@app_module.ResourceApp.json(model=model.DocumentCollection,
                             request_method='POST',
                             body_model=model.Document)
def create_document(self, request):
    resource = self.add(request.body_obj)
    return request.view(resource)


# Load and dump json


@app_module.ResourceApp.dump_json(model=model.DocumentCollection)
def dump_json_collection(app, self, request):
    if request.params.get('full'):
        def item_function(document):
            return app._dump_json(document, request)
    else:
        def item_function(document):
            return {
                '@id': request.link(document),
                '@type': document.schema_type,
            }
    data = {
        '@type': 'ItemList',
        '@id': request.link(self),
        'itemListElement': [item_function(v) for v in self.values()]
    }
    data.update({'@context': 'http://schema.org'})
    return data


@app_module.ResourceApp.dump_json(model.Root)
def dump_json_root(app, self, request):
    data = {
        'salads': dump_json_document(app.child(app_module.SaladsApp()),
                                     self.salads,
                                     request)
    }
    data.update({'@context': 'http://schema.org'})
    return data


@app_module.ResourceApp.dump_json(model=model.Document)
def dump_json_document(app, self, request):
    data = {
        '@type': self.schema_type,
        '@id': request.link(self, app=app)
    }
    data.update({'@context': 'http://schema.org'})
    return data


@app_module.ResourceApp.dump_json(model=model.Salad)
def dump_json_salad(app, self, request):
    json = {
        'startDate': self.start_time.isoformat(),
        'location': self.location,
        'ingredients': dump_json_document(
            app.child(app_module.IngredientsApp(self)),
            self.ingredients, request
        )
    }
    json.update(dump_json_document(app, self, request))
    return json


@app_module.ResourceApp.dump_json(model=model.Ingredient)
def dump_json_ingredient(app, self, request):
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
    json.update(dump_json_document(app, self, request))
    return json


@app_module.SaladsApp.load_json()
def load_json_salad(json, request):
    if model.Salad.is_valid_json(json):
        return model.Salad(start_time=json.get('startDate'),
                           location=json.get('location'))
    return json


@app_module.IngredientsApp.load_json()
def load_json_ingredient(json, request):
    if model.Ingredient.is_valid_json(json):
        return model.Ingredient(name=json['name'], owner=json['seller'])
    return json
