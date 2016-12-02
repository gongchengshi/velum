def calculate_throughput(response, t_start, t_end):
    t_delta = t_end - t_start
    num_bytes = len(response.content)
    throughput = int(num_bytes / t_delta) if t_delta else num_bytes
    return throughput


import requests


def get_public_ip_address():
    try:
        r = requests.get('http://ip.jsontest.com/', timeout=10)
        r.raise_for_status()
        my_ip = r.json()['ip']
    except:
        try:
            r = requests.get('http://httpbin.org/ip', timeout=10)
            r.raise_for_status()
            my_ip = r.json()['origin']
        except:
            raise Exception('Failed to get my IP address.')
    return my_ip


def new_moving_average(current_average, current_count, value):
    return ((current_average * current_count) + value) / (current_count + 1)


import StringIO
from difflib import SequenceMatcher


class PercentDiffCalculator:
    def __init__(self, base):
        self.expected_length = len(base)
        self.differ = SequenceMatcher(a=self.make_hash_sequence(base), autojunk=False)

    @staticmethod
    def make_hash_sequence(content):
        buf = StringIO.StringIO(content)
        return [hash(line) for line in buf.readlines()]

    def diff(self, content):
        """
        If the difference is less than 1% then return 1%
        Return the value rounded to the nearest percent
        Return a negative percent if the actual response is smaller than the expected response
        """

        self.differ.set_seq2(self.make_hash_sequence(content))
        percent_diff = (1.0 - self.differ.ratio()) * 100.0
        percent_diff = 1 if 0 < percent_diff < 1 else int(round(percent_diff, 0))

        if percent_diff != 0 and len(content) < self.expected_length:
            percent_diff *= -1

        return percent_diff
