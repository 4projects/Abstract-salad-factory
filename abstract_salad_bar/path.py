from . import app
from . import model


@app.RootApp.path(model=model.Root, path='')
def get_root_path(request):
    return model.Root(request.app.db)


@app.ResourceApp.path(model=model.DocumentCollection, path='')
def get_collection_path(request):
    return request.app.db


@app.ResourceApp.path(model=model.Document, path='{id}')
def get_document_path(request, id):
    return request.app.db.get(id)


@app.SaladsApp.mount(path='{id}/ingredients', app=app.IngredientsApp)
def mount_ingredients(request, id):
    salad = request.app.db.get(id)
    if salad:
        return app.IngredientsApp(salad=salad)


@app.RootApp.mount(path='salads', app=app.SaladsApp)
def mount_salads():
    return app.SaladsApp()


# Trying to defer all links, but this does not seem to work.
# @app.SaladsApp.defer_links(model=model.IngredientCollection)
# def defer_ingredients(app, obj):
#     print(obj)
#     return app.child(app.IngredientsApp(obj))
