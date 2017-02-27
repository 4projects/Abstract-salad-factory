import logging

from . import app
from .config import config
from . import model

import webob


@app.RootApp.path(model=model.RootDocument, path='')
def get_root_path(request):
    return request.app.db


@app.ResourceApp.path(model=model.DocumentCollection, path='')
def get_collection_path(request):
    return request.app.db


@app.ResourceApp.path(model=model.Document, path='{id}')
def get_document_path(request, id):
    return request.app.db.get(id)


@app.WebsocketApp.path(model=model.Websocket, path='')
def get_websocket_path(request):
    return model.Websocket(None)


@app.SaladsApp.mount(path='{id}/ingredients', app=app.IngredientsApp)
def mount_ingredients(request, id):
    salad = request.app.db.get(id)
    if salad:
        return app.IngredientsApp(salad)


@app.RootApp.mount(path='salads', app=app.SaladsApp)
def mount_salads(request):
    root = request.app.db
    return app.SaladsApp(root)


@app.ResourceApp.mount(path='ws', app=app.WebsocketApp)
def mount_websocket(request):
    return app.WebsocketApp()


@app.WebsocketApp.link_prefix()
def websocket_link_prefix(request):
    log = logging.getLogger(__name__)
    log.debug('Linking websocket')
    # Create a new request object which we will use to set the right
    # values for our websocket settings.
    request = webob.Request(request.environ.copy())
    if request.scheme.endswith('s'):
        request.scheme = 'wss'
    else:
        request.scheme = 'ws'
    # request.host_port is a string so compare to a string.
    if request.host_port == str(config['port'].get()):
        # We can only set the request.host value, so take the domain
        # and the new websocket port to create the new host.
        request.host = '{}:{}'.format(request.domain,
                                      config['websocket']['port'].get())
    return request.application_url
