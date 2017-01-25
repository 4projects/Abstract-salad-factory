from . import model

from more.transaction import TransactionApp
from more.static import StaticApp
import morepath
import ZODB
import zodburi


# Want to move this to settings, but have not worked out how.
uri = 'memory://'
storage_factory, dbkw = zodburi.resolve_uri(uri)
storage = storage_factory()

# Tweens only work on the root app. So set the root app as the TransactionApp,
# to make sure the transaction tween is run.


class ResourceApp(TransactionApp, StaticApp):

    @morepath.reify
    def db(self):
        uri = self.settings.db.uri
        db = ZODB.DB(storage, **dbkw).open()
        db = db.root()
        db.setdefault('salads', model.SaladCollection())
        return db


@ResourceApp.setting(section='db', name='uri')
def get_database_settings():
    return 'file://bla.fs'


class RootApp(ResourceApp):
    pass


class SaladsApp(ResourceApp):

    @morepath.reify
    def db(self):
        db = super().db
        return db['salads']


class IngredientsApp(ResourceApp):

    def __init__(self, salad):
        super().__init__()
        self.salad = salad
        self.id = salad.id

    @morepath.reify
    def db(self):
        return self.salad.ingredients


App = RootApp
