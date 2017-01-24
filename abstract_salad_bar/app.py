from . import model

from more.transaction import TransactionApp
import morepath
import ZODB
import zodburi


# Want to move this to settings, but have not worked out how.
uri = 'memory://'
storage_factory, dbkw = zodburi.resolve_uri(uri)
storage = storage_factory()

# Tweens only work on the root app. So set the root app as the TransactionApp,
# to make sure the transaction tween is run.


class App(TransactionApp):

    @morepath.reify
    def db(self):
        uri = self.settings.db.uri
        return ZODB.DB(storage, **dbkw).open()


@App.setting(section='db', name='uri')
def get_database_settings():
    return 'file://bla.fs'


class ResourceApp(App):

    @morepath.reify
    def db(self):
        db = super().db
        return db.root()


class SaladsApp(ResourceApp):

    @morepath.reify
    def db(self):
        db = super().db
        return db.setdefault('salads', model.SaladCollection())


class IngredientsApp(ResourceApp):

    def __init__(self, salad):
        super().__init__()
        self.salad = salad
        self.id = salad.id

    @morepath.reify
    def db(self):
        return self.salad.ingredients
