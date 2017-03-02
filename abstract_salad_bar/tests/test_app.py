import morepath
import abstract_salad_bar

# from webtest import TestApp as Client


# def test_root():
#     morepath.scan(abstract_salad_bar)
#     morepath.commit(abstract_salad_bar.App)

#     client = Client(abstract_salad_bar.App())
#     root = client.get('/')

#     assert root.status_code == 200
#     assert len(root.json['greetings']) == 2
