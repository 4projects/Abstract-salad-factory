import logging

from . import app as app_module
from . import model


log = logging.getLogger(__name__)


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


# TODO move to path.
# Load and dump json



@app_module.RootApp.defer_links(model=model.SaladCollection)
def defer_salad_collection_links(app, obj):
    return app.child(app_module.SaladsApp(obj.parent))


@app_module.SaladsApp.defer_links(model=model.IngredientCollection)
def defer_ingredient_collection_links(app, obj):
    return app.child(app_module.IngredientsApp(obj.parent))


@app_module.ResourceApp.dump_json(model=model.Resource)
def dump_json(self, request):
    return self.dump_json(request)


@app_module.SaladsApp.load_json()
def load_json_salad(json, request):
    return model.SaladDocument.create_from_json(json, request)


@app_module.IngredientsApp.load_json()
def load_json_ingredient(json, request):
    return model.IngredientDocument.create_from_json(json, request)
