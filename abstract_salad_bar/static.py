import logging

import bowerstatic
import webob
from webob.static import DirectoryApp


log = logging.getLogger(__name__)

bower = bowerstatic.Bower()

components = bower.components(
    'components',
    bowerstatic.module_relative_path('bower_components')
)

static = DirectoryApp('abstract_salad_bar/static')

known_locales = ['en-US', 'nl']


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
            peek = request.path_info_peek()
            if peek in known_locales:
                include('jquery')
                include('jquery-serialize-object')
                include('moment')
                include('moment-timezone')
                try:
                    include('moment/locale/{}.js'.format(peek.lower()))
                except bowerstatic.Error as e:
                    log.debug('Failed to load moment locale file for %s: %s',
                              peek, e)
            return static_handler(request)

    return app_with_static
