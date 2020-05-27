from collections import OrderedDict


class FixedSizeOrderedDict(OrderedDict):
    # A specialisation of OrderedDict that enforces a max size, similar to deque
    def __init__(self, *args, max=0, **kwargs):
        self._max = max
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        if self._max > 0:
            if len(self) > self._max:
                self.popitem(False)