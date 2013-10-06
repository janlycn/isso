
from __future__ import unicode_literals

import os
import json
import tempfile
import unittest

from werkzeug.test import Client
from werkzeug.wrappers import Response

from isso import Isso, notify, utils, core

utils.heading = lambda *args: "Untitled."
utils.urlexists = lambda *args: True


class FakeIP(object):

    def __init__(self, app, ip):
        self.app = app
        self.ip = ip

    def __call__(self, environ, start_response):
        environ['REMOTE_ADDR'] = self.ip
        return self.app(environ, start_response)


class TestVote(unittest.TestCase):

    def setUp(self):
        fd, self.path = tempfile.mkstemp()

    def tearDown(self):
        os.unlink(self.path)

    def makeClient(self, ip):

        conf = core.Config.load(None)
        conf.set("general", "dbpath", self.path)
        conf.set("guard", "enabled", "off")

        class App(Isso, core.Mixin):
            pass

        app = App(conf)
        app.wsgi_app = FakeIP(app.wsgi_app, ip)

        return Client(app, Response)

    def testZeroLikes(self):

        rv = self.makeClient("127.0.0.1").post("/new?uri=test", data=json.dumps({"text": "..."}))
        assert json.loads(rv.data)['likes'] == json.loads(rv.data)['dislikes'] == 0

    def testSingleLike(self):

        self.makeClient("127.0.0.1").post("/new?uri=test", data=json.dumps({"text": "..."}))
        rv = self.makeClient("0.0.0.0").post("/id/1/like")

        assert rv.status_code == 200
        assert json.loads(rv.data)["likes"] == 1

    def testSelfLike(self):

        bob = self.makeClient("127.0.0.1")
        bob.post("/new?uri=test", data=json.dumps({"text": "..."}))
        rv = bob.post('/id/1/like')

        assert rv.status_code == 200
        assert json.loads(rv.data)["likes"] == 0

    def testMultipleLikes(self):

        self.makeClient("127.0.0.1").post("/new?uri=test", data=json.dumps({"text": "..."}))
        for num in range(15):
            rv = self.makeClient("1.2.%i.0" % num).post('/id/1/like')
            assert rv.status_code == 200
            assert json.loads(rv.data)["likes"] == num + 1

    def testVoteOnNonexistentComment(self):
        rv = self.makeClient("1.2.3.4").post('/id/1/like')
        assert rv.status_code == 200
        assert json.loads(rv.data) == None

    def testTooManyLikes(self):

        self.makeClient("127.0.0.1").post("/new?uri=test", data=json.dumps({"text": "..."}))
        for num in range(256):
            rv = self.makeClient("1.2.%i.0" % num).post('/id/1/like')
            assert rv.status_code == 200

            if num >= 142:
                assert json.loads(rv.data)["likes"] == 142
            else:
                assert json.loads(rv.data)["likes"] == num + 1

    def testDislike(self):
        self.makeClient("127.0.0.1").post("/new?uri=test", data=json.dumps({"text": "..."}))
        rv = self.makeClient("1.2.3.4").post('/id/1/dislike')

        assert rv.status_code == 200
        assert json.loads(rv.data)['likes'] == 0
        assert json.loads(rv.data)['dislikes'] == 1
