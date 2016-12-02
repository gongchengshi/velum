import zmq
from python_common.interruptable_thread import InterruptableThread
from velum.common.constants import DEFAULT_VELUM_PORT, GetNewProxyReasons
from velum.common.exceptions import WebProxyException
from velum.proxy_manager.proxy_info import ProxyInfo
from velum.model.models import ProxyEndpoint
from velum.model.model_helpers import get_or_add_endpoint


class ProxyManager(InterruptableThread):
    class Assignment:
        def __init__(self):
            self.standard = None
            self.restricted = None

    def __init__(self):
        InterruptableThread.__init__(self)
        self.zmq_context = zmq.Context.instance()
        self.server = self.zmq_context.socket(zmq.REP)
        self.server.bind('tcp://*:' + DEFAULT_VELUM_PORT)
        self.assignments = {}
        self.stop_requested = True

    def run(self):
        try:
            while not self.is_stop_requested():
                request = self.server.recv_json()
                cmd = request['cmd']
                if cmd == 'get_new':
                    result = self.get_new(request['key'],
                                          request['restricted'],
                                          request['reason'])
                    self.server.send_json(result)
                elif cmd == 'get_current':
                    result = self.get_current(request['key'],
                                              request['restricted'])
                    self.server.send_json(result)
                elif cmd == 'update_stats':
                    self.update_stats(request['id'],  # ProxyEndpoint.id
                                      request['throughput'])
                    self.server.send()
        finally:
            print 'Proxy manager exited'

    def _get_best(self, key, restricted):
        endpoint = get_or_add_endpoint(key)

        proxy_endpoint = None
        if restricted:
            proxy_endpoints = ProxyEndpoint.select(
                ProxyEndpoint.endpoint == endpoint and
                ProxyEndpoint.restricted and
                ProxyEndpoint.Proxy.deactivated_date is None).order_by(ProxyEndpoint.physical_distance)

            if not proxy_endpoints:
                proxy_endpoints = ProxyEndpoint.select(
                    ProxyEndpoint.endpoint == endpoint and
                    ProxyEndpoint.Proxy.deactivated_date is None).order_by(ProxyEndpoint.physical_distance)

                for p in proxy_endpoints:
                    if p.key not in self.assignments:
                        proxy_endpoint = p

            if not proxy_endpoint and proxy_endpoints:
                proxy_endpoints = sorted(proxy_endpoints, key=lambda p: p.ave_throughput, reverse=True)
                proxy_endpoints = sorted(proxy_endpoints, key=lambda p: p.blocked_count)
                proxy_endpoint = proxy_endpoints[0]

            if proxy_endpoint and not proxy_endpoint.restricted:
                proxy_endpoint.restricted = True
                proxy_endpoint.save()
        else:
            proxy_endpoints = ProxyEndpoint.select(
                ProxyEndpoint.endpoint == endpoint and
                not ProxyEndpoint.restricted and
                ProxyEndpoint.Proxy.deactivated_date is None).order_by(ProxyEndpoint.physical_distance)

            if proxy_endpoints:
                proxy_endpoints = sorted(proxy_endpoints, key=lambda p: p.ave_throughput, reverse=True)
                proxy_endpoints = sorted(proxy_endpoints, key=lambda p: p.blocked_count)
                proxy_endpoint = proxy_endpoints[0]

        if proxy_endpoint is None:
            raise WebProxyException()

        proxy = proxy_endpoint.proxy
        proxy_address = 'http://' + proxy.ip_address + ':' + proxy.port
        return ProxyInfo(proxy_endpoint.id, key, proxy_address, proxy.name, restricted)

    def get_new(self, key, restricted, reason=GetNewProxyReasons.NONE):
        try:
            current = self.assignments[key]
        except KeyError:
            return self.get_current(key, restricted)

        proxy_endpoint = ProxyEndpoint.get(ProxyEndpoint.id == current.proxy_endpoint_id)
        if reason:
            if reason == GetNewProxyReasons.BLOCKED:
                proxy_endpoint.blocked()

        if restricted:
            if current.restricted is None:
                current.restricted = self._get_best(key, restricted)
        else:
            if current.standard is None:
                current.standard = self._get_best(key, restricted)

        return (current.restricted if restricted else current.standard).pack()

    def get_current(self, key, restricted):
        try:
            current = self.assignments[key]
        except KeyError:
            current = ProxyManager.Assignment()
            self.assignments[key] = current

        if restricted:
            if current.restricted is None:
                current.restricted = self._get_best(key, restricted)
        else:
            if current.standard is None:
                current.standard = self._get_best(key, restricted)

        return (current.restricted if restricted else current.standard).pack()

    @staticmethod
    def update_stats(proxy_endpoint_id, throughput):
        # Todo: What to do if the proxy manager can't keep up?
        # Options: 1) Do batch updates every N requests. 2) Have the client update a PostgreSQL DB directly.
        # 3) Put the proxy manager on its own instance.
        proxy_endpoint = ProxyEndpoint.get(ProxyEndpoint.id == proxy_endpoint_id)
        proxy_endpoint.update_stats(throughput)
        proxy_endpoint.save()

        proxy = proxy_endpoint.proxy
        proxy.update_stats(throughput > 0.0)
        proxy.save()
