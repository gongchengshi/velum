class WebProxyException(Exception):
    def __init__(self, reason=None):
        Exception.__init__(reason)


class WebProxyDbException(Exception):
    def __init__(self, reason=None):
        Exception.__init__(reason)


class VelumNotResponding(Exception):
    def __init__(self):
        Exception.__init__(self, 'No response was received from Velum within the specified timeout')
