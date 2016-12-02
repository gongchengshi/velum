import time
from multiprocessing import TimeoutError
import socket
import os
import requests
from requests.exceptions import ProxyError, HTTPError, TooManyRedirects, ConnectionError
from requests.exceptions import Timeout as RequestsTimeout
from python_common.timeout_wrapper import Timeout
from velum.common.exceptions import WebProxyDbException
from velum.common.geolocation import GeolocationException, get_lat_long
from velum.common.utils import get_public_ip_address, PercentDiffCalculator, calculate_throughput
from velum.model.models import *
from velum.model.model_helpers import get_or_add_endpoint, get_or_add_proxy_endpoint


def initialize_unused_proxy_names():
    local_unused_proxy_names = []
    all_proxy_names = Proxy.select(Proxy.name).distinct(Proxy.name)
    names = {p.name for p in all_proxy_names}
    file_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(file_dir, 'proxy_names.txt'), 'r') as proxy_names_file:
        for name in proxy_names_file:
            if name not in names:
                local_unused_proxy_names.append(name)
    return local_unused_proxy_names


class ProxyInitializer:
    unused_proxy_names = None

    @staticmethod
    def get_unused_proxy_name():
        if ProxyInitializer.unused_proxy_names is None:
            ProxyInitializer.unused_proxy_names = initialize_unused_proxy_names()
        # Todo: Recycle proxy names associated with ones from disabled proxies once the proxy name list is exhausted.
        return ProxyInitializer.unused_proxy_names.pop()

    my_ip_address = get_public_ip_address()

    file_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(file_dir, 'expected_content.html'), 'r') as expected_file:
        diff_calc = PercentDiffCalculator(expected_file.read())

    service_endpoints = {
        'http://headers.jsontest.com/': 'jsontest.com',
        'http://httpbin.org/headers': 'httpbin.org',
        'http://mysuperduperwebsite.s3-website-us-west-2.amazonaws.com/index.html': 'amazonaws.com',
        'https://httpbin.org/': 'httpbin.org',
        'http://tinyurl.com/k5h7kye': 'tinyurl.com',
        'https://www.google.com/': 'google.com'
    }

    def __init__(self, ip, port, source, proxy=None):
        self.proxy = proxy or Proxy()
        self.proxy_dict = {'http': 'http://%s:%s' % (ip, port),
                           'https': 'http://%s:%s' % (ip, port)}
        self.proxy.ip_address = ip
        self.proxy.port = port
        self.proxy.source = source

    def initialize(self):
        try:
            self.proxy.latitude, self.proxy.longitude = get_lat_long(self.proxy.ip_address)
        except GeolocationException, ex:
            raise WebProxyDbException(ex.message)

        self.proxy.save()  # Saving here so that ProxyEndpoint throughput stats can be set for subsequent requests.

        try:
            self.proxy.follows_redirects = self.follows_redirects()
            self.proxy.is_anonymous = self.is_anonymous()
            self.proxy.percent_modifying = self.percent_modifying()

            if self.proxy.percent_modifying:
                self.proxy.deactivate(DeactivationReasons.ContentModifying)
            elif self.proxy.follows_redirects:
                self.proxy.deactivate(DeactivationReasons.FollowsRedirects)
            elif self.proxy.is_anonymous:
                self.proxy.deactivate(DeactivationReasons.NotAnonymous)
        except HTTPError, ex:
            self.proxy.deactivate(ex.response.status_code)
        except ProxyError:
            self.proxy.deactivate(DeactivationReasons.ProxyError)
        except TooManyRedirects:
            self.proxy.deactivate(DeactivationReasons.TooManyRedirects)
        except (RequestsTimeout, socket.timeout, TimeoutError):
            self.proxy.deactivate(DeactivationReasons.TimeoutExceeded)
        except socket.error:
            self.proxy.deactivate(DeactivationReasons.SocketError)
        except ConnectionError:
            self.proxy.deactivate(DeactivationReasons.ConnectionError)

        if not self.proxy.deactivated_date:
            self.proxy.supports_https = self.supports_https()
            self.proxy.name = ProxyInitializer.get_unused_proxy_name()

        self.proxy.created_date = date.today()
        self.proxy.save()

        if self.proxy.deactivated_date is None:
            endpoints = Endpoint.select()
            for endpoint in endpoints:
                get_or_add_proxy_endpoint(self.proxy, endpoint)

    def proxy_get(self, url, allow_redirects=False):
        t_start = time.time()
        with Timeout(10):
            r = requests.get(url, allow_redirects=allow_redirects, proxies=self.proxy_dict, timeout=3)
        throughput = calculate_throughput(r, t_start, time.time())

        endpoint = get_or_add_endpoint(ProxyInitializer.service_endpoints[url])

        proxy_endpoint = get_or_add_proxy_endpoint(self.proxy, endpoint)
        proxy_endpoint.update_stats(throughput)
        proxy_endpoint.save()
        return r

    def is_anonymous(self):
        response = self.proxy_get("http://headers.jsontest.com/")
        if response.status_code != 200:
            response = requests.get('http://httpbin.org/headers')
            if response.status_code != 200:
                raise HTTPError(response=response)
        return ProxyInitializer.my_ip_address not in response.text

    def percent_modifying(self):
        """Request a known web page compare the actual response with expected response"""
        r = self.proxy_get('http://mysuperduperwebsite.s3-website-us-west-2.amazonaws.com/index.html',
                           allow_redirects=True)
        r.raise_for_status()
        return ProxyInitializer.diff_calc.diff(r.content)

    def supports_https(self):
        try:
            response = self.proxy_get("https://httpbin.org/")
            return response.status_code == 200 and 'Runscope' in response.content
        except (TypeError, ProxyError, ConnectionError, TooManyRedirects, Timeout, socket.timeout, socket.error):
            try:
                response = self.proxy_get('https://www.google.com/')
                return response.status_code == 200 and 'Google' in response.content
            except (TypeError, ProxyError, ConnectionError, TooManyRedirects, Timeout, socket.timeout, socket.error):
                return False

    def follows_redirects(self):
        response = self.proxy_get("http://tinyurl.com/k5h7kye", allow_redirects=False)
        response.raise_for_status()
        return response.status_code not in [301, 302, 303, 307]


def get_or_add_proxy(ip_address, port, source):
    try:
        proxy = Proxy.get((Proxy.ip_address == ip_address) & (Proxy.port == port))
        if proxy.created_date:
            return proxy
        initializer = ProxyInitializer(ip_address, port, source, proxy=proxy)
    except DoesNotExist:
        initializer = ProxyInitializer(ip_address, port, source)

    initializer.initialize()

    return initializer.proxy
