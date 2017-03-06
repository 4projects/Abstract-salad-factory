import morepath
import asf

# from webtest import TestApp as Client


# def test_root():
#     morepath.scan(asf)
#     morepath.commit(asf.App)

#     client = Client(asf.App())
#     root = client.get('/')

#     assert root.status_code == 200
#     assert len(root.json['greetings']) == 2
