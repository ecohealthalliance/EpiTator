class Interval():
    def __init__(self, start, end, weight, corresponding_object):
        self.start = start
        self.end = end
        self.weight = weight
        self.corresponding_object = corresponding_object
        # The combined weight of the MWIS prior to this interval.
        self.__value__ = None
        # The previous inverval in the MWIS prior to this interval.
        self.__previous__ = None

    def start_endpoint(self):
        return Endpoint(self, True)

    def end_endpoint(self):
        return Endpoint(self, False)

    def __len__(self):
        return self.end - self.start


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
        # This sorts endpont in the following order when offsets are the same:
        # [NI end points][ZI start points][NI start points][ZI end points]
        # NI = Non-zero length interval
        # ZI = Zero length interval
        if self.get_idx() == other.get_idx():
            if len(self.interval) == 0:
                if len(other.interval) == 0:
                    return self.is_start and not other.is_start
                else:
                    return self.is_start and other.is_start
            else:
                if len(other.interval) == 0:
                    return not self.is_start or not other.is_start
                else:
                    return not self.is_start and other.is_start
        else:
            return self.get_idx() < other.get_idx()


def find_maximum_weight_interval_set(intervals):
    """
    Takes a list of weighted intervals and returns a non-overlapping set of them
    with the maximum possible weight.
    Weights may be numeric or numeric tuples.
    There are some edge-cases to consider in determining what constitutes an
    overlap in relation to end-points and zero length intervals.
    The intervals are left-closed. If the left endpoints of two zero
    length intervals overlap, they are considered to be overlapping.
    However, the right endpoint of a non-zero length interval could overlap
    the left endpoint of another interval without it being considered an overlap.
    Of course, if an endpoint is in the middle of another non-zero length
    interval, it is considered to be overlapping.
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
                if isinstance(max_interval_sofar.__value__, tuple):
                    endpoint.interval.__value__ = tuple(map(sum, zip(max_interval_sofar.__value__,
                                                                     endpoint.interval.__value__)))
                else:
                    endpoint.interval.__value__ += max_interval_sofar.__value__
                endpoint.interval.__previous__ = max_interval_sofar
        else:  # endoint.is_end
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
