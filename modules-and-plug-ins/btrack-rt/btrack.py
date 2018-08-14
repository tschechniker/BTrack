from contextlib import contextmanager
from _btrack import ffi, lib
import time


def _check_error():
    msg = ffi.string(lib.get_last_error())
    raise Exception(msg)


class Tracker:
    slots = ('__ctx',)
    def __init__(self, ctx):
        self.__ctx = ctx

    def has_beats(self):
        return lib.has_beats(self.__ctx)

    @property
    def bpm(self):
        return self.__ctx.bpm

    @property
    def vol(self):
        return self.__ctx.vol


@contextmanager
def track_beats():
    ctx = lib.track_beats()
    if ctx == ffi.NULL:
        _check_error()

    try:
        yield Tracker(ctx)
    finally:
        e = lib.stop_tracking(ctx)
        if e:
            _check_error()


if __name__ == '__main__':
    with track_beats() as tracker:
        while True:
            if tracker.has_beats():
                print("Beat (py):", tracker.bpm)
            time.sleep(0.02)

