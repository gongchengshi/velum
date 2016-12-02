import sys
import os

from velum.model.model_helpers import initialize
from velum.proxy_import.add_new_proxies import check_services, process_proxy
from velum.proxy_import.web_proxy_lists import get_proxy_lists


def main():
    if not check_services():
        return -1

    if not os.path.exists("web_proxies.db"):
        initialize()

    for zip_file in get_proxy_lists():
        print "\n---- Opening Proxy List ----"
        for line in zip_file.open('full_list_nopl/_full_list.txt'):
            ip_address, port = line.strip().split(':')
            process_proxy(ip_address, port, 'hidemyass.com')
            sys.stdout.flush()
    print ""
    return 0

if __name__ == "__main__":
    main()
