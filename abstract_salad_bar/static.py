import itertools
import logging

import bowerstatic
from bowerstatic.autoversion import get_latest_filesystem_datetime

import webob
from webob.static import DirectoryApp

from . import locale


log = logging.getLogger(__name__)

bower = bowerstatic.Bower()

components = bower.components(
    'components',
    bowerstatic.module_relative_path('bower_components')
)

local = bower.local_components(
    'asb',
    components)

asb = local.component(bowerstatic.module_relative_path('local_component'),
                      version=None)

static = DirectoryApp('abstract_salad_bar/static')


def get_static(app, tempdir):

    locale.LocaleApp.initialize('abstract_salad_bar/template',
                                'abstract_salad_bar/locale', tempdir)

    known_languages = tuple(itertools.chain(
        locale.LocaleApp.known_locales.values()
    ))

    @webob.dec.wsgify
    def app_with_static(request):

        def create_handler(app):

            def handler(request):
                return request.get_response(app)
            return handler

        include = local.includer(request.environ)
        include('asb/js/asb.js')
        include('asb/js/index.js')
        include('asb/js/util.js')
        if asb.autoversion:
            bower_timestamp = get_latest_filesystem_datetime(asb.path).\
                timestamp()
        else:
            bower_timestamp = None
        peek = request.path_info_peek()
        if peek == 'api':
            request.path_info_pop()
            handler = create_handler(app)
        elif peek in itertools.chain.from_iterable(
            locale.LocaleApp.known_locales.values()
        ):
            locale_app = locale.LocaleApp.get_app(peek)
            request.path_info_pop()
            # Include dependencies.
            include('jquery')
            include('jquery-serialize-object')
            include('moment')
            include('moment-timezone')
            # Try to include the right momentjs locale, else just
            # skip it.
            for lang in (locale_app.languages):
                try:
                    include('moment/locale/{}.js'.format(
                        lang.replace('_', '-').lower()
                    ))
                    break
                except bowerstatic.Error:
                    pass
            else:
                log.debug('Failed to load "moment" locale file for "%s".',
                          peek)
            # Load locale app.
            if bower_timestamp:
                locale_app.bust_cache(bower_timestamp)
            handler = create_handler(locale_app)
            # Add injector tween.
            handler = bowerstatic.InjectorTween(bower, handler)
        elif not peek or peek == 'index.html':
            # Index file, load index template.
            locale_app = locale.LocaleApp.get_app(None)
            # Bust cache if local component is newer.
            if bower_timestamp:
                locale_app.bust_cache(bower_timestamp)
            handler = create_handler(locale_app)
            # Add injector tween.
            handler = bowerstatic.InjectorTween(bower, handler)
        else:
            # Return static files.
            handler = create_handler(static)
            # Add publisher tween.
            handler = bowerstatic.PublisherTween(bower, handler)
        return handler(request)

    return app_with_static
