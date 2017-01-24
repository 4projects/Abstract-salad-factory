import bowerstatic

from .app import App


bower = bowerstatic.Bower()


components = bower.components(
    'components',
    bowerstatic.module_relative_path('bower_components')
)


local = bower.local_components('local', components)


local.component(bowerstatic.module_relative_path('local_component'),
                version=None)


@App.static_components()
def get_static_components():
    return local
