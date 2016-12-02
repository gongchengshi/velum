import sys
from peewee import DoesNotExist
import requests
from velum.common.exceptions import WebProxyDbException
from velum.model.models import Proxy
from velum.proxy_import.proxy_initializer import ProxyInitializer


def check_services():
    ok = True
    if not (requests.get("http://headers.jsontest.com/") or requests.get('http://httpbin.org/headers')):
        ok = False
        print "Can't retrieve headers"

    if not requests.get("https://httpbin.org/"):
        ok = False
        print "Can't test HTTPS"

    if requests.get("http://tinyurl.com/k5h7kye", allow_redirects=False).status_code not in [301, 302, 303, 307]:
        ok = False
        print "Can't test redirects via tinyurl.com"

    if not requests.get('https://s3-us-west-2.amazonaws.com/mysuperduperwebsite/destination.html'):
        ok = False
        print "Can't test redirects to destination"

    if not (requests.get('http://www.freegeoip.net/json/74.117.214.70', timeout=3) or
            requests.get("http://ip-api.com/json/74.117.214.70")):
        ok = False
        print "Can't get geolocation information"

    if not requests.get('https://s3-us-west-2.amazonaws.com/mysuperduperwebsite/index.html'):
        ok = False
        print "Can't test content modification"

    return ok


def process_proxy(ip_address, port, source):
    try:
        try:
            proxy = Proxy.get((Proxy.ip_address == ip_address) & (Proxy.port == port))
            if proxy.created_date:
                sys.stdout.write('.')
                sys.stdout.flush()
                return
            initializer = ProxyInitializer(ip_address, port, source, proxy=proxy)
        except DoesNotExist:
            initializer = ProxyInitializer(ip_address, port, source)

        sys.stdout.write("\n{0: <22}".format(ip_address + ':' + port))
        sys.stdout.flush()
        initializer.initialize()
        if initializer.proxy.deactivated_date:
            sys.stdout.write("Dud {0: <4}".format(initializer.proxy.deactivation_reason))
        else:
            sys.stdout.write("HTTPS   " if initializer.proxy.supports_https else "HTTP    ")
    except WebProxyDbException as ex:
        sys.stdout.write(ex.message)
    sys.stdout.flush()
