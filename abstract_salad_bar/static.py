import logging

import bowerstatic
import webob
from webob.static import DirectoryApp

from . import locale


log = logging.getLogger(__name__)

bower = bowerstatic.Bower()

components = bower.components(
    'components',
    bowerstatic.module_relative_path('bower_components')
)

static = DirectoryApp('abstract_salad_bar/static')


def get_static(app, tempdir):

    locale.LocaleApp.initialize('abstract_salad_bar/template',
                                'abstract_salad_bar/locale', tempdir)

    @webob.dec.wsgify
    def app_with_static(request):
        include = components.includer(request.environ)
        peek = request.path_info_peek()
        if peek == 'api':
            request.path_info_pop()
            return request.get_response(app)
        elif peek in locale.LocaleApp.known_locales:
            locale_app = locale.LocaleApp.get_app(peek)
            request.path_info_pop()
            # Include dependencies.
            include('jquery')
            include('jquery-serialize-object')
            include('moment')
            include('moment-timezone')
            # Try to include the right momentjs locale, else just
            # skip it.
            for lang in reversed(locale_app.languages):
                try:
                    include('moment/locale/{}.js'.format(
                        lang.replace('_', '-').lower()
                    ))
                    break
                except bowerstatic.Error:
                    pass
            else:
                log.debug('Failed to load moment locale file for %s.',
                          peek)
            # Load locale app.

            def handler(request):
                return request.get_response(locale_app)
            # Add injector tween.
            handler = bowerstatic.InjectorTween(bower, handler)
            return handler(request)
        else:
            # Return static file.

            def handler(request):
                return request.get_response(static)
            # Add publisher tween.
            handler = bowerstatic.PublisherTween(bower, handler)
            return handler(request)

    return app_with_static
