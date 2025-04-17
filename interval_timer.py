#!/usr/bin/env python3
"""Record the interval between events"""
#
# :dotsctl:
#   destdir: ~/bin/
# ...

import argparse
import time


def num2timestr(seconds):
    """Convert a number of seconds into a human time"""

    if seconds == 0:
        return "now"

    days, seconds = divmod(seconds, (60*60*24))
    hours, seconds = divmod(seconds, (60*60))
    minutes, seconds = divmod(seconds, 60)

    fields = 0
    r = []
    if days:
        r += [f"{days}d"]
        fields += 1
    if fields < 2 and hours:
        r += [f"{hours}h"]
        fields += 1
    if fields < 2 and minutes:
        r += [f"{minutes}m"]
        fields += 1
    if fields < 2 and seconds:
        if isinstance(seconds, float):
            r += [f"{seconds:.2}s"]
        else:
            r += [f"{seconds}s"]
        fields += 1
    return "".join(r)


class Statistics:
    def __init__(self):
        self.total = 0
        self.count = 0
        self.last = None
        self.min = None
        self.max = None

    def add(self, delta):
        self.last = delta
        self.count += 1
        self.total += delta

        if self.min is None:
            self.min = delta
        if self.max is None:
            self.max = delta

        if self.min > delta:
            self.min = delta

        if self.max < delta:
            self.max = delta

    @property
    def mean(self):
        return self.total / self.count

    def __str__(self):
        fields = {
            "count": self.count,
            "total": num2timestr(int(self.total)),
            "last": num2timestr(int(self.last)),
            "min": num2timestr(int(self.min)),
            "max": num2timestr(int(self.max)),
            "mean": num2timestr(self.mean),
        }

        r = []
        for k, v in fields.items():
            r.append(f"{k}={v}")

        return " ".join(r)


def argparser():
    args = argparse.ArgumentParser(description=__doc__)
    return args.parse_args()


def main():
    args = argparser()

    stats = Statistics()
    t1 = time.time()

    while True:
        _ = input()
        t2 = time.time()

        elapsed = t2 - t1
        stats.add(elapsed)
        t1 = t2

        print(int(t2), stats, end = "")


if __name__ == "__main__":
    main()
