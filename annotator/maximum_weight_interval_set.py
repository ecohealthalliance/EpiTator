class Interval():
    def __init__(self, start, end, weight, corresponding_object):
        self.start = start
        self.end = end
        self.weight = weight
        self.corresponding_object = corresponding_object
        self.value = 0.0
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
            # when iterating over the sorted endpoints. This is necessairy
            # so that that starting interval scores won't include the
            # score of the intervals that end at the same point they begin.
            return self.is_start
        else:
            return self.get_idx() < other.get_idx()
def find_maximum_weight_interval_set(intervals):
    """
    Takes a list of weighted intervals and returns a non-overlapping set of them
    with the maximum possible weight. Endpoints cannot overlap.
    Currently interval weights must be sensitive to no more than 2 decimal places.
    """
    endpoints = []
    for interval in intervals:
        endpoints.append(interval.start_endpoint())
        endpoints.append(interval.end_endpoint())
    sorted_endpoints = sorted(endpoints)
    temp_max = 0.0
    for endpoint in sorted_endpoints:
        if endpoint.is_start:
            endpoint.interval.value = temp_max + endpoint.interval.weight
        else:
            if endpoint.interval.value > temp_max:
                temp_max = endpoint.interval.value
    # Now temp_max is the actual max weight.
    # Do backtracking to determine the intervals in the
    # maximum weighted interval set:
    mwis = []
    seek_idx = None
    for endpoint in reversed(sorted_endpoints):
        # Seek to endpoints before seek_idx
        if seek_idx is not None:
            if endpoint.get_idx() >= seek_idx:
                continue
        # Comparing values to identify intervals has the disadvantage that it
        # it limits the precision of the intervals weights.
        if (
            not endpoint.is_start and
            round(endpoint.interval.value, 3) == round(temp_max, 3)
        ):
            mwis.insert(0, endpoint.interval)
            temp_max -= endpoint.interval.weight
            seek_idx = endpoint.interval.start
    return mwis
