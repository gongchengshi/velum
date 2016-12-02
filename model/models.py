from datetime import datetime, date

from peewee import *
from velum.common.utils import new_moving_average


# threadlocals=True creates one SQLite connection per thread.
# This allows serialization of reads/writes on multiple threads.
db = SqliteDatabase('web_proxies.db', threadlocals=True)

import logging

logger = logging.getLogger('peewee')
#logger.setLevel(logging.DEBUG)
logger.setLevel(logging.ERROR)
logger.addHandler(logging.StreamHandler())


class ProxyModel(Model):
    class Meta:
        database = db


class DeactivationReasons:
    TimeoutExceeded = 1
    TooManyRedirects = 2
    TooManyFailedHttpRequests = 3
    ProxyError = 4
    SocketError = 5
    ConnectionError = 6
    FollowsRedirects = 7
    NotAnonymous = 8
    ContentModifying = 9


class Proxy(ProxyModel):
    ip_address = TextField()
    port = IntegerField()
    name = TextField(null=True)
    url = TextField(null=True)
    source = TextField()
    created_date = DateField(null=True)

    latitude = FloatField(null=True)
    longitude = FloatField(null=True)

    percent_modifying = IntegerField(default=0)  # to nearest percentage point
    supports_https = BooleanField(default=False)
    is_anonymous = BooleanField(default=False)
    follows_redirects = BooleanField(default=True)

    http_successes = IntegerField(default=0)
    http_attempts = IntegerField(default=0)

    deactivated_date = DateField(null=True)
    deactivation_reason = IntegerField(null=True)

    def deactivate(self, reason):
        self.deactivated_date = date.today()
        self.deactivation_reason = reason

    def deactivated(self):
        return self.deactivated_date is not None

    def update_stats(self, success):
        if success:
            self.http_successes += 1
        self.http_attempts += 1

        if self.http_attempts > 10 and self.http_successes < (
                .90 * self.http_attempts) and not self.deactivated_date:
            self.deactivate(DeactivationReasons.TooManyFailedHttpRequests)

    @staticmethod
    def test():
        pass

    @staticmethod
    def viable_proxies_in_country(country):
        return Proxy.select().where((Proxy.country == country) &
                                    (Proxy.supports_https is True) &
                                    (Proxy.percent_modifying == 0) &
                                    (Proxy.is_anonymous is True) &
                                    (Proxy.deactivated_date >> None) &
                                    (Proxy.follows_redirects is False))

    @staticmethod
    def viable_proxies_not_in_country(country):
        return Proxy.select().where((Proxy.country != country) &
                                    (Proxy.supports_https is True) &
                                    (Proxy.percent_modifying == 0) &
                                    (Proxy.is_anonymous is True) &
                                    (Proxy.deactivated_date >> None) &
                                    (Proxy.follows_redirects is False))

    class Meta:
        indexes = ((('ip_address', 'port'), True),)


class Endpoint(ProxyModel):
    # This determines the granularity of proxy assignments.This could be an IP address, domain name, etc.
    key = TextField(unique=True)
    ip_address = TextField(null=True)
    latitude = FloatField(null=True)
    longitude = FloatField(null=True)


class ProxyEndpoint(ProxyModel):
    proxy = ForeignKeyField(Proxy)
    endpoint = ForeignKeyField(Endpoint)
    created_date = DateField()
    physical_distance = IntegerField(null=True)  # in kilometers
    ave_throughput = IntegerField(null=True)  # in bytes per second
    max_throughput = IntegerField(null=True)  # in bytes per second
    min_throughput = IntegerField(null=True)  # in bytes per second
    last_success = DateTimeField(null=True)
    last_failure = DateTimeField(null=True)
    num_requests = IntegerField(default=0)
    blocked_count = IntegerField(default=0)
    last_blocked = DateTimeField(null=True)
    throttle_level = IntegerField(default=0)  # in milliseconds
    restricted = BooleanField(default=False)

    def update_stats(self, bps):
        self.last_success = datetime.utcnow()

        self.num_requests += 1

        if bps <= 0.0:
            return

        self.max_throughput = bps if self.max_throughput is None else max(self.max_throughput, bps)
        self.min_throughput = bps if self.min_throughput is None else min(self.min_throughput, bps)
        self.ave_throughput = bps if self.ave_throughput is None \
            else new_moving_average(self.ave_throughput, self.num_requests, bps)

        # todo: consider deactivating a proxy endpoint based on its success rate.
        # It could be that it is the endpoint causing the proxy to fail and not the proxy itself.
        # this will require adding success parameters to this function
        # proxy.update_stats() could be called from here.

    def blocked(self):
        self.blocked_count += 1
        self.last_blocked = datetime.utcnow()
        self.save()

    class Meta:
        indexes = ((('proxy', 'endpoint'), True),)


class Event403(ProxyModel):
    proxy_endpoint = ForeignKeyField(ProxyEndpoint)
    timestamp = DateTimeField()
