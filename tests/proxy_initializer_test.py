from shutil import copyfile
copyfile('../../python_common/geocoding/test/example.cfg', 'geopyplus.cfg')

import os
# import unittest

from model.model_helpers import initialize
from proxy_import.proxy_initializer import ProxyInitializer


if os.path.exists("web_proxies.db"):
    os.remove("web_proxies.db")

if not os.path.exists("web_proxies.db"):
    initialize()
initializer = ProxyInitializer('10.100.0.240', 8080, 'me')
initializer.initialize()

# class ProxyInitializerTests(unittest.TestCase):
#     def setUp(self):
#         if not os.path.exists("web_proxies.db"):
#             initialize()
#
#     def test_initialize(self):
#         initializer = ProxyInitializer('10.100.0.240', 8080, 'me')
#         initializer.initialize()
#
# unittest.main()
