import time
import requests
import requests.exceptions
from twisted.internet.defer import Deferred
from twisted.internet import reactor
from twisted.web.http import Request, HTTPChannel
from velum.model.models import DeactivationReasons


def request_from_proxy(parent):
    t_start = time.time()

    proxy_endpoint, proxy, proxy_dict = get_endpoint_proxy(parent.uri)
    r = None

    max_tries = 3
    for i in xrange(max_tries):
        try:
            r = requests.get(parent.uri,
                             headers=parent.getAllHeaders().copy(),
                             allow_redirects=False,
                             verify=False,
                             proxies=proxy_dict)
        except requests.exceptions.ProxyError:
            proxy.deactivate(DeactivationReasons.ProxyError)
            proxy_endpoint, proxy, proxy_dict = get_endpoint_proxy(parent.uri)

    throughput = calculate_throughput(r, t_start, time.time())

    proxy_endpoint.update_stats(throughput)
    proxy_endpoint.save()

    proxy.update_stats(r.status_code < 400 or r.status_code >= 500, parent.uri[4] == 's')
    proxy.save()

    for key, value in r.headers.iteritems():
        parent.setHeader(key, value)

    parent.setResponseCode(r.status_code)
    parent.write(r.content)
    parent.finish()


class ProxyRequest(Request):
    def __init__(self, channel, queued):
        Request.__init__(self, channel, queued)

    def process(self):
        d = Deferred()
        d.addCallback(request_from_proxy)
        d.callback(self)


class WebProxy(HTTPChannel):
    requestFactory = ProxyRequest


from twisted.web import http


class ProxyFactory(http.HTTPFactory):
    def buildProtocol(self, addr):
        return WebProxy()

try:
    reactor.listenTCP(8084, ProxyFactory())
    reactor.run()
finally:
    import smtplib

    server = smtplib.SMTP("my.inbox.com", 25)
    server.starttls()
    server.login('<email>', '<password>')

    server.sendmail('Web Proxy', '<phone number>@vtext.com', 'Web proxy has stopped')
