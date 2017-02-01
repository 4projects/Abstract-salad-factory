import logging

from more.transaction import TransactionApp

log = logging.getLogger(__name__)

# Tweens only work on the root app. So set the root app as the TransactionApp,
# to make sure the transaction tween is run.


class ResourceApp(TransactionApp):

    def __init__(self, parent):
        self.parent = parent
        self.id = self.parent.id


class RootApp(ResourceApp):

    def __init__(self, root):
        self.db = root
        self.id = root.id


class SaladsApp(ResourceApp):

    def __init__(self, parent):
        super().__init__(parent)
        self.db = self.parent.salads


class IngredientsApp(ResourceApp):

    def __init__(self, parent):
        super().__init__(parent)
        self.db = self.parent.ingredients


App = RootApp
