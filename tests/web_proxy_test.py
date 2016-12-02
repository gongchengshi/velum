import sys

import os


#sys.path = [os.path.dirname(os.path.dirname(__file__))] + sys.path

import unittest

from model.model_helpers import initialize
from proxy_import.proxy_initializer import ProxyInitializer


class ProxyInitializerTests(unittest.TestCase):
    def setUp(self):
        if not os.path.exists("web_proxies.db"):
            initialize()

    def test_initialize(self):
        initializer = ProxyInitializer('10.100.0.240', 8080, 'me')
        initializer.initialize()

unittest.main()
