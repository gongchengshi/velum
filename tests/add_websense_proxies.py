import os

from model.model_helpers import initialize
from proxy_import.add_new_proxies import *


websense_proxies = {
    '116.50.57.180': 8080, # Hong Kong 2
    'hybrid-web.global.blackspider.com': 8081,
    '208.87.233.150': 8081, # San Jose
    '85.115.52.150': 8081, # London
    '85.115.60.150': 8081, # Paris
    '85.115.58.150': 8081, # Dusseldorf
    '116.50.57.150': 8081, # Hong Kong
    '116.50.58.150': 8081, # Sydney,
    '208.87.234.150': 8081, # Virginia
}


def main():
    if not check_services():
        return -1

    if not os.path.exists("web_proxies.db"):
        initialize()

    for host, port in websense_proxies.iteritems():
        process_proxy(host, str(port), 'WebSense')
        print "Added %s:%s" % (host, port)

    return 0

if __name__ == "__main__":
    main()
