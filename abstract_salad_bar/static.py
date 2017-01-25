import bowerstatic
import webob
from webob.static import DirectoryApp


bower = bowerstatic.Bower()

components = bower.components(
    'components',
    bowerstatic.module_relative_path('bower_components')
)

static = DirectoryApp('abstract_salad_bar/static')


def get_static(app):

    def static_handler(request):
        return request.get_response(static)

    static_handler = bowerstatic.InjectorTween(bower, static_handler)
    static_handler = bowerstatic.PublisherTween(bower, static_handler)

    @webob.dec.wsgify
    def app_with_static(request):
        if request.path_info_peek() == 'api':
            request.path_info_pop()
            return request.get_response(app)
        else:
            include = components.includer(request.environ)
            include('jquery')
            return static_handler(request)

    return app_with_static
