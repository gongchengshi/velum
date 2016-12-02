#!/usr/bin/python2
import os
from velum.proxy_manager.proxy_manager import ProxyManager


def main():
    os.nice(-1)

    velum = ProxyManager()
    velum.start()
    velum.join()

if __name__ == "__main__":
    main()
