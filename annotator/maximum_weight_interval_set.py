class Interval():
    def __init__(self, start, end, weight, corresponding_object):
        self.start = start
        self.end = end
        self.weight = weight
        self.corresponding_object = corresponding_object
        # The combined weight of the MWIS prior to this interval.
        self.__value__ = 0.0
        # The previous inverval in the MWIS prior to this interval.
        self.__previous__ = None
    def start_endpoint(self):
        return Endpoint(self, True)
    def end_endpoint(self):
        return Endpoint(self, False)
class Endpoint():
    def __init__(self, interval, is_start):
        self.interval = interval
        self.is_start = is_start
    def get_idx(self):
        if self.is_start:
            return self.interval.start
        else:
            return self.interval.end
    def __lt__(self, other):
        if self.get_idx() == other.get_idx():
            # This condition is used so the starting endpoints come first
            # when iterating over the sorted endpoints.
            # This is necessary for zero length intervals.
            # However, it also adds the requirement that overlapping endpoints
            # makes invervals overlap.
            return self.is_start and not other.is_start
        else:
            return self.get_idx() < other.get_idx()

def find_maximum_weight_interval_set(intervals):
    """
    Takes a list of weighted intervals and returns a non-overlapping set of them
    with the maximum possible weight.
    If endpoints overlap, the intervals are considered to be overlapping.
    """
    endpoints = []
    for interval in intervals:
        endpoints.append(interval.start_endpoint())
        endpoints.append(interval.end_endpoint())
    sorted_endpoints = sorted(endpoints)
    max_interval_sofar = None
    for endpoint in sorted_endpoints:
        if endpoint.is_start:
            endpoint.interval.__value__ = endpoint.interval.weight
            if max_interval_sofar:
                endpoint.interval.__value__ += max_interval_sofar.__value__
                endpoint.interval.__previous__ = max_interval_sofar
        else: #endoint.is_end
            if not max_interval_sofar:
                max_interval_sofar = endpoint.interval
            elif endpoint.interval.__value__ >= max_interval_sofar.__value__:
                max_interval_sofar = endpoint.interval
    mwis = []
    while max_interval_sofar:
        mwis.insert(0, max_interval_sofar)
        max_interval_sofar = max_interval_sofar.__previous__
    if len(intervals) >= 1:
        assert len(mwis) >= 1
    return mwis
