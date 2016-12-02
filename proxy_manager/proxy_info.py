import json


class ProxyInfo:
    def __init__(self, proxy_endpoint_id, key, proxy, name, restricted):
        self.proxy_endpoint_id = proxy_endpoint_id
        self.key = key
        self.proxy = proxy
        self.name = name
        self.restricted = restricted

    def pack(self):
        return json.dumps(self.__dict__())

    @staticmethod
    def json_decoder(j):
        return ProxyInfo(j['proxy_endpoint_id'],
                         j['key'],
                         j['proxy'],
                         j['name'],
                         j['restricted'] == 'True')

    @staticmethod
    def unpack(text):
        return json.loads(text, object_hook=ProxyInfo.json_decoder)
