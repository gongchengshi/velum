from velum.common.constants import GetNewProxyReasons
import zmq
from velum.common.exceptions import VelumNotResponding
from velum.proxy_manager.proxy_info import ProxyInfo


class ProxyManagerClient:
    def __init__(self, address):
        self.zmq_context = zmq.Context.instance()
        self.client = self.zmq_context.socket(zmq.REQ)
        self.async_client = self.zmq_context.socket(zmq.DEALER)
        self.client.RCVTIMEO = 1000 * 60  # wait up to a minute for responses to come back
        self.client.connect(address)

    def get_new(self, key, restricted, reason=GetNewProxyReasons.NONE):
        try:
            self.client.send_json({'cmd': 'get_new',
                                   'key': key,
                                   'restricted': restricted,
                                   'reason': reason})
            response = self.client.recv_json()
            return ProxyInfo.unpack(response)
        except zmq.error.Again:
            raise VelumNotResponding()

    def get_current(self, key, restricted):
        try:
            self.client.send_json({'cmd': 'get_current',
                                   'key': key,
                                   'restricted': restricted})
            response = self.client.recv_json()
            return ProxyInfo.unpack(response)
        except zmq.error.Again:
            raise VelumNotResponding()

    def update_stats(self, proxy_endpoint_id, throughput):
        try:
            self.async_client.send_json({'cmd': 'update_stats',
                                         'id': proxy_endpoint_id,
                                         'throughput': throughput})
        except zmq.error.Again:
            raise VelumNotResponding()
