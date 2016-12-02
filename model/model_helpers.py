import socket
from python_common.geography import haversine

from velum.common.geolocation import get_lat_long, GeolocationException
from velum.model.models import *


def initialize():
    db.connect()
    Proxy.create_table()
    Endpoint.create_table()
    ProxyEndpoint.create_table()
    Event403.create_table()


def get_or_add_proxy_endpoint(proxy, endpoint):
    try:
        proxy_endpoint = ProxyEndpoint.get((ProxyEndpoint.proxy == proxy) & (ProxyEndpoint.endpoint == endpoint))
        return proxy_endpoint
    except DoesNotExist:
        pass

    proxy_endpoint = ProxyEndpoint()
    proxy_endpoint.proxy = proxy
    proxy_endpoint.endpoint = endpoint
    proxy_endpoint.created_date = date.today()
    if proxy.latitude and proxy.longitude and endpoint.longitude and endpoint.latitude:
        proxy_endpoint.physical_distance = haversine(
            proxy.longitude, proxy.latitude, endpoint.longitude, endpoint.latitude)

    proxy_endpoint.save()
    return proxy_endpoint


def get_or_add_endpoint(key):
    try:
        endpoint = Endpoint.get((Endpoint.key == key))
    except DoesNotExist:
        endpoint = Endpoint()
        endpoint.key = key

        try:
            endpoint.ip_address = socket.gethostbyname(key)
            endpoint.latitude, endpoint.longitude = get_lat_long(endpoint.ip_address)
        except (socket.gaierror, GeolocationException):
            pass

        endpoint.save()

    proxies = Proxy.select()
    for proxy in proxies:
        get_or_add_proxy_endpoint(proxy, endpoint)
    return endpoint


def populate_proxy_endpoints(endpoint):
    proxy_endpoints = ProxyEndpoint.get(Proxy.endpoint == endpoint)
    proxies = Proxy.get(Proxy.deactivated_date is None)
    known_proxies = set([x.proxy for x in proxy_endpoints])
    for proxy in proxies:
        if proxy in known_proxies:
            continue
        get_or_add_proxy_endpoint(proxy, endpoint)


def get_proxy(ip_address, port):
    return Proxy.get((Proxy.ip_address == ip_address) & Proxy.port == port) if port \
        else Proxy.get(Proxy.ip_address == ip_address)


def get_endpoint(key):
    return Endpoint.get(Endpoint.key == key)
