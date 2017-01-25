import bowerstatic

from .app import App


bower = bowerstatic.Bower()

components = bower.components(
    'components',
    bowerstatic.module_relative_path('bower_components')
)






@App.static_components()
def get_static_components():
    return components
